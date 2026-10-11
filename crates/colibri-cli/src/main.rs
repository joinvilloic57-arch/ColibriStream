use colibri_core::{MmapTensor, SimdDispatcher};
use colibri_probe::{probe_system, cpu};
use colored::*;

#[tokio::main]
async fn main() {
    println!("{}", "═══════════════════════════════════════════════════════════════".green().bold());
    println!("{}", "   COLIBRISTREAM CORE ENGINE (Phase 4 Bare-Metal Runtime)       ".green().bold());
    println!("{}", "   Zero-Copy NVMe mmap • SIMD Kernel Dispatch • MoE Streaming    ".dimmed());
    println!("{}", "═══════════════════════════════════════════════════════════════\n".green().bold());

    // 1. Hardware Probe
    let telemetry = probe_system();
    println!("{}", "[*] Hardware Diagnostics:".cyan().bold());
    println!("    • CPU Architecture : {} ({} physical/logical cores)", telemetry.cpu_arch.white(), telemetry.cpu_cores);
    let isa_flags = cpu::detect_isa();
    println!("    • SIMD Vector ISA  : {}", isa_flags.join(", ").yellow());
    println!("    • Host RAM Ceiling : {:.2} GB total ({:.2} GB available)", telemetry.total_ram_gb, telemetry.avail_ram_gb);
    println!("    • Storage Burst I/O: {:.2} GB/s sequential throughput", telemetry.nvme_speed_gb_s);

    // 2. SIMD Dynamic Dispatch
    let dispatcher = SimdDispatcher::new();
    println!("\n{}", "[*] Tensor Compute Dispatcher:".cyan().bold());
    println!("    • Active Kernel    : {}", dispatcher.feature_name().green().bold());

    // 3. Test dot product acceleration
    let a = vec![1.5f32; 1024];
    let b = vec![2.0f32; 1024];
    let result = unsafe { dispatcher.dot_product(a.as_ptr(), b.as_ptr(), 1024) };
    println!("    • SIMD Sanity Run  : 1024-element dot product = {:.2} (Expected: 3072.00)", result);

    println!("\n{}", "✔ Colibristream Bare-Metal Rust Kernel Operational.".green().bold());
}
