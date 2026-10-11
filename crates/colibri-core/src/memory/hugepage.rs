/// Transparent Huge Page (THP) and direct pointer utility.
pub struct HugePageBuffer {
    ptr: *mut u8,
    size: usize,
}

impl HugePageBuffer {
    pub fn allocate(size: usize) -> Option<Self> {
        let aligned_size = (size + 2 * 1024 * 1024 - 1) & !(2 * 1024 * 1024 - 1);
        unsafe {
            let mut ptr: *mut libc::c_void = std::ptr::null_mut();
            let ret = libc::posix_memalign(&mut ptr, 2 * 1024 * 1024, aligned_size);
            if ret != 0 || ptr.is_null() {
                return None;
            }
            #[cfg(target_os = "linux")]
            libc::madvise(ptr, aligned_size, libc::MADV_HUGEPAGE);

            Some(Self {
                ptr: ptr as *mut u8,
                size: aligned_size,
            })
        }
    }

    pub fn as_mut_slice(&mut self) -> &mut [u8] {
        unsafe { std::slice::from_raw_parts_mut(self.ptr, self.size) }
    }

    pub fn size(&self) -> usize {
        self.size
    }
}

impl Drop for HugePageBuffer {
    fn drop(&mut self) {
        unsafe {
            libc::free(self.ptr as *mut libc::c_void);
        }
    }
}
unsafe impl Send for HugePageBuffer {}
unsafe impl Sync for HugePageBuffer {}
