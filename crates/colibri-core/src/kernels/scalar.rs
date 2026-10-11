pub unsafe fn dot_product_scalar(a: *const f32, b: *const f32, len: usize) -> f32 {
    let mut sum = 0.0f32;
    for i in 0..len {
        sum += *a.add(i) * *b.add(i);
    }
    sum
}
