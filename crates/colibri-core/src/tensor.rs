use bytemuck::Pod;

/// Zero-copy tensor slice viewer over memory mapped weight buffers.
pub struct TensorView<'a, T> {
    data: &'a [T],
    shape: Vec<usize>,
}

impl<'a, T: Pod> TensorView<'a, T> {
    pub fn from_raw_bytes(bytes: &'a [u8], shape: Vec<usize>) -> Option<Self> {
        let expected_elements: usize = shape.iter().product();
        let expected_bytes = expected_elements * std::mem::size_of::<T>();
        if bytes.len() < expected_bytes {
            return None;
        }

        let typed_slice = bytemuck::try_cast_slice(&bytes[..expected_bytes]).ok()?;
        Some(Self {
            data: typed_slice,
            shape,
        })
    }

    #[inline(always)]
    pub fn as_slice(&self) -> &'a [T] {
        self.data
    }

    #[inline(always)]
    pub fn shape(&self) -> &[usize] {
        &self.shape
    }

    #[inline(always)]
    pub fn as_ptr(&self) -> *const T {
        self.data.as_ptr()
    }

    #[inline(always)]
    pub fn len(&self) -> usize {
        self.data.len()
    }

    #[inline(always)]
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }
}
