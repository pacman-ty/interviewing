def solve(n):
    map = {0: 0, 1: 1, 2: 4, 3: 9}
    
    ans = 0 
    count = 1

    ans = ans + count * map[remainder]
    while(n): 
        remainder = n % 4 
        count = count * 10
        n = n // 4

    return ans 

print(solve(3))
print(solve(7))
