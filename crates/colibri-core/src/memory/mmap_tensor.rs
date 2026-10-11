use std::fs::File;
use std::path::Path;
use memmap2::{Mmap, MmapOptions};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum MemoryError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Slice out of bounds: offset {offset} + len {len} > size {total}")]
    OutOfBounds { offset: usize, len: usize, total: usize },
}

/// Zero-copy memory mapped tensor container.
/// Direct kernel paging with madvise sequential hints and hugepage backing.
pub struct MmapTensor {
    mmap: Mmap,
    len: usize,
}

impl MmapTensor {
    /// Opens a weight file (e.g. .gguf, .safetensors, .bin) with zero-copy mmap.
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self, MemoryError> {
        let file = File::open(path)?;
        let mmap = unsafe { MmapOptions::new().map(&file)? };
        let len = mmap.len();

        #[cfg(target_os = "linux")]
        unsafe {
            // MADV_WILLNEED: Advise kernel to preload pages if feasible
            libc::madvise(mmap.as_ptr() as *mut libc::c_void, len, libc::MADV_WILLNEED);
            // MADV_HUGEPAGE: Enable transparent huge pages (2MB) for high-bandwidth SIMD streaming
            #[cfg(target_env = "gnu")]
            libc::madvise(mmap.as_ptr() as *mut libc::c_void, len, libc::MADV_HUGEPAGE);
        }

        Ok(Self { mmap, len })
    }

    #[inline(always)]
    pub fn as_slice(&self) -> &[u8] {
        &self.mmap[..]
    }

    #[inline(always)]
    pub fn len(&self) -> usize {
        self.len
    }

    #[inline(always)]
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    /// Zero-copy byte slice extraction without copying from disk into heap.
    pub fn slice_bytes(&self, offset: usize, length: usize) -> Result<&[u8], MemoryError> {
        if offset + length > self.len {
            return Err(MemoryError::OutOfBounds {
                offset,
                len: length,
                total: self.len,
            });
        }
        Ok(&self.mmap[offset..offset + length])
    }
}
