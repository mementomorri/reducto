#Bad Code
def foo(a):
  q = len(a)
    for i in range(len(a)):
	r = a[i]
	b = a[a[i]] % q
	a[i] = q*b + r
  for i in range(len(a)):
    a[i] = a[i] // q
  return a


#Good Code

def transform_list(input_list):
    transformed_list = []

    for value in input_list:
        transformed_value = transform_value(value)
        transformed_list.append(transformed_value)

    return transformed_list

def transform_value(value):
    length = len(value)
    transformed_value = value % length
    return length * transformed_value + value
