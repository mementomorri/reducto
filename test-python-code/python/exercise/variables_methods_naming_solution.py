from typing import List, Any, Optional

def recursive_sum(elements: List[int]) -> int:
    """
    Recursive function to calculate the sum of a list.
    """
    if not elements:
        return 0
    return elements[0] + recursive_sum(elements[1:])

def square_elements(elements: List[int]) -> List[int]:
    """
    Calculate the square of each element in a list.
    """
    return [x**2 for x in elements]

def find_maximum(elements: List[int]) -> int:
    """
    Find the maximum element in a list.
    """
    return max(elements)

def find_minimum(elements: List[int]) -> int:
    """
    Find the minimum element in a list.
    """
    return min(elements)

def count_occurrences(elements: List[Any], element: Any) -> int:
    """
    Count the occurrences of an element in a list.
    """
    return elements.count(element)

def remove_duplicates(elements: List[Any]) -> List[Any]:
    """
    Remove duplicates from a list.
    """
    return list(set(elements))

def sort_list(elements: List[Any]) -> List[Any]:
    """
    Sort a list in ascending order.
    """
    return sorted(elements)

def reverse_list(elements: List[Any]) -> List[Any]:
    """
    Reverse a list.
    """
    return elements[::-1]

def concatenate_lists(list1: List[Any], list2: List[Any]) -> List[Any]:
    """
    Concatenate two lists.
    """
    return list1 + list2

def is_sorted(elements: List[int]) -> bool:
    """
    Check if a list is sorted in ascending order.
    """
    return elements == sorted(elements)

def find_index(elements: List[Any], element: Any) -> int:
    """
    Find the index of an element in a list.
    """
    return elements.index(element) if element in elements else -1

def insert_element(elements: List[Any], element: Any, index: int) -> List[Any]:
    """
    Insert an element at a specific index in a list.
    """
    elements.insert(index, element)
    return elements
