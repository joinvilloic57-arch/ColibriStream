pub mod cpu;
pub mod memory;
pub mod storage;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemTelemetry {
    pub cpu_cores: usize,
    pub cpu_arch: String,
    pub total_ram_gb: f64,
    pub avail_ram_gb: f64,
    pub nvme_speed_gb_s: f64,
}

pub fn probe_system() -> SystemTelemetry {
    let mut sys = sysinfo::System::new_all();
    sys.refresh_all();

    let total_ram = sys.total_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    let avail_ram = sys.available_memory() as f64 / (1024.0 * 1024.0 * 1024.0);

    SystemTelemetry {
        cpu_cores: sys.cpus().len(),
        cpu_arch: std::env::consts::ARCH.to_string(),
        total_ram_gb: total_ram,
        avail_ram_gb: avail_ram,
        nvme_speed_gb_s: storage::measure_nvme_throughput(),
    }
}
