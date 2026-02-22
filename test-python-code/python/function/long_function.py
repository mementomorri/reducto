#Bad Code

def process_data(input_data):
    # This function processes the input data to generate an output result, but it's extremely long and hard to follow

    result = []

    for i in range(len(input_data)):
        item = input_data[i]
        if item % 2 == 0:
            item *= 2
        else:
            item = item + 1

        if item > 10:
            item = item - 10

        for j in range(i + 1, len(input_data)):
            next_item = input_data[j]
            if next_item < item:
                result.append(next_item)

        if i % 3 == 0:
            item = item / 2
        elif i % 3 == 1:
            item = item / 3
        else:
            item = item / 4

        if item < 5:
            item = item + 10

        result.append(item)

    return result
  
  #Good Code
  def process_data(input_data):
    # This function processes the input data to generate an output result

    processed_data = apply_operations(input_data)
    filtered_data = filter_values(processed_data)
    transformed_data = transform_values(filtered_data)

    return transformed_data


def apply_operations(data):
    # Apply operations to the data

    result = []

    for item in data:
        if item % 2 == 0:
            item *= 2
        else:
            item += 1

        if item > 10:
            item -= 10

        result.append(item)

    return result


def filter_values(data):
    # Filter values based on certain conditions

    result = []

    for i in range(len(data)):
        item = data[i]
        for j in range(i + 1, len(data)):
            next_item = data[j]
            if next_item < item:
                result.append(next_item)

    return result


def transform_values(data):
    # Transform values based on specific rules

    result = []

    for i, item in enumerate(data):
        if i % 3 == 0:
            item /= 2
        elif i % 3 == 1:
            item /= 3
        else:
            item /= 4

        if item < 5:
            item += 10

        result.append(item)

    return result

