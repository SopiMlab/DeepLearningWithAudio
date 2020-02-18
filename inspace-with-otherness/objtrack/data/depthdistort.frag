#version 460

uniform vec2 resolution;
uniform sampler2D image;

out vec4 out_color;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    uv.y = 1.0 - uv.y;
    vec3 color = texture2D(image, uv).rgb;

    vec2 principal = vec2(0.0, 0.0);
    vec2 focalLength = vec2(531.15, 531.15);
    vec2 uv2 = (uv - principal) / focalLength;
    double r = sqrt(uv2.x*uv2.x + uv2.y*uv2.y);

    out_color = vec4(color, 1.0);
}