#Bad Code

def f(n):
    if n <= 1:
        return 1
    else:
        return n * f(n - 1)

def p(l):
    a, b = 0, 1
    print("Fibonacci Sequence:", end="")
    while a <= l:
        print(" " + str(a), end="")
        next_val = a + b
        a = b
        b = next_val
    print()

    
#Good code

def calculate_factorial(num):
    if num <= 1:
        return 1
    else:
        return num * calculate_factorial(num - 1)

def print_fibonacci_sequence(limit):
    a, b = 0, 1
    print("Fibonacci Sequence:", end="")
    while a <= limit:
        print(" " + str(a), end="")
        next_val = a + b
        a = b
        b = next_val
    print()
