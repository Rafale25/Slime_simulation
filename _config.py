import math

RATIO_MULT = 80

class AgentConfig:
	N = 100_000
	SPEED = 4.0
	STEER = 1.0
	SENSORANGLESPACING = math.pi/4# 0 to PI/2
	SENSORDISTANCE = 16

	def __init__(self):
		self.n = AgentConfig.N
		self.speed = AgentConfig.SPEED
		self.steer = AgentConfig.STEER
		self.sensorAngleSpacing = AgentConfig.SENSORANGLESPACING
		self.sensorDistance = AgentConfig.SENSORDISTANCE

class TextureConfig:
	size = (16*RATIO_MULT, 9*RATIO_MULT)
	diffuse = 0.7
	evaporation = 0.05

	color_1 = (0, 0, 0)
	color_2 = (0, 0.5, 0)
	color_3 = (0, 1, 0)

	local_size_x = 32
	local_size_y = 32
	local_size_z = 1

class Camera:
	center = [0, 0]
	ratio = (16, 9)
	zoom = 80.0
