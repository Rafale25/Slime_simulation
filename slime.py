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
# import numpy as np

import moderngl
import imgui
import glm

import moderngl_window as mglw
# from moderngl_window.conf import settings
from moderngl_window.integrations.imgui import ModernglWindowRenderer

def random_uniform_vec2():
	angle = uniform(-math.pi, math.pi);
	return cos(angle), sin(angle);

RATIO_MULT = 100

class AgentConfig:
	N = 50000
	speed = 1.0
	color = (1, 1, 1)
	local_size_x = 512
	local_size_y = 1
	local_size_z = 1

class TextureConfig:
	size = (16*RATIO_MULT, 9*RATIO_MULT)
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
	window_size = (1280, 720)
	fullscreen = False
	resizable = False
	vsync = True
	resource_dir = "./resources"

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		imgui.create_context()
		self.imgui = ModernglWindowRenderer(self.wnd)

		self.width, self.height = self.window_size
		self.pause = False

		# data = array('B', [0, 0, 0, 255] * (TextureConfig.size[0] * TextureConfig.size[1]))
		data = array('f', [0.0, 0.0, 0.0, 1.0] * (TextureConfig.size[0] * TextureConfig.size[1]))

		# for i in range(0, TextureConfig.size[1]*TextureConfig.size[0]*4, 4):
		# 	index = int(i / 4)
		# 	x = index % (TextureConfig.size[0])
		# 	y = int(index / (TextureConfig.size[0]))

			# if x % 2 or y % 2:
			# 	data[i + 0] = 255
			# else:
			# 	data[i + 1] = 255

			# data[i + 0] = y%256
			# data[i + 1] = x%256
			# data[i + 2] = x%256
			# data[i + 3] = 255

		# texture
		self.texture = self.ctx.texture(
			size=TextureConfig.size,
			data=data,
			# data=array('B', [255, 0, 0, 255] * (TextureConfig.size[0] * TextureConfig.size[1])),
			components=4,
			dtype='f4')
			# dtype='u1')

		self.texture.repeat_x, self.texture.repeat_y = False, False
		self.texture.filter = moderngl.NEAREST, moderngl.NEAREST


		self.quad_2d = mglw.geometry.quad_2d(
			size=(TextureConfig.size[0], TextureConfig.size[1]),
			pos=(TextureConfig.size[0]/2, TextureConfig.size[1]/2),
			normals=False)
		# self.quad_2d = mglw.geometry.quad_fs() #screen sized quad
		self.shader_texture = self.load_program(
			vertex_shader="./texture.vert",
			fragment_shader="./texture.frag"
		)

		# agent : Vec2 position, float angle, float useless_for_padding
		self.buffer_agent = self.ctx.buffer(array('f', self.gen_initial_ant_data(AgentConfig.N)))

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

	def update_uniforms(self, frametime):
		self.CS_agent['timer'] = time.time() * 1e6
		self.CS_agent['nb_agent'] = AgentConfig.N
		self.CS_agent['speed'] = AgentConfig.speed

		self.CS_texture['width'] = TextureConfig.size[0]
		self.CS_texture['height'] = TextureConfig.size[1]
		pass

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
	# data initialization
	def gen_initial_ant_data(self, count):
		for _ in range(count):
			# position
			yield TextureConfig.size[0]/2
			yield TextureConfig.size[1]/2

			vec = random_uniform_vec2()
			yield vec[0]
			yield vec[1]

			# yield random.uniform(-math.pi, math.pi)
			# yield 0 # unused

	# -------------------------------------------------------------------------
	# IMGUI
	def imgui_newFrame(self):
		imgui.new_frame()
		imgui.begin("Properties", True)

		c, self.pause = imgui.checkbox("Paused", self.pause)

		imgui.spacing();imgui.spacing();imgui.separator();imgui.spacing();imgui.spacing()
		imgui.text("Agents Settings"); imgui.spacing()

		imgui.begin_group()
		c, AgentConfig.speed = imgui.slider_float(
			label="Speed",
			value=AgentConfig.speed,
			min_value=0.01,
			max_value=10.0,
			format="%.2f")
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
