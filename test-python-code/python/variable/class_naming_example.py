# Bad code
class A:
    def m(self):
        pass

class B(A):
    def n(self):
        pass

class C(B):
    def o(self):
        pass

# Good code
class Vehicle:
    def move(self):
        pass

class Car(Vehicle):
    def accelerate(self):
        pass

class ElectricCar(Car):
    def charge(self):
        pass
