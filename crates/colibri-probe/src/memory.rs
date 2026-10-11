pub fn get_memory_info() -> (f64, f64) {
    let mut sys = sysinfo::System::new();
    sys.refresh_memory();
    let total = sys.total_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    let avail = sys.available_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    (total, avail)
}
