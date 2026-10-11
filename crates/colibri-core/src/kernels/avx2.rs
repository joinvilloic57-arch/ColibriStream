#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
pub unsafe fn dot_product_avx2(a: *const f32, b: *const f32, len: usize) -> f32 {
    let mut sum_vec = _mm256_setzero_ps();
    let chunks = len / 8;
    let remainder = len % 8;

    for i in 0..chunks {
        let va = _mm256_loadu_ps(a.add(i * 8));
        let vb = _mm256_loadu_ps(b.add(i * 8));
        sum_vec = _mm256_fmadd_ps(va, vb, sum_vec);
    }

    // Horizontal sum across 256-bit register
    let mut buffer = [0.0f32; 8];
    _mm256_storeu_ps(buffer.as_mut_ptr(), sum_vec);
    let mut total: f32 = buffer.iter().sum();

    // Remainder loop
    let tail_offset = chunks * 8;
    for i in 0..remainder {
        total += *a.add(tail_offset + i) * *b.add(tail_offset + i);
    }

    total
}

#[cfg(not(target_arch = "x86_64"))]
pub unsafe fn dot_product_avx2(a: *const f32, b: *const f32, len: usize) -> f32 {
    super::scalar::dot_product_scalar(a, b, len)
}
