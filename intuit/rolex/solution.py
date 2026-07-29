def solution(s: str) -> int:
    """

    Given a circular string of '>' and '<' representing desired spin directions

    of cogwheels in a cycle, return the minimum removals so all meshing pairs

    spin in opposite directions.

   

    Key insight: conflicts (same-direction neighbors) form consecutive runs

    along the cycle. Each run of k conflict edges requires ceil(k/2) removals.

    This is the minimum vertex cover of a path (or cycle if all edges conflict).

    """

    n = len(s)

    if n <= 1:

        return 0

 

    # Step 1: Identify conflict edges.

    # Edge i connects gear i to gear (i+1) % n.

    # It's a conflict if both gears want the same direction.

    is_conflict = [s[i] == s[(i + 1) % n] for i in range(n)]

 

    num_conflicts = sum(is_conflict)

 

    # Step 2: No conflicts means the mechanism already works perfectly.

    if num_conflicts == 0:

        return 0

 

    # Step 3: If ALL edges are conflicts, every gear spins the same way.

    # The conflict graph is a full cycle. Minimum vertex cover of an

    # n-cycle is ceil(n/2) — you must remove every other gear, and for

    # odd n you need one extra because the cycle wraps around.

    if num_conflicts == n:

        return (n + 1) // 2

 

    # Step 4: Find maximal consecutive runs of conflict edges.

    # Since not all edges are conflicts, at least one non-conflict edge

    # exists. We start there to "linearize" the cycle — this guarantees

    # no run is split across the start/end boundary.
    start = is_conflict.index(False)


 

    result = 0

    run_length = 0

 

    for i in range(n):

        idx = (start + i) % n

        if is_conflict[idx]:

            # Extend the current run of consecutive conflict edges

            run_length += 1

        else:

            # End of a run — a path of run_length conflict edges needs

            # ceil(run_length / 2) vertex removals to cover all edges

            if run_length > 0:

                result += (run_length + 1) // 2

            run_length = 0

 

    # Handle the last run (if the iteration ended mid-run)

    if run_length > 0:

        result += (run_length + 1) // 2

 

    return result

 

 

# ---- Test with the provided examples ----

print(solution("<>>>"))   # Expected: 1

print(solution("<><>"))   # Expected: 0

print(solution(">>><>"))   # Expected: 2
