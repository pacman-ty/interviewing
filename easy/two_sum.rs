use std::collections::HashMap;

impl Solution {
    pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
        let mut vals: HashMap<i32, i32> = HashMap::with_capacity(nums.len());
        for (i, v) in nums.iter().enumerate() {
            match vals.get(&(target - *v)) {
                Some(&index) => return vec![i as i32, index],
                None => vals.insert(*v, i as i32),
            };
        }
        vec![]
    }
}
