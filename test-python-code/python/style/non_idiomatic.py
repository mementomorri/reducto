"""
Non-idiomatic Python code for idiomatization testing.
Each example shows anti-patterns that should be transformed.
"""

# BAD: For-loop instead of list comprehension
def get_even_numbers(numbers):
    evens = []
    for num in numbers:
        if num % 2 == 0:
            evens.append(num)
    return evens


# GOOD: List comprehension
def get_even_numbers_idiomatic(numbers):
    return [num for num in numbers if num % 2 == 0]


# BAD: String concatenation instead of f-string
def create_greeting(name, age, city):
    return "Hello, " + name + "! You are " + str(age) + " years old and live in " + city + "."


# GOOD: F-string
def create_greeting_idiomatic(name, age, city):
    return f"Hello, {name}! You are {age} years old and live in {city}."


# BAD: Manual file handling instead of context manager
def read_file_contents(filepath):
    file = open(filepath, "r")
    try:
        content = file.read()
    finally:
        file.close()
    return content


# GOOD: Context manager
def read_file_contents_idiomatic(filepath):
    with open(filepath, "r") as file:
        return file.read()


# BAD: Dictionary building with loop instead of dict comprehension
def create_square_dict(numbers):
    result = {}
    for num in numbers:
        result[num] = num * num
    return result


# GOOD: Dict comprehension
def create_square_dict_idiomatic(numbers):
    return {num: num * num for num in numbers}


# BAD: Using index in for-loop
def print_with_index(items):
    for i in range(len(items)):
        print(str(i) + ": " + str(items[i]))


# GOOD: Using enumerate
def print_with_index_idiomatic(items):
    for i, item in enumerate(items):
        print(f"{i}: {item}")


# BAD: Multiple if statements instead of any/all
def has_positive_number(numbers):
    for num in numbers:
        if num > 0:
            return True
    return False


# GOOD: Using any()
def has_positive_number_idiomatic(numbers):
    return any(num > 0 for num in numbers)


# BAD: Checking empty list with len
def is_not_empty(items):
    if len(items) > 0:
        return True
    return False


# GOOD: Truthiness check
def is_not_empty_idiomatic(items):
    return bool(items)


# BAD: Nested conditionals for default value
def get_config_value(config, key):
    if key in config:
        return config[key]
    else:
        return None


# GOOD: Using dict.get()
def get_config_value_idiomatic(config, key):
    return config.get(key)


# BAD: List to string conversion
def join_words(words):
    result = ""
    for i, word in enumerate(words):
        if i > 0:
            result = result + " "
        result = result + word
    return result


# GOOD: Using str.join()
def join_words_idiomatic(words):
    return " ".join(words)


# BAD: Reversed range for iteration
def process_reverse(items):
    result = []
    for i in range(len(items) - 1, -1, -1):
        result.append(items[i])
    return result


# GOOD: Using reversed()
def process_reverse_idiomatic(items):
    return list(reversed(items))


# BAD: Manual counter instead of itertools
def get_pairs(list1, list2):
    pairs = []
    for item1 in list1:
        for item2 in list2:
            pairs.append((item1, item2))
    return pairs


# GOOD: Using itertools.product (or list comprehension)
def get_pairs_idiomatic(list1, list2):
    return [(a, b) for a in list1 for b in list2]


# BAD: Checking multiple values with or chain
def is_weekend(day):
    if day == "Saturday" or day == "Sunday":
        return True
    return False


# GOOD: Using in operator
def is_weekend_idiomatic(day):
    return day in ("Saturday", "Sunday")
