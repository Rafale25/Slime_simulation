#version 430

in vec3 in_position;
in vec2 in_texcoord_0;
out vec2 uv;

uniform mat4 modelview;

void main() {
	gl_Position = modelview * vec4(in_position, 1.0);
	// gl_Position = vec4(in_position, 1.0);
	uv = in_texcoord_0;
}
