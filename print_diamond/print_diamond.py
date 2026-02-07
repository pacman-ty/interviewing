def print_line(n: int): 
    midpoint = n // 2

    for i in range(n):
        if midpoint >= i:
            ch = chr(ord('a') + i)
        else:
            ch = chr(ord('a') + (n - i - 1))
        print(ch, end='')

    print()
    
def print_diamond(n: int): 
    for i in range(1, n + 2, 2):
        spaces = (n - i) // 2 
        print(' ' * spaces, end='')
        print_line(i)

    for i in range(n - 2, 0, -2):
        spaces = (n - i) // 2 
        print(' ' * spaces, end='')
        print_line(i)

print_line(3)
print_line(5)
print_line(7)
print_line(9)

print_diamond(3)
print_diamond(5)
print_diamond(7)
print_diamond(9)

