# shape.pyi
from typing import Protocol

class Shape(Protocol):
    def area(self) -> float: ...

class Circle(Shape):
    def __init__(self, radius: float) -> None: ...
    def area(self) -> float: ...

def create_circle(radius: float) -> Circle: ...

class Square(Shape):
    def __init__(self, side: float) -> None: ...
    def area(self) -> float: ...

def create_square(side: float) -> Square: ...

class Triangle(Shape):
    def __init__(self, base: float, height: float) -> None: ...
    def area(self) -> float: ...

def create_triangle(base: float, height: float) -> Triangle: ...
