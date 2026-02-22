# Bad Code
def p(l):
    # Initialize the sum to zero
    a = 0
    
    # Iterate over each element in the list
    for i in l:
        # Add the current element to the sum
        a += i

    # Compute the average by dividing the sum by the number of elements in the list
    m = a/len(l)

    # Print the average
    print(m)


# Good Code
def calculate_average(number_list):
    if not number_list:
        raise ValueError("The list is empty.")

    total_sum = sum(number_list)
    average = total_sum / len(number_list)

    return average
