pub mod scalar;
pub mod avx2;

pub type DotProductFn = unsafe fn(a: *const f32, b: *const f32, len: usize) -> f32;
