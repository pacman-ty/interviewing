
Now I have a clear picture of the problem. Let me break it down and walk through the full solution.

 

---

 

## Problem Understanding

 

**Strange Sequence**: Find the n-th (0-indexed) number in the sorted sequence of all non-negative integers whose digits are **only** from the set {0, 1, 4, 9}.

 

The sequence begins: **0, 1, 4, 9, 10, 11, 14, 19, 40, 41, 44, 49, 90, 91, 94, 99, 100, ...**

 

---

 

## Thought Process (Interview Walkthrough)

 

### Step 1: Brute Force Idea (and why we skip it)

 

The naive approach would be to iterate over every integer 0, 1, 2, 3, ... and check if it only contains digits from {0,1,4,9}, counting valid ones until we hit the n-th. For n=1000 this might require checking hundreds of thousands of integers. It works, but we can do **much** better.

 

### Step 2: The Key Insight -- Base-4 Bijection

 

Here's the critical observation an interviewer is looking for:

 

There are exactly **4** allowed digits: {0, 1, 4, 9}. Every valid number in this sequence is essentially a **base-4 number** where instead of the standard digit set {0, 1, 2, 3}, we use {0, 1, 4, 9}.

 

Think about it:

| Base-4 digit | Maps to |

|---|---|

| 0 | 0 |

| 1 | 1 |

| 2 | 4 |

| 3 | 9 |

 

So the algorithm is: **convert `n` to base 4, then replace each digit using the mapping.**

 

Let me verify with the examples:

- **n=3**: 3 in base 4 = `3` -> map digit 3 to 9 -> answer is **9** ✓

- **n=7**: 7 in base 4 = `13` -> map `1`->`1`, `3`->`9` -> answer is **19** ✓

 

### Step 3: The Solution

 

```python

def strange_sequence(n):

    """

    INTERVIEW APPROACH — Base-4 Bijection

   

    Key Insight: There are exactly 4 allowed digits {0, 1, 4, 9}.

    This means there's a 1-to-1 correspondence between base-4 numbers

    and valid numbers in our sequence.

   

    The n-th valid number is obtained by:

      1. Writing n in base 4

      2. Replacing each base-4 digit with the corresponding allowed digit

   

    Why does this work?

    - 1-digit valid numbers: 0,1,4,9        -> 4 numbers (= 4^1)

    - 2-digit valid numbers: 10,11,...,99    -> 12 numbers (but total up to 2 digits = 4^2 = 16)

    - In general, the count of valid numbers up to d digits matches

      the count of base-4 numbers up to d digits.

    - The sorted order is preserved because our digit mapping {0,1,4,9}

      is strictly increasing, so the lexicographic/numeric order is identical

      to the base-4 ordering.

    """

 

    # The mapping: base-4 digit -> allowed digit

    # Index 0 maps to digit 0, index 1 maps to 1, index 2 maps to 4, index 3 maps to 9

    digit_map = [0, 1, 4, 9]

 

    # Edge case: if n is 0, the 0th element of the sequence is 0 itself

    if n == 0:

        return 0

 

    # Step 1: Convert n to base 4

    # We extract digits from least significant to most significant (right to left)

    # by repeatedly dividing by 4 and collecting remainders.

    base4_digits = []

    while n > 0:

        remainder = n % 4          # current least-significant base-4 digit

        base4_digits.append(remainder)

        n //= 4                    # shift right in base 4

 

    # base4_digits is in reverse order (least significant first),

    # so we reverse it to get most-significant-first

    base4_digits.reverse()

 

    # Step 2: Map each base-4 digit to the corresponding allowed digit

    # and reconstruct the final number

    result = 0

    for d in base4_digits:

        # Shift the result left by one decimal digit position and add the mapped digit

        # This is equivalent to building the number digit by digit in base 10

        result = result * 10 + digit_map[d]

 

    return result

 

 

# ---------- Verification with the provided examples ----------

print(strange_sequence(3))   # Expected: 9

print(strange_sequence(7))   # Expected: 19

 

# ---------- Print first 20 terms to sanity-check ----------

# Expected: 0, 1, 4, 9, 10, 11, 14, 19, 40, 41, 44, 49, 90, 91, 94, 99, 100, 101, 104, 109

for i in range(20):

    print(f"n={i}: {strange_sequence(i)}")

```

 

---

 

## Why Each Step Is Correct

 

1. **Base-4 conversion**: There are exactly 4 choices per digit position. The total count of valid numbers with at most `d` digits is \(4^d\), which is the same as the count of non-negative integers representable in `d` digits of base 4. This gives us the bijection.

 

2. **The digit mapping preserves order**: Since `0 < 1 < 4 < 9`, if number A comes before number B in base-4 ordering, the mapped version of A will also be numerically smaller than the mapped version of B. This is because we're replacing digits with a strictly increasing sequence, so the relative ordering is preserved.

 

3. **Edge case n=0**: Base-4 representation of 0 has no digits from the while loop, so we handle it explicitly. (Alternatively, you could handle it by initializing the result to 0 and letting the empty loop return 0.)

 

---

 

## Complexity Analysis

 

**Time Complexity: O(log n)**

- Converting `n` to base 4 takes O(log_4(n)) iterations (each iteration divides n by 4).

- Mapping the digits and reconstructing the result also takes O(log_4(n)) iterations.

- Overall: **O(log n)** -- essentially the number of digits in the base-4 representation.

 

**Space Complexity: O(log n)**

- We store the base-4 digits in a list of length O(log_4(n)).

- For `n <= 1000`, log_4(1000) ~ 5, so at most ~5 digits. Extremely lightweight.

 

---

 

## Comparison with Brute Force

 

| Approach | Time | Space |

|---|---|---|

| Brute force (iterate & check) | O(n * k) where k is avg digits per number checked | O(1) |

| **Base-4 bijection** | **O(log n)** | **O(log n)** |

 

The base-4 approach is exponentially faster. For n=1000, brute force might check thousands of numbers; the bijection does ~5 arithmetic operations.

 

---

 

## Interview Talking Points

 

If I were presenting this in an interview, the key things I'd emphasize:

 

1. **Pattern recognition**: "4 allowed digits" immediately suggests base-4 encoding. Whenever you see a problem with `k` choices at each position, think about base-`k` numbering.

 

2. **Order preservation**: The crucial property is that {0, 1, 4, 9} is sorted, so the mapping doesn't disturb the ordering.

 

3. **No need for BFS/generation**: Some candidates might try to generate valid numbers level by level (BFS-style: all 1-digit, then 2-digit, etc.). That works but is O(n) time and space. The base-4 approach is O(log n) -- strictly better.

 
