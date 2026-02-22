# Bad Code
def calculate(a, b):
    c = a + b
    d = c * 2
    e = d / 3
    return e

result = calculate(10, 5)
print(result)

# Good Code
def calculate_sum_double_divide(first_number, second_number):
    sum_of_numbers = first_number + second_number
    doubled_sum = sum_of_numbers * 2
    average = doubled_sum / 3
    return average
