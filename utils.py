from random import uniform
from math import pi, cos, sin

def random_uniform_vec2():
	angle = uniform(-pi, pi)
	return cos(angle), sin(angle)
