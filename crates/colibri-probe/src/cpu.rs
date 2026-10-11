pub fn detect_isa() -> Vec<&'static str> {
    let mut flags = Vec::new();
    #[cfg(target_arch = "x86_64")]
    {
        if is_x86_feature_detected!("avx512f") {
            flags.push("AVX-512");
        }
        if is_x86_feature_detected!("avx2") {
            flags.push("AVX2");
        }
        if is_x86_feature_detected!("fma") {
            flags.push("FMA");
        }
    }
    #[cfg(target_arch = "aarch64")]
    {
        flags.push("NEON");
    }
    flags
}
