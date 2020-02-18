#version 460

uniform vec2 resolution;
uniform sampler2D mask1;
uniform sampler2D mask2;

out vec4 out_color;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    uv.y = 1.0 - uv.y;
    vec3 color1 = texture2D(mask1, uv).rgb;
    vec3 color2 = texture2D(mask2, uv).rgb;
    vec3 color = vec3(color1.r, color1.r*color2.r, color2.r);

    out_color = vec4(color, 1.0);
}