#version 460

uniform vec2 resolution;
uniform sampler2D image1;
uniform sampler2D image2;

out vec4 out_color;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    uv.y = 1.0 - uv.y;
    vec3 color1 = texture2D(image1, uv).rgb;
    vec3 color2 = texture2D(image2, uv).rgb;

    out_color = vec4(color1*color2, 1.0);
}