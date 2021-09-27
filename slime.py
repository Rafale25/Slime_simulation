#! /usr/bin/python3

import sys
import math
import random
import struct
import time
import pathlib

from math import pi, cos, sin
from random import uniform
from array import array

import moderngl
import imgui
import glm

import moderngl_window as mglw
# from moderngl_window.conf import settings
from moderngl_window.integrations.imgui import ModernglWindowRenderer

def random_uniform_vec2():
	angle = uniform(-math.pi, math.pi);
	return cos(angle), sin(angle);

RATIO_MULT = 120

class AgentConfig:
	N = 100_000
	speed = 4.0
	steer = 1.0
	sensorAngleSpacing = math.pi/4# 0 to PI/2
	# sensorSize = 1# 0 to PI/2
	sensorDistance = 16

	local_size_x = 512
	local_size_y = 1
	local_size_z = 1

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

class MyWindow(mglw.WindowConfig):
	title = "Slime Simulation"
	gl_version = (4, 3)
	window_size = (Camera.ratio[0] * RATIO_MULT, Camera.ratio[1] * RATIO_MULT)
	fullscreen = False
	resizable = False
	vsync = True
	resource_dir = "./resources"

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		imgui.create_context()
		self.imgui = ModernglWindowRenderer(self.wnd)

		self.width, self.height = self.window_size
		self.pause = True

		# texture
		self.texture = self.ctx.texture(
			size=TextureConfig.size,
			data=array('f', [0.0, 0.0, 0.0, 1.0] * (TextureConfig.size[0] * TextureConfig.size[1])),
			components=4,
			dtype='f4')

		self.texture.repeat_x, self.texture.repeat_y = False, False
		self.texture.filter = moderngl.NEAREST, moderngl.NEAREST

		self.quad_2d = mglw.geometry.quad_2d(
			size=(TextureConfig.size[0], TextureConfig.size[1]),
			pos=(TextureConfig.size[0]/2, TextureConfig.size[1]/2),
			normals=False)
		self.shader_texture = self.load_program(
			vertex_shader="./texture.vert",
			fragment_shader="./texture.frag"
		)

		# agent : vec2 position, vec2 direction
		self.buffer_agent = self.ctx.buffer(array('f', self.gen_initial_data(AgentConfig.N)))

		self.CS_agent = self.load_compute_shader(
			'./agent.comp',
			{
				"texture_width": TextureConfig.size[0],
				"texture_height": TextureConfig.size[1],
				"l_size_x": AgentConfig.local_size_x,
			}
		)
		self.CS_texture = self.load_compute_shader(
			'./texture.comp',
			{
				"l_size_x": TextureConfig.local_size_x,
				"l_size_y": TextureConfig.local_size_y,
				"l_size_z": TextureConfig.local_size_z
			}
		)

	def __del__(self):
		print("Cleaning up ressources.")
		self.shader_texture.release()
		self.buffer_agent.release()
		self.CS_agent.release()
		self.CS_texture.release()

	def update_uniforms(self, frametime):
		self.CS_agent['timer'] = (time.time() * 100000) % 2_147_483_647 # dont exceed int_max
		self.CS_agent['nb_agent'] = AgentConfig.N
		self.CS_agent['speed'] = AgentConfig.speed
		self.CS_agent['steerStrength'] = AgentConfig.steer
		self.CS_agent['sensorAngleSpacing'] = AgentConfig.sensorAngleSpacing
		# self.CS_agent['sensorSize'] = AgentConfig.sensorSize
		self.CS_agent['sensorDistance'] = AgentConfig.sensorDistance

		self.CS_texture['width'] = TextureConfig.size[0]
		self.CS_texture['height'] = TextureConfig.size[1]
		self.CS_texture['diffuse'] = TextureConfig.diffuse
		self.CS_texture['evaporation'] = TextureConfig.evaporation

		self.shader_texture['color_1'] = TextureConfig.color_1
		self.shader_texture['color_2'] = TextureConfig.color_2
		self.shader_texture['color_3'] = TextureConfig.color_3

	def update(self, time, frametime):
		self.update_uniforms(frametime)
		self.buffer_agent.bind_to_storage_buffer(0)
		self.texture.bind_to_image(0, read=True, write=True)

		self.CS_agent.run(
			group_x=AgentConfig.N // AgentConfig.local_size_x + 1,
			group_y=1,
			group_z=1
		)

		self.CS_texture.run(
			group_x=TextureConfig.size[0] // TextureConfig.local_size_x + 1,
			group_y=TextureConfig.size[1] // TextureConfig.local_size_y + 1,
			group_z=1
		)

	def render(self, time, frametime):
		if not self.pause:
			self.update(time, frametime)

		self.ctx.clear(0.5, 0.5, 0.5)

		# modelview = glm.ortho(
		# 	Camera.center[0] - Camera.ratio[0]/2 * Camera.zoom,
		# 	Camera.center[0] + Camera.ratio[0]/2 * Camera.zoom,
		# 	Camera.center[1] - Camera.ratio[1]/2 * Camera.zoom,
		# 	Camera.center[1] + Camera.ratio[1]/2 * Camera.zoom,
		# 	-1, 1)
		modelview = glm.ortho(0, TextureConfig.size[0], 0, TextureConfig.size[1], -1, 1)
		self.shader_texture['modelview'].write(modelview)

		self.texture.use(location=0)
		self.quad_2d.render(self.shader_texture)

		self.imgui_newFrame()
		self.imgui_render()

	# -------------------------------------------------------------------------
	def resize_buffer(self, new_count):
		AGENT_SIZE_BYTES = 4 * 4
		buffer = self.buffer_agent.read()[0:new_count * AGENT_SIZE_BYTES]

		self.buffer_agent.orphan(new_count * AGENT_SIZE_BYTES)

		if new_count > AgentConfig.N:
			new_bytes = array('f', self.gen_initial_data(new_count - AgentConfig.N))
			buffer += new_bytes

		self.buffer_agent.write(buffer)

		AgentConfig.N = new_count

	# data initialization
	def gen_initial_data(self, count):
		for _ in range(count):
			# position
			vec = random_uniform_vec2()
			dist = random.uniform(0, 200)
			yield TextureConfig.size[0]/2 + vec[0] * dist
			yield TextureConfig.size[1]/2 + vec[1] * dist

			# direction
			vec = random_uniform_vec2()
			yield vec[0]
			yield vec[1]

	# -------------------------------------------------------------------------
	# IMGUI
	def imgui_newFrame(self):
		imgui.new_frame()
		imgui.begin("Properties", True)

		c, self.pause = imgui.checkbox("Paused", self.pause)

		imgui.spacing();imgui.spacing();imgui.separator();imgui.spacing();imgui.spacing()

		imgui.text("Agents Settings"); imgui.spacing()
		imgui.begin_group()
		c, new_N = imgui.slider_int(
			label="N",
			value=AgentConfig.N,
			min_value=1,
			max_value=1_000_000)
		if c:
			self.resize_buffer(new_N)

		c, AgentConfig.speed = imgui.slider_float(
			label="Speed",
			value=AgentConfig.speed,
			min_value=0.01,
			max_value=10.0,
			format="%.2f")

		c, AgentConfig.steer = imgui.slider_float(
			label="SteerStrength",
			value=AgentConfig.steer,
			min_value=0.01,
			max_value=5.0,
			format="%.3f")

		c, AgentConfig.sensorAngleSpacing = imgui.slider_float(
			label="SensorAngleSpacing",
			value=AgentConfig.sensorAngleSpacing,
			min_value=0.1,
			max_value=math.pi,
			format="%.2f")

		# c, AgentConfig.sensorSize = imgui.slider_int(
		# 	label="SensorSize",
		# 	value=AgentConfig.sensorSize,
		# 	min_value=1,
		# 	max_value=2)

		c, AgentConfig.sensorDistance = imgui.slider_int(
			label="SensorDistance",
			value=AgentConfig.sensorDistance,
			min_value=0,
			max_value=100)

		c, TextureConfig.color_1 = imgui.color_edit3("Color 1", *TextureConfig.color_1)
		c, TextureConfig.color_2 = imgui.color_edit3("Color 2", *TextureConfig.color_2)
		c, TextureConfig.color_3 = imgui.color_edit3("Color 3", *TextureConfig.color_3)

		imgui.end_group()

		imgui.text("Texture Settings"); imgui.spacing()
		imgui.begin_group()
		c, TextureConfig.diffuse = imgui.slider_float(
			label="Diffuse",
			value=TextureConfig.diffuse,
			min_value=0.0,
			max_value=1.0,
			format="%.2f")

		c, TextureConfig.evaporation = imgui.slider_float(
			label="Decay",
			value=TextureConfig.evaporation,
			min_value=0.0,
			max_value=0.1,
			format="%.4f")
		imgui.end_group()

		imgui.end()

	def imgui_render(self):
		imgui.render()
		self.imgui.render(imgui.get_draw_data())

	# -------------------------------------------------------------------------
	# EVENTS
	def resize(self, width: int, height: int):
		self.imgui.resize(width, height)

	def key_event(self, key, action, modifiers):
		self.imgui.key_event(key, action, modifiers)

	def mouse_position_event(self, x, y, dx, dy):
		self.imgui.mouse_position_event(x, y, dx, dy)

	def mouse_drag_event(self, x, y, dx, dy):
		self.imgui.mouse_drag_event(x, y, dx, dy)
		Camera.center[0] += -dx
		Camera.center[1] += dy

	def mouse_scroll_event(self, x_offset, y_offset):
		self.imgui.mouse_scroll_event(x_offset, y_offset)
		Camera.zoom += y_offset * 10
		if Camera.zoom < 1.0:
			Camera.zoom = 1.0

	def mouse_press_event(self, x, y, button):
		self.imgui.mouse_press_event(x, y, button)

	def mouse_release_event(self, x: int, y: int, button: int):
		self.imgui.mouse_release_event(x, y, button)

	def unicode_char_entered(self, char):
		self.imgui.unicode_char_entered(char)


def main():
	MyWindow.run()

if __name__ == "__main__":
	main()
