#version 460

uniform vec2 resolution;
uniform sampler2D colorImage;
uniform sampler2D depthImage;
uniform float nearZ;
uniform float farZ;
uniform float xScale;
uniform float xTranslate;
uniform float yScale;
uniform float yTranslate;

out vec4 out_color;

vec4 safeTex(sampler2D image, vec2 uv) {
    return 0.0 <= uv.x && uv.x < 1.0 && 0.0 <= uv.y && uv.y < 1.0
        ? texture2D(image, uv)
        : vec4(0.0);
}

void main() {
    vec2 xy = gl_FragCoord.xy;
    xy.y = resolution.y - xy.y;
    xy *= vec2(xScale, yScale);
    xy += vec2(xTranslate, yTranslate);
    vec2 uv = xy / resolution;
    vec3 color = safeTex(depthImage, uv).rgb;

    float z = color.x;
    if(nearZ < z || z < farZ) {
        color *= vec3(1.0, 0.0, 0.0);
    }

    vec2 uv1 = gl_FragCoord.xy / resolution;
    uv1.y = 1.0 - uv1.y;
    vec3 color1 = safeTex(colorImage, uv1).rgb;
    color1 = vec3(0.2989*color1.r + 0.587*color1.g + 0.114*color1.b);
    color1 = color1 * 0.5 + 0.5;
    color *= color1;

    //color = vec3(uv, 0.0);
    
    out_color = vec4(color, 1.0);
}