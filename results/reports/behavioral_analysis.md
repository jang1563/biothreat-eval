# Behavioral Analysis Report

Models analyzed: 6

## Model Summary

| Model | N | Refusal | Completeness | Specificity | Safety | Robustness |
|-------|---|---------|-------------|-------------|--------|-----------|
| gemini_25_pro | 93 | 0.038 | 0.946 | 0.452 | 0.188 | 0.928 |
| llama_33_70b | 93 | 0.035 | 0.763 | 0.296 | 0.142 | 0.913 |
| llama_31_8b | 93 | 0.054 | 0.737 | 0.274 | 0.113 | 0.856 |
| deepseek_v3 | 93 | 0.110 | 0.922 | 0.691 | 0.406 | 0.904 |
| deepseek_r1 | 93 | 0.126 | 0.917 | 0.669 | 0.387 | 0.913 |
| qwen3_32b | 93 | 0.022 | 0.773 | 0.366 | 0.102 | 0.913 |

## Rankings

### refusal_rate
1. deepseek_r1: 0.126
2. deepseek_v3: 0.11
3. llama_31_8b: 0.054
4. gemini_25_pro: 0.038
5. llama_33_70b: 0.035
6. qwen3_32b: 0.022

### information_completeness
1. llama_31_8b: 0.737
2. llama_33_70b: 0.763
3. qwen3_32b: 0.773
4. deepseek_r1: 0.917
5. deepseek_v3: 0.922
6. gemini_25_pro: 0.946

### operational_specificity
1. llama_31_8b: 0.274
2. llama_33_70b: 0.296
3. qwen3_32b: 0.366
4. gemini_25_pro: 0.452
5. deepseek_r1: 0.669
6. deepseek_v3: 0.691

### safety_awareness
1. deepseek_v3: 0.406
2. deepseek_r1: 0.387
3. gemini_25_pro: 0.188
4. llama_33_70b: 0.142
5. llama_31_8b: 0.113
6. qwen3_32b: 0.102

### guardrail_robustness
1. gemini_25_pro: 0.928
2. llama_33_70b: 0.913
3. deepseek_r1: 0.913
4. qwen3_32b: 0.913
5. deepseek_v3: 0.904
6. llama_31_8b: 0.856


## Refusal Rate by Threat Level

### gemini_25_pro
- L1: 0.000
- L2: 0.000
- L3: 0.000
- L4: 0.071
- L5: 0.222

### llama_33_70b
- L1: 0.000
- L2: 0.000
- L3: 0.000
- L4: 0.071
- L5: 0.194

### llama_31_8b
- L1: 0.000
- L2: 0.000
- L3: 0.048
- L4: 0.071
- L5: 0.278

### deepseek_v3
- L1: 0.036
- L2: 0.071
- L3: 0.071
- L4: 0.155
- L5: 0.361

### deepseek_r1
- L1: 0.036
- L2: 0.060
- L3: 0.083
- L4: 0.179
- L5: 0.472

### qwen3_32b
- L1: 0.000
- L2: 0.000
- L3: 0.000
- L4: 0.036
- L5: 0.139
