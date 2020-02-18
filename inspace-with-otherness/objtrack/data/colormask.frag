#version 460

uniform vec2 resolution;
uniform sampler2D image;
uniform vec3 target_hsl_min;
uniform vec3 target_hsl_max;

out vec4 out_color;

vec3 rgb2hsl(vec3 rgb) {
    float r = rgb.r;
    float g = rgb.g;
    float b = rgb.b;
    float v, m, vm, r2, g2, b2;
    float h = 0.0;
    float s = 0.0;
    float l = 0.0;
    v = max(max(r, g), b);
    m = min(min(r, g), b);
    l = (m + v) / 2.0;
    if(l > 0.0) {
        vm = v - m;
        s = vm;
        if(s > 0.0) {
            s /= (l <= 0.5) ? (v + m) : (2.0 - v - m);
            r2 = (v - r) / vm;
            g2 = (v - g) / vm;
            b2 = (v - b) / vm;
            if(r == v) {
                h = (g == m ? 5.0 + b2 : 1.0 - g2);
            } else if(g == v) {
                h = (b == m ? 1.0 + r2 : 3.0 - b2);
            } else {
                h = (r == m ? 3.0 + g2 : 5.0 - r2);
            }
        }
    }
    h /= 6.0;
    return vec3(h, s, l);
}

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    uv.y = 1.0 - uv.y;
    vec3 color = texture2D(image, uv).rgb;

    vec3 color_hsl = rgb2hsl(color);
    bool hue_match = target_hsl_min.x <= target_hsl_max.x
      ? target_hsl_min.x <= color_hsl.x && color_hsl.x <= target_hsl_max.x
      : target_hsl_min.x <= color_hsl.x || color_hsl.x <= target_hsl_max.x;
    bool sat_match = target_hsl_min.y <= color_hsl.y && color_hsl.y <= target_hsl_max.y;
    bool light_match = target_hsl_min.z <= color_hsl.z && color_hsl.z <= target_hsl_max.z;

    bool match = hue_match && sat_match && light_match;
    
    float value = match ? 1.0 : 0.0;
    
    out_color = vec4(vec3(value), 1.0);
}