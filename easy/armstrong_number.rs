impl Solution {
  pub fn is_armstrong_number(num: u32) -> bool {
    if num == 0 {
        return true;
    }

    let mut n = num;
    let mut digits = 0;

    while n > 0 {
        digits += 1;
        n /= 10;
    }

    let mut n = num;
    let mut sum = 0;

    while n > 0 {
        let d = n % 10;
        sum += d.pow(digits);
        n /= 10;
    }

    sum == num
  }
}

// This version is strictly worse then the one above
// Taking modulos should be faster because it cant all be done 
// In the cpu / registers
// Included as alternative / practice and performance should still 
// be kind of comparable 
impl Solution {
  pub fn is_armstrong_number(num: u32) -> bool {
    let num_str = num.to_string();
    let len = num_str.len() as u32;
    num_str.chars().map(|ch| ch.to_digit(10).unwrap().pow(len)).sum::<u32>() == num
  }
}


