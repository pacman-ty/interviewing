import sys
import os

def remember_password(k : int, n : int, passwords : str, password : str): 
    list_pass = passwords.split()
    map_pass = {}

    for passw in list_pass: 
        if len(passw) in map_pass : 
            map_pass[len(passw)] += 1
        else : 
            map_pass[len(passw)] = 1

    pass_len = len(password) 
    
    best_time = 0
    worst_time = 0

    for i in range(pass_len + 1) : 
    
        if  i not in map_pass : 
            continue 
        if pass_len == i : 
            best_time += 1 
            worst_time += time(i, k)
            print(f"{best_time} {worst_time}")
            return 
        else : 
            best_time += time(i, k)
            worst_time += time(i, k)
        
        
def time(n, k): 
    return n + ((n // k) * 5)


if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "tests"
    test_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    if not test_files:
        print(f"No files found in '{directory}'")
        sys.exit(1)

    for filename in sorted(test_files):
        filepath = os.path.join(directory, filename)
        print(f"--- {filename} ---")
        with open(filepath) as f:
            lines = [line.rstrip("\n") for line in f]
        k         = int(lines[0])
        n         = int(lines[1])
        passwords = lines[2]
        password  = lines[3]
        remember_password(k, n, passwords, password)
        print()
