def remember_password_optimized(k, n, passwords, actual):

    """

    OPTIMIZED APPROACH:

    -------------------

    Key Insight: We don't need to simulate all orderings. The only thing that

    varies between orderings is WHERE the correct password falls among its

    same-length group. Everything else is deterministic.

   

    Three categories of passwords matter:

      1. "shorter" — passwords with length < len(actual): MUST all be tried first.

      2. "same"    — passwords with length == len(actual): tried in arbitrary order.

      3. "longer"  — passwords with length > len(actual): never reached.

   

    Best case: correct password is tried FIRST in its same-length group.

      → wrong_attempts = shorter

      → total_attempts = shorter + 1

   

    Worst case: correct password is tried LAST in its same-length group.

      → wrong_attempts = shorter + (same - 1)

      → total_attempts = shorter + same

   

    Time formula: total_attempts + 5 * floor(wrong_attempts / k)

   

    Why floor(wrong_attempts / k)?

    Every k consecutive wrong attempts triggers one 5-second penalty.

    After k wrongs → penalty, counter resets. After 2k wrongs → 2 penalties. Etc.

    So the number of penalties is simply wrong_attempts // k.

    """

   

    actual_len = len(actual)

   

    # Step 1: Count passwords strictly shorter than the actual password.

    # These MUST all be attempted before any same-length password.

    shorter = 0

   

    # Step 2: Count passwords of the same length (including the actual one).

    # Among these, the ordering is arbitrary — giving us best/worst cases.

    same = 0

   

    for pw in passwords:

        if len(pw) < actual_len:

            shorter += 1

        elif len(pw) == actual_len:

            same += 1

        # Passwords longer than actual_len are irrelevant — John will have

        # already found the correct password before reaching them.

   

    # Step 3: Calculate best case.

    # Best case: John luckily tries the correct password first in its group.

    # He's made 'shorter' wrong attempts, then gets it right immediately.

    best_wrong = shorter

    best_total = shorter + 1

    best_penalties = best_wrong // k

    best_time = best_total + 5 * best_penalties

   

    # Step 4: Calculate worst case.

    # Worst case: John unluckily tries the correct password last in its group.

    # He's made 'shorter + (same - 1)' wrong attempts before finding it.

    worst_wrong = shorter + (same - 1)

    worst_total = shorter + same

    worst_penalties = worst_wrong // k

    worst_time = worst_total + 5 * worst_penalties

   

    return best_time, worst_time

 

print(remember_password_optimized(1, 2, ["aa1", "bbb"], "aa1"))  # (1, 7)

print(remember_password_optimized(2, 3, ["a", "bb", "ccc"], "bb"))  # (2, 2)
