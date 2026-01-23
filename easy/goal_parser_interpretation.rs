impl Solution {
    pub fn interpret(command: String) -> String {
        let mut goal = String::new();
        let mut prev = ' ';

        for c in command.chars() {
            match (c, prev) {
                ('G', _) => goal.push(c),
                (')', '(') => goal.push('o'),
                (')', 'l') => goal.push_str("al"),
                _ => prev = c,
            }
        }
        goal
    }
}


// Seperate cool solution I saw probably wouldnt use this 
// in an interview though 

impl Solution {
    pub fn interpret(command: String) -> String {
        command.replace("()", "o").replace("(al)", "al")
    }
}
