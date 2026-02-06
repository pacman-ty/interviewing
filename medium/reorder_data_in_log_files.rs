impl Solution {
    pub fn reorder_log_files(logs: Vec<String>) -> Vec<String> {
        // let log be mutable so we can move pointer 
        // in loop making it cheaper avoiding 
        // O(n * m) => ll.push(log.to_string())
        let mut logs = logs;
        let mut ll: Vec<String> = Vec::new();
        let mut dl: Vec<String> = Vec::new();
        

        for log in logs {
            let (key, value) = log.split_once(" ").unwrap();

            if value.as_bytes()[0].is_ascii_digit() {
                dl.push(log);
            } else {
                ll.push(log);
            }
        }   

        
        ll.sort_by(|a, b| {
            let (k1, v1) = a.split_once(" ").unwrap();
            let (k2, v2) = b.split_once(" ").unwrap();

            if v1 == v2 {
                return k1.cmp(k2);
            } else {
                return v1.cmp(v2);
            }
        });

        ll.append(&mut dl);
        ll
    }
}
