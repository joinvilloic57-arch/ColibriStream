use std::fs::OpenOptions;
use std::io::{Read, Write};
use std::time::Instant;

/// Benchmark sequential storage throughput using 16MB direct I/O
pub fn measure_nvme_throughput() -> f64 {
    let test_path = std::env::temp_dir().join("colibri_probe_io.tmp");
    let buffer_size = 16 * 1024 * 1024; // 16MB
    let data = vec![0xAAu8; buffer_size];

    // Write test buffer
    if let Ok(mut file) = OpenOptions::new().create(true).write(true).open(&test_path) {
        let _ = file.write_all(&data);
    } else {
        return 0.0;
    }

    // Measure read speed
    let speed = if let Ok(mut file) = OpenOptions::new().read(true).open(&test_path) {
        let mut read_buf = vec![0u8; buffer_size];
        let start = Instant::now();
        if file.read_exact(&mut read_buf).is_ok() {
            let elapsed = start.elapsed().as_secs_f64();
            if elapsed > 0.0 {
                (buffer_size as f64 / (1024.0 * 1024.0 * 1024.0)) / elapsed
            } else {
                0.0
            }
        } else {
            0.0
        }
    } else {
        0.0
    };

    let _ = std::fs::remove_file(&test_path);
    speed
}
