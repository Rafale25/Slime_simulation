#version 430

uniform sampler2D texture0;
out vec4 fragColor;
in vec2 uv;

uniform vec3 color_1;
uniform vec3 color_2;
uniform vec3 color_3;

vec4 color_transition(vec4 firstColor, vec4 secondColor, vec4 thirdColor, float value) {
	float h = 0.5; // adjust position of middleColor
	vec4 color = mix(mix(firstColor, secondColor, value/h), mix(secondColor, thirdColor, (value - h)/(1.0 - h)), step(h, value));
	return color;
}

void main() {
	float value = texture(texture0, uv).r;

	vec4 color = color_transition(vec4(color_1, 1.0), vec4(color_2, 1.0), vec4(color_3, 1.0), value);

	fragColor = color;
}
