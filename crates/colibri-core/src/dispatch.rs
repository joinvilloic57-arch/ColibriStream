use crate::kernels::{scalar, avx2, DotProductFn};

pub struct SimdDispatcher {
    dot_product_impl: DotProductFn,
    feature_name: &'static str,
}

impl SimdDispatcher {
    /// Detects CPU ISA dynamically at runtime and binds optimal SIMD kernel.
    pub fn new() -> Self {
        #[cfg(target_arch = "x86_64")]
        {
            if is_x86_feature_detected!("avx2") && is_x86_feature_detected!("fma") {
                return Self {
                    dot_product_impl: avx2::dot_product_avx2,
                    feature_name: "AVX2+FMA (256-bit SIMD)",
                };
            }
        }

        Self {
            dot_product_impl: scalar::dot_product_scalar,
            feature_name: "Scalar Fallback",
        }
    }

    #[inline(always)]
    pub fn feature_name(&self) -> &'static str {
        self.feature_name
    }

    #[inline(always)]
    pub unsafe fn dot_product(&self, a: *const f32, b: *const f32, len: usize) -> f32 {
        (self.dot_product_impl)(a, b, len)
    }
}

impl Default for SimdDispatcher {
    fn default() -> Self {
        Self::new()
    }
}
