#version 430

uniform sampler2D texture0;
out vec4 fragColor;
in vec2 uv;

void main() {
	// vec4 color = texture(texture0, uv).rgba;
	float color = texture(texture0, uv).r;

	fragColor = vec4(0, color, 0, 1);
	// fragColor = vec4(
	// 	float(color.r) / 255,
	// 	float(color.g) / 255,
	// 	float(color.b) / 255,
	// 	float(color.a) / 255
	// );
}
