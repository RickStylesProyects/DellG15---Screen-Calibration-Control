#version 140
uniform sampler2D sampler;
uniform float opacity;
in vec2 texcoord;
out vec4 fragColor;

// This value is replaced by the Python script
#define SATURATION_LEVEL 1.0

const vec3 lumaCoef = vec3(0.2126, 0.7152, 0.0722);

void main() {
    vec4 tex = texture(sampler, texcoord);
    
    // Calculate Luminance
    float luma = dot(tex.rgb, lumaCoef);
    vec3 gray = vec3(luma);
    
    // Apply Saturation (mix between gray and original color)
    vec3 satColor = mix(gray, tex.rgb, float(SATURATION_LEVEL));
    
    // Clamp to valid range
    satColor = clamp(satColor, 0.0, 1.0);
    
    // Output
    fragColor = vec4(satColor, tex.a) * opacity;
}
