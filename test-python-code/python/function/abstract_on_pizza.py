#Bad Code
def make_pizza():
    # Mix the ingredients for the dough
    flour = 2  # cups
    water = 1  # cup
    yeast = 0.25  # teaspoon
    salt = 1  # teaspoon
    dough = flour + water + yeast + salt

    # Knead the dough
    for i in range(10):
        dough *= 2  # Knead the dough by doubling its volume

    # Roll out the dough
    dough_thickness = 0.25  # inch
    dough = dough / dough_thickness

    # Apply the tomato sauce
    sauce = 0.5  # cups
    pizza = dough + sauce  # Add sauce to the dough

    # Add the cheese
    cheese = 1.5  # cups
    pizza += cheese  # Add cheese to the pizza

    # Preheat the oven
    oven_temperature = 450  # Fahrenheit

    # Set the timer for baking
    timer = 20  # 20 minutes

    # Bake the pizza in the oven
    baking_time = 0
    while baking_time < timer:
        pizza += oven_temperature  # This is a very crude representation of baking
        baking_time += 1

    return pizza
    
#Good Code

def make_pizza():
    prepare_dough()
    apply_tomato_sauce()
    add_cheese()
    bake_in_oven()

def prepare_dough():
    mix_ingredients()
    knead_dough()
    roll_out_dough()

def mix_ingredients():
    # Details of mixing flour, water, yeast etc.

def knead_dough():
    # Details of kneading the dough to make it smooth

def roll_out_dough():
    # Details of rolling the dough to the right thickness

def apply_tomato_sauce():
    # Details of applying tomato sauce on the rolled out dough

def add_cheese():
    # Details of adding cheese on the tomato sauce

def bake_in_oven():
    preheat_oven()
    set_timer()
    place_pizza_in_oven()

def preheat_oven():
    # Details of preheating the oven to the right temperature

def set_timer():
    # Details of setting the timer to the correct baking time

def place_pizza_in_oven():
    # Details of placing the pizza in the oven safely
