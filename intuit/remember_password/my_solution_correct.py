def remember_password(k, n, passwords, password):
    list_pass = passwords.split()
    pass_len = len(password)

    # count passwords by length
    map_pass = {}
    for passw in list_pass:
        map_pass[len(passw)] = map_pass.get(len(passw), 0) + 1

    def time_for_attempts(count, attempts_before):
        # attempts_before = wrong attempts already made before this group
        total = 0
        for i in range(count):
            total += 1  # 1 second per attempt
            attempts_so_far = attempts_before + i + 1
            if attempts_so_far % k == 0:
                total += 5  # 5 second penalty every k attempts
        return total

    best_time = 0
    worst_time = 0
    attempts_so_far = 0

    for length in sorted(map_pass.keys()):
        count = map_pass[length]
        if length < pass_len:
            # must try all of them in both cases
            t = time_for_attempts(count, attempts_so_far)
            best_time += t
            worst_time += t
            attempts_so_far += count
        elif length == pass_len:
            # best case: correct password is first attempt of this group
            best_time += 1
            if attempts_so_far % k == 0 and attempts_so_far > 0:
                best_time += 5

            # worst case: correct password is last attempt of this group
            worst_time += time_for_attempts(count, attempts_so_far)
            print(f"{best_time} {worst_time}")
            break

def time(n, k):
    return n + ((n // k) * 5)

import os, sys

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
