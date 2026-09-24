## Setup

- **11 model(s)**: codestral-2508, dots-studio/dots-3-note-preview:free, google/gemma-4-31b-it:free, ministral-14b-2512, ministral-3b-2512, ministral-8b-2512, nex-agi/nex-n2.5-mini:free, openai/gpt-oss-120b, poolside/laguna-s-2.1:free, qwen/qwen3.8-27b, z-ai/glm-5.2:free
- **17 task(s)**: 103, 11, 135, 227, 257, 285, 390, 418, 444, 75, django__django-11066, django__django-17029, pydata__xarray-4629, scikit-learn__scikit-learn-13439, sympy__sympy-13480, sympy__sympy-14711, sympy__sympy-18189
- **174 run(s)** with usable data

## Results

| Model | Task | Result | Iterations | Tokens in | Tokens out | Wall time | Stopped because | Evidence |
|---|---|---|---:|---:|---:|---:|---|---|
| codestral-2508 | django__django-11066 | pass | 7 | 16,294 | 405 | 12.7s | solved | `runs/codestral-2508__django__django-11066.json` |
| codestral-2508 | django__django-17029 | fail | 30 | 137,356 | 6,504 | 83.5s | Iterations limit reached | `runs/codestral-2508__django__django-17029.json` |
| codestral-2508 | 103 | fail | 5 | 3,935 | 435 | 8.4s | Iterations limit reached | `runs/codestral-2508__mbpp-103.json` |
| codestral-2508 | 11 | pass | 2 | 1,040 | 158 | 3.2s | solved | `runs/codestral-2508__mbpp-11.json` |
| codestral-2508 | 135 | pass | 2 | 956 | 54 | 1.5s | solved | `runs/codestral-2508__mbpp-135.json` |
| codestral-2508 | 227 | pass | 2 | 995 | 60 | 1.3s | solved | `runs/codestral-2508__mbpp-227.json` |
| codestral-2508 | 257 | pass | 2 | 980 | 46 | 1.0s | solved | `runs/codestral-2508__mbpp-257.json` |
| codestral-2508 | 285 | fail | 5 | 3,465 | 190 | 4.0s | Iterations limit reached | `runs/codestral-2508__mbpp-285.json` |
| codestral-2508 | 390 | pass | 2 | 1,079 | 60 | 1.2s | solved | `runs/codestral-2508__mbpp-390.json` |
| codestral-2508 | 418 | pass | 2 | 1,040 | 54 | 1.1s | solved | `runs/codestral-2508__mbpp-418.json` |
| codestral-2508 | 444 | fail | 5 | 5,035 | 135 | 2.7s | Iterations limit reached | `runs/codestral-2508__mbpp-444.json` |
| codestral-2508 | 75 | pass | 2 | 1,174 | 114 | 1.4s | solved | `runs/codestral-2508__mbpp-75.json` |
| codestral-2508 | pydata__xarray-4629 | pass | 7 | 31,343 | 364 | 11.4s | solved | `runs/codestral-2508__pydata__xarray-4629.json` |
| codestral-2508 | scikit-learn__scikit-learn-13439 | fail | 30 | 166,619 | 2,440 | 162.7s | Iterations limit reached | `runs/codestral-2508__scikit-learn__scikit-learn-13439.json` |
| codestral-2508 | sympy__sympy-13480 | pass | 18 | 53,494 | 1,268 | 149.0s | solved | `runs/codestral-2508__sympy__sympy-13480.json` |
| codestral-2508 | sympy__sympy-14711 | fail | 16 | 273,344 | 1,558 | 46.7s | Input token limit reached | `runs/codestral-2508__sympy__sympy-14711.json` |
| codestral-2508 | sympy__sympy-18189 | pass | 16 | 55,618 | 914 | 144.0s | solved | `runs/codestral-2508__sympy__sympy-18189.json` |
| dots-studio/dots-3-note-preview:free | django__django-11066 | pass | 8 | 19,715 | 963 | 32.4s | solved | `runs/dots-studio-dots-3-note-preview:free__django__django-11066.json` |
| dots-studio/dots-3-note-preview:free | django__django-17029 | pass | 10 | 23,224 | 1,648 | 41.3s | solved | `runs/dots-studio-dots-3-note-preview:free__django__django-17029.json` |
| dots-studio/dots-3-note-preview:free | 103 | fail | 1 | 471 | 1,500 | 21.4s | Output token limit reached | `runs/dots-studio-dots-3-note-preview:free__mbpp-103.json` |
| dots-studio/dots-3-note-preview:free | 11 | fail | 1 | 472 | 1,500 | 20.3s | Output token limit reached | `runs/dots-studio-dots-3-note-preview:free__mbpp-11.json` |
| dots-studio/dots-3-note-preview:free | 135 | pass | 2 | 972 | 392 | 10.5s | solved | `runs/dots-studio-dots-3-note-preview:free__mbpp-135.json` |
| dots-studio/dots-3-note-preview:free | 227 | pass | 2 | 1,023 | 300 | 8.8s | solved | `runs/dots-studio-dots-3-note-preview:free__mbpp-227.json` |
| dots-studio/dots-3-note-preview:free | 257 | pass | 2 | 990 | 152 | 7.4s | solved | `runs/dots-studio-dots-3-note-preview:free__mbpp-257.json` |
| dots-studio/dots-3-note-preview:free | 285 | fail | 1 | 470 | 1,120 | 18.4s | Output token limit reached | `runs/dots-studio-dots-3-note-preview:free__mbpp-285.json` |
| dots-studio/dots-3-note-preview:free | 390 | pass | 2 | 1,080 | 641 | 13.4s | solved | `runs/dots-studio-dots-3-note-preview:free__mbpp-390.json` |
| dots-studio/dots-3-note-preview:free | 418 | pass | 2 | 1,031 | 384 | 12.1s | solved | `runs/dots-studio-dots-3-note-preview:free__mbpp-418.json` |
| dots-studio/dots-3-note-preview:free | 444 | fail | 1 | 631 | 1,178 | 18.1s | Output token limit reached | `runs/dots-studio-dots-3-note-preview:free__mbpp-444.json` |
| dots-studio/dots-3-note-preview:free | 75 | pass | 2 | 1,151 | 404 | 11.1s | solved | `runs/dots-studio-dots-3-note-preview:free__mbpp-75.json` |
| dots-studio/dots-3-note-preview:free | pydata__xarray-4629 | pass | 6 | 29,261 | 690 | 27.0s | solved | `runs/dots-studio-dots-3-note-preview:free__pydata__xarray-4629.json` |
| dots-studio/dots-3-note-preview:free | scikit-learn__scikit-learn-13439 | fail | 30 | 151,436 | 2,800 | 320.2s | Iterations limit reached | `runs/dots-studio-dots-3-note-preview:free__scikit-learn__scikit-learn-13439.json` |
| dots-studio/dots-3-note-preview:free | sympy__sympy-13480 | pass | 10 | 18,485 | 1,355 | 157.2s | solved | `runs/dots-studio-dots-3-note-preview:free__sympy__sympy-13480.json` |
| dots-studio/dots-3-note-preview:free | sympy__sympy-14711 | fail | 30 | 145,751 | 6,319 | 124.0s | Iterations limit reached | `runs/dots-studio-dots-3-note-preview:free__sympy__sympy-14711.json` |
| dots-studio/dots-3-note-preview:free | sympy__sympy-18189 | pass | 30 | 193,802 | 5,141 | 230.3s | solved | `runs/dots-studio-dots-3-note-preview:free__sympy__sympy-18189.json` |
| google/gemma-4-31b-it:free | django__django-11066 | fail | 2 | 5,803 | 2,301 | 234.1s | Agent loop error | `runs/google-gemma-4-31b-it:free__django__django-11066.json` |
| google/gemma-4-31b-it:free | django__django-17029 | fail | 10 | 11,634 | 490 | 809.2s | Agent loop error | `runs/google-gemma-4-31b-it:free__django__django-17029.json` |
| google/gemma-4-31b-it:free | 103 | pass | 2 | 1,455 | 589 | 95.5s | solved | `runs/google-gemma-4-31b-it:free__mbpp-103.json` |
| google/gemma-4-31b-it:free | 11 | pass | 2 | 1,233 | 313 | 135.5s | solved | `runs/google-gemma-4-31b-it:free__mbpp-11.json` |
| google/gemma-4-31b-it:free | 135 | pass | 2 | 1,085 | 94 | 188.7s | solved | `runs/google-gemma-4-31b-it:free__mbpp-135.json` |
| google/gemma-4-31b-it:free | 227 | pass | 2 | 1,131 | 129 | 87.8s | solved | `runs/google-gemma-4-31b-it:free__mbpp-227.json` |
| google/gemma-4-31b-it:free | 257 | pass | 2 | 1,089 | 57 | 131.7s | solved | `runs/google-gemma-4-31b-it:free__mbpp-257.json` |
| google/gemma-4-31b-it:free | 285 | pass | 2 | 1,225 | 221 | 147.7s | solved | `runs/google-gemma-4-31b-it:free__mbpp-285.json` |
| google/gemma-4-31b-it:free | 390 | pass | 2 | 1,183 | 77 | 92.4s | solved | `runs/google-gemma-4-31b-it:free__mbpp-390.json` |
| google/gemma-4-31b-it:free | 444 | fail | 2 | 680 | 87 | 101.8s | Time limit reached | `runs/google-gemma-4-31b-it:free__mbpp-444.json` |
| google/gemma-4-31b-it:free | 75 | pass | 2 | 1,271 | 133 | 54.7s | solved | `runs/google-gemma-4-31b-it:free__mbpp-75.json` |
| google/gemma-4-31b-it:free | pydata__xarray-4629 | fail | 4 | 9,945 | 1,759 | 233.8s | Empty final answer | `runs/google-gemma-4-31b-it:free__pydata__xarray-4629.json` |
| google/gemma-4-31b-it:free | scikit-learn__scikit-learn-13439 | fail | 8 | 14,702 | 522 | 644.3s | Agent loop error | `runs/google-gemma-4-31b-it:free__scikit-learn__scikit-learn-13439.json` |
| google/gemma-4-31b-it:free | sympy__sympy-13480 | fail | 2 | 2,940 | 214 | 218.0s | Agent loop error | `runs/google-gemma-4-31b-it:free__sympy__sympy-13480.json` |
| google/gemma-4-31b-it:free | sympy__sympy-18189 | pass | 6 | 18,709 | 3,061 | 655.0s | solved | `runs/google-gemma-4-31b-it:free__sympy__sympy-18189.json` |
| ministral-14b-2512 | django__django-11066 | pass | 7 | 17,793 | 855 | 21.5s | solved | `runs/ministral-14b-2512__django__django-11066.json` |
| ministral-14b-2512 | django__django-17029 | pass | 7 | 14,865 | 785 | 14.3s | solved | `runs/ministral-14b-2512__django__django-17029.json` |
| ministral-14b-2512 | 103 | fail | 4 | 3,354 | 1,345 | 13.1s | Output token limit reached | `runs/ministral-14b-2512__mbpp-103.json` |
| ministral-14b-2512 | 11 | pass | 2 | 1,019 | 116 | 3.5s | solved | `runs/ministral-14b-2512__mbpp-11.json` |
| ministral-14b-2512 | 135 | pass | 2 | 956 | 54 | 1.0s | solved | `runs/ministral-14b-2512__mbpp-135.json` |
| ministral-14b-2512 | 227 | pass | 2 | 995 | 60 | 1.1s | solved | `runs/ministral-14b-2512__mbpp-227.json` |
| ministral-14b-2512 | 257 | pass | 2 | 980 | 46 | 2.0s | solved | `runs/ministral-14b-2512__mbpp-257.json` |
| ministral-14b-2512 | 285 | pass | 4 | 2,538 | 239 | 3.3s | solved | `runs/ministral-14b-2512__mbpp-285.json` |
| ministral-14b-2512 | 390 | pass | 2 | 1,079 | 60 | 2.1s | solved | `runs/ministral-14b-2512__mbpp-390.json` |
| ministral-14b-2512 | 418 | pass | 2 | 1,043 | 60 | 1.2s | solved | `runs/ministral-14b-2512__mbpp-418.json` |
| ministral-14b-2512 | 444 | fail | 5 | 5,359 | 372 | 5.3s | Iterations limit reached | `runs/ministral-14b-2512__mbpp-444.json` |
| ministral-14b-2512 | 75 | pass | 2 | 1,159 | 84 | 1.4s | solved | `runs/ministral-14b-2512__mbpp-75.json` |
| ministral-14b-2512 | pydata__xarray-4629 | pass | 6 | 28,203 | 383 | 13.2s | solved | `runs/ministral-14b-2512__pydata__xarray-4629.json` |
| ministral-14b-2512 | scikit-learn__scikit-learn-13439 | pass | 12 | 42,798 | 1,733 | 146.3s | solved | `runs/ministral-14b-2512__scikit-learn__scikit-learn-13439.json` |
| ministral-14b-2512 | sympy__sympy-13480 | pass | 12 | 32,285 | 1,477 | 143.2s | solved | `runs/ministral-14b-2512__sympy__sympy-13480.json` |
| ministral-14b-2512 | sympy__sympy-14711 | pass | 10 | 35,568 | 1,401 | 27.9s | solved | `runs/ministral-14b-2512__sympy__sympy-14711.json` |
| ministral-14b-2512 | sympy__sympy-18189 | pass | 19 | 78,723 | 2,534 | 285.4s | solved | `runs/ministral-14b-2512__sympy__sympy-18189.json` |
| ministral-3b-2512 | django__django-11066 | pass | 25 | 102,678 | 5,189 | 32.5s | solved | `runs/ministral-3b-2512__django__django-11066.json` |
| ministral-3b-2512 | django__django-17029 | pass | 24 | 62,020 | 1,450 | 15.6s | solved | `runs/ministral-3b-2512__django__django-17029.json` |
| ministral-3b-2512 | 103 | fail | 2 | 1,089 | 814 | 3.8s | Output token limit reached | `runs/ministral-3b-2512__mbpp-103.json` |
| ministral-3b-2512 | 11 | fail | 5 | 3,885 | 513 | 6.1s | Iterations limit reached | `runs/ministral-3b-2512__mbpp-11.json` |
| ministral-3b-2512 | 135 | pass | 2 | 956 | 54 | 0.8s | solved | `runs/ministral-3b-2512__mbpp-135.json` |
| ministral-3b-2512 | 227 | pass | 2 | 995 | 60 | 1.2s | solved | `runs/ministral-3b-2512__mbpp-227.json` |
| ministral-3b-2512 | 257 | pass | 2 | 981 | 48 | 0.9s | solved | `runs/ministral-3b-2512__mbpp-257.json` |
| ministral-3b-2512 | 285 | pass | 4 | 2,720 | 292 | 2.0s | solved | `runs/ministral-3b-2512__mbpp-285.json` |
| ministral-3b-2512 | 390 | pass | 2 | 1,079 | 60 | 1.4s | solved | `runs/ministral-3b-2512__mbpp-390.json` |
| ministral-3b-2512 | 418 | pass | 2 | 1,074 | 122 | 1.2s | solved | `runs/ministral-3b-2512__mbpp-418.json` |
| ministral-3b-2512 | 444 | fail | 5 | 5,712 | 563 | 4.0s | Iterations limit reached | `runs/ministral-3b-2512__mbpp-444.json` |
| ministral-3b-2512 | 75 | pass | 2 | 1,159 | 84 | 1.0s | solved | `runs/ministral-3b-2512__mbpp-75.json` |
| ministral-3b-2512 | pydata__xarray-4629 | pass | 7 | 28,308 | 217 | 6.8s | solved | `runs/ministral-3b-2512__pydata__xarray-4629.json` |
| ministral-3b-2512 | scikit-learn__scikit-learn-13439 | fail | 30 | 63,398 | 1,121 | 21.0s | Iterations limit reached | `runs/ministral-3b-2512__scikit-learn__scikit-learn-13439.json` |
| ministral-3b-2512 | sympy__sympy-13480 | pass | 11 | 16,260 | 455 | 11.5s | solved | `runs/ministral-3b-2512__sympy__sympy-13480.json` |
| ministral-3b-2512 | sympy__sympy-14711 | fail | 30 | 62,422 | 1,468 | 17.6s | Iterations limit reached | `runs/ministral-3b-2512__sympy__sympy-14711.json` |
| ministral-3b-2512 | sympy__sympy-18189 | fail | 30 | 99,534 | 2,848 | 24.2s | Iterations limit reached | `runs/ministral-3b-2512__sympy__sympy-18189.json` |
| ministral-8b-2512 | django__django-11066 | pass | 6 | 14,436 | 599 | 12.4s | solved | `runs/ministral-8b-2512__django__django-11066.json` |
| ministral-8b-2512 | django__django-17029 | pass | 7 | 14,747 | 747 | 13.6s | solved | `runs/ministral-8b-2512__django__django-17029.json` |
| ministral-8b-2512 | 103 | fail | 5 | 4,984 | 1,189 | 12.1s | Iterations limit reached | `runs/ministral-8b-2512__mbpp-103.json` |
| ministral-8b-2512 | 11 | pass | 2 | 1,063 | 204 | 4.5s | solved | `runs/ministral-8b-2512__mbpp-11.json` |
| ministral-8b-2512 | 135 | pass | 2 | 956 | 54 | 1.2s | solved | `runs/ministral-8b-2512__mbpp-135.json` |
| ministral-8b-2512 | 227 | pass | 2 | 995 | 60 | 1.2s | solved | `runs/ministral-8b-2512__mbpp-227.json` |
| ministral-8b-2512 | 257 | pass | 2 | 981 | 48 | 1.1s | solved | `runs/ministral-8b-2512__mbpp-257.json` |
| ministral-8b-2512 | 285 | pass | 4 | 2,893 | 414 | 4.8s | solved | `runs/ministral-8b-2512__mbpp-285.json` |
| ministral-8b-2512 | 390 | pass | 2 | 1,079 | 60 | 1.4s | solved | `runs/ministral-8b-2512__mbpp-390.json` |
| ministral-8b-2512 | 418 | pass | 2 | 1,062 | 98 | 1.4s | solved | `runs/ministral-8b-2512__mbpp-418.json` |
| ministral-8b-2512 | 444 | pass | 3 | 2,775 | 550 | 5.6s | solved | `runs/ministral-8b-2512__mbpp-444.json` |
| ministral-8b-2512 | 75 | pass | 2 | 1,159 | 84 | 1.4s | solved | `runs/ministral-8b-2512__mbpp-75.json` |
| ministral-8b-2512 | pydata__xarray-4629 | pass | 13 | 35,346 | 1,169 | 27.8s | solved | `runs/ministral-8b-2512__pydata__xarray-4629.json` |
| ministral-8b-2512 | scikit-learn__scikit-learn-13439 | pass | 24 | 122,125 | 3,629 | 298.7s | solved | `runs/ministral-8b-2512__scikit-learn__scikit-learn-13439.json` |
| ministral-8b-2512 | sympy__sympy-13480 | pass | 13 | 43,440 | 1,690 | 267.0s | solved | `runs/ministral-8b-2512__sympy__sympy-13480.json` |
| ministral-8b-2512 | sympy__sympy-14711 | fail | 30 | 292,368 | 7,906 | 126.8s | Iterations limit reached | `runs/ministral-8b-2512__sympy__sympy-14711.json` |
| ministral-8b-2512 | sympy__sympy-18189 | pass | 14 | 50,336 | 2,173 | 164.1s | solved | `runs/ministral-8b-2512__sympy__sympy-18189.json` |
| nex-agi/nex-n2.5-mini:free | django__django-11066 | fail | 30 | 198,251 | 3,484 | 76.1s | Iterations limit reached | `runs/nex-agi-nex-n2.5-mini:free__django__django-11066.json` |
| nex-agi/nex-n2.5-mini:free | django__django-17029 | fail | 16 | 85,241 | 3,292 | 64.9s | Agent loop error | `runs/nex-agi-nex-n2.5-mini:free__django__django-17029.json` |
| nex-agi/nex-n2.5-mini:free | 103 | pass | 3 | 4,196 | 1,094 | 14.4s | solved | `runs/nex-agi-nex-n2.5-mini:free__mbpp-103.json` |
| nex-agi/nex-n2.5-mini:free | 11 | pass | 2 | 1,260 | 437 | 8.5s | solved | `runs/nex-agi-nex-n2.5-mini:free__mbpp-11.json` |
| nex-agi/nex-n2.5-mini:free | 135 | pass | 2 | 1,582 | 186 | 6.7s | solved | `runs/nex-agi-nex-n2.5-mini:free__mbpp-135.json` |
| nex-agi/nex-n2.5-mini:free | 227 | pass | 2 | 1,990 | 488 | 8.7s | solved | `runs/nex-agi-nex-n2.5-mini:free__mbpp-227.json` |
| nex-agi/nex-n2.5-mini:free | 257 | pass | 2 | 1,519 | 825 | 11.7s | solved | `runs/nex-agi-nex-n2.5-mini:free__mbpp-257.json` |
| nex-agi/nex-n2.5-mini:free | 285 | fail | 1 | 885 | 752 | 10.2s | Output token limit reached | `runs/nex-agi-nex-n2.5-mini:free__mbpp-285.json` |
| nex-agi/nex-n2.5-mini:free | 390 | pass | 2 | 2,074 | 300 | 7.5s | solved | `runs/nex-agi-nex-n2.5-mini:free__mbpp-390.json` |
| nex-agi/nex-n2.5-mini:free | 418 | pass | 2 | 2,124 | 403 | 8.8s | solved | `runs/nex-agi-nex-n2.5-mini:free__mbpp-418.json` |
| nex-agi/nex-n2.5-mini:free | 444 | pass | 3 | 4,790 | 372 | 8.8s | solved | `runs/nex-agi-nex-n2.5-mini:free__mbpp-444.json` |
| nex-agi/nex-n2.5-mini:free | 75 | pass | 2 | 2,237 | 414 | 8.3s | solved | `runs/nex-agi-nex-n2.5-mini:free__mbpp-75.json` |
| openai/gpt-oss-120b | django__django-11066 | fail | 2 | 4,564 | 1,314 | 4.4s | Empty final answer | `runs/openai-gpt-oss-120b__django__django-11066.json` |
| openai/gpt-oss-120b | django__django-17029 | fail | 2 | 4,921 | 4,480 | 60.1s | Empty final answer | `runs/openai-gpt-oss-120b__django__django-17029.json` |
| openai/gpt-oss-120b | 103 | fail | 3 | 3,046 | 1,135 | 3.5s | Output token limit reached | `runs/openai-gpt-oss-120b__mbpp-103.json` |
| openai/gpt-oss-120b | 11 | pass | 2 | 1,440 | 453 | 2.5s | solved | `runs/openai-gpt-oss-120b__mbpp-11.json` |
| openai/gpt-oss-120b | 135 | pass | 2 | 1,187 | 157 | 1.1s | solved | `runs/openai-gpt-oss-120b__mbpp-135.json` |
| openai/gpt-oss-120b | 227 | pass | 2 | 1,168 | 133 | 1.0s | solved | `runs/openai-gpt-oss-120b__mbpp-227.json` |
| openai/gpt-oss-120b | 257 | fail | 1 | 527 | 45 | 1.0s | Agent loop error | `runs/openai-gpt-oss-120b__mbpp-257.json` |
| openai/gpt-oss-120b | 285 | fail | 1 | 537 | 249 | 3.3s | Agent loop error | `runs/openai-gpt-oss-120b__mbpp-285.json` |
| openai/gpt-oss-120b | 390 | pass | 1 | 582 | 201 | 2.9s | solved | `runs/openai-gpt-oss-120b__mbpp-390.json` |
| openai/gpt-oss-120b | 418 | fail | 1 | 561 | 131 | 14.3s | Agent loop error | `runs/openai-gpt-oss-120b__mbpp-418.json` |
| openai/gpt-oss-120b | 444 | fail | 1 | 695 | 544 | 22.3s | Agent loop error | `runs/openai-gpt-oss-120b__mbpp-444.json` |
| openai/gpt-oss-120b | 75 | fail | 1 | 604 | 135 | 10.7s | Agent loop error | `runs/openai-gpt-oss-120b__mbpp-75.json` |
| openai/gpt-oss-120b | pydata__xarray-4629 | fail | 8 | 33,595 | 5,106 | 267.5s | Agent loop error | `runs/openai-gpt-oss-120b__pydata__xarray-4629.json` |
| openai/gpt-oss-120b | scikit-learn__scikit-learn-13439 | fail | 3 | 8,022 | 10,000 | 60.0s | Output token limit reached | `runs/openai-gpt-oss-120b__scikit-learn__scikit-learn-13439.json` |
| openai/gpt-oss-120b | sympy__sympy-13480 | fail | 6 | 9,579 | 1,786 | 199.0s | Agent loop error | `runs/openai-gpt-oss-120b__sympy__sympy-13480.json` |
| openai/gpt-oss-120b | sympy__sympy-14711 | fail | 3 | 4,919 | 4,120 | 87.8s | Agent loop error | `runs/openai-gpt-oss-120b__sympy__sympy-14711.json` |
| openai/gpt-oss-120b | sympy__sympy-18189 | fail | 2 | 4,035 | 3,885 | 18.3s | Agent loop error | `runs/openai-gpt-oss-120b__sympy__sympy-18189.json` |
| poolside/laguna-s-2.1:free | django__django-11066 | fail | 1 | 1,900 | 10,000 | 187.6s | Output token limit reached | `runs/poolside-laguna-s-2.1:free__django__django-11066.json` |
| poolside/laguna-s-2.1:free | django__django-17029 | fail | 1 | 1,258 | 10,000 | 195.6s | Output token limit reached | `runs/poolside-laguna-s-2.1:free__django__django-17029.json` |
| poolside/laguna-s-2.1:free | 103 | fail | 1 | 503 | 834 | 22.8s | Output token limit reached | `runs/poolside-laguna-s-2.1:free__mbpp-103.json` |
| poolside/laguna-s-2.1:free | 11 | pass | 2 | 1,543 | 626 | 29.3s | solved | `runs/poolside-laguna-s-2.1:free__mbpp-11.json` |
| poolside/laguna-s-2.1:free | 135 | pass | 2 | 1,128 | 165 | 11.8s | solved | `runs/poolside-laguna-s-2.1:free__mbpp-135.json` |
| poolside/laguna-s-2.1:free | 227 | pass | 2 | 1,103 | 121 | 14.7s | solved | `runs/poolside-laguna-s-2.1:free__mbpp-227.json` |
| poolside/laguna-s-2.1:free | 257 | pass | 2 | 1,142 | 153 | 19.4s | solved | `runs/poolside-laguna-s-2.1:free__mbpp-257.json` |
| poolside/laguna-s-2.1:free | 285 | pass | 2 | 1,456 | 482 | 17.0s | solved | `runs/poolside-laguna-s-2.1:free__mbpp-285.json` |
| poolside/laguna-s-2.1:free | 390 | pass | 2 | 1,427 | 371 | 15.0s | solved | `runs/poolside-laguna-s-2.1:free__mbpp-390.json` |
| poolside/laguna-s-2.1:free | 418 | pass | 2 | 1,364 | 321 | 21.6s | solved | `runs/poolside-laguna-s-2.1:free__mbpp-418.json` |
| poolside/laguna-s-2.1:free | 444 | pass | 2 | 1,749 | 449 | 30.3s | solved | `runs/poolside-laguna-s-2.1:free__mbpp-444.json` |
| poolside/laguna-s-2.1:free | 75 | pass | 2 | 1,251 | 105 | 21.4s | solved | `runs/poolside-laguna-s-2.1:free__mbpp-75.json` |
| poolside/laguna-s-2.1:free | pydata__xarray-4629 | pass | 5 | 24,564 | 881 | 83.7s | solved | `runs/poolside-laguna-s-2.1:free__pydata__xarray-4629.json` |
| poolside/laguna-s-2.1:free | scikit-learn__scikit-learn-13439 | fail | 9 | 24,496 | 811 | 102.0s | Agent loop error | `runs/poolside-laguna-s-2.1:free__scikit-learn__scikit-learn-13439.json` |
| poolside/laguna-s-2.1:free | sympy__sympy-13480 | fail | 11 | 29,823 | 1,289 | 328.4s | Agent loop error | `runs/poolside-laguna-s-2.1:free__sympy__sympy-13480.json` |
| poolside/laguna-s-2.1:free | sympy__sympy-14711 | fail | 1 | 1,297 | 10,000 | 204.4s | Output token limit reached | `runs/poolside-laguna-s-2.1:free__sympy__sympy-14711.json` |
| poolside/laguna-s-2.1:free | sympy__sympy-18189 | fail | 1 | 1,987 | 160 | 32.1s | Agent loop error | `runs/poolside-laguna-s-2.1:free__sympy__sympy-18189.json` |
| qwen/qwen3.8-27b | django__django-11066 | pass | 4 | 9,322 | 230 | 20.9s | solved | `runs/qwen-qwen3.8-27b__django__django-11066.json` |
| qwen/qwen3.8-27b | django__django-17029 | pass | 7 | 13,238 | 412 | 112.0s | solved | `runs/qwen-qwen3.8-27b__django__django-17029.json` |
| qwen/qwen3.8-27b | 103 | pass | 2 | 1,338 | 472 | 1.5s | solved | `runs/qwen-qwen3.8-27b__mbpp-103.json` |
| qwen/qwen3.8-27b | 11 | pass | 2 | 1,175 | 223 | 1.7s | solved | `runs/qwen-qwen3.8-27b__mbpp-11.json` |
| qwen/qwen3.8-27b | 135 | pass | 2 | 1,048 | 63 | 0.6s | solved | `runs/qwen-qwen3.8-27b__mbpp-135.json` |
| qwen/qwen3.8-27b | 227 | pass | 2 | 1,073 | 65 | 0.6s | solved | `runs/qwen-qwen3.8-27b__mbpp-227.json` |
| qwen/qwen3.8-27b | 257 | pass | 2 | 1,068 | 51 | 0.7s | solved | `runs/qwen-qwen3.8-27b__mbpp-257.json` |
| qwen/qwen3.8-27b | 285 | pass | 2 | 1,077 | 77 | 0.6s | solved | `runs/qwen-qwen3.8-27b__mbpp-285.json` |
| qwen/qwen3.8-27b | 390 | pass | 2 | 1,159 | 65 | 0.5s | solved | `runs/qwen-qwen3.8-27b__mbpp-390.json` |
| qwen/qwen3.8-27b | 418 | pass | 2 | 1,111 | 53 | 0.7s | solved | `runs/qwen-qwen3.8-27b__mbpp-418.json` |
| qwen/qwen3.8-27b | 444 | pass | 2 | 1,404 | 87 | 8.8s | solved | `runs/qwen-qwen3.8-27b__mbpp-444.json` |
| qwen/qwen3.8-27b | 75 | pass | 2 | 1,230 | 87 | 9.7s | solved | `runs/qwen-qwen3.8-27b__mbpp-75.json` |
| qwen/qwen3.8-27b | pydata__xarray-4629 | fail | 4 | 8,631 | 149 | 75.4s | Agent loop error | `runs/qwen-qwen3.8-27b__pydata__xarray-4629.json` |
| qwen/qwen3.8-27b | scikit-learn__scikit-learn-13439 | fail | 14 | 57,751 | 567 | 489.1s | Agent loop error | `runs/qwen-qwen3.8-27b__scikit-learn__scikit-learn-13439.json` |
| qwen/qwen3.8-27b | sympy__sympy-13480 | pass | 7 | 12,584 | 436 | 169.4s | solved | `runs/qwen-qwen3.8-27b__sympy__sympy-13480.json` |
| qwen/qwen3.8-27b | sympy__sympy-14711 | fail | 7 | 15,076 | 414 | 129.1s | Agent loop error | `runs/qwen-qwen3.8-27b__sympy__sympy-14711.json` |
| qwen/qwen3.8-27b | sympy__sympy-18189 | pass | 14 | 57,489 | 1,030 | 613.3s | solved | `runs/qwen-qwen3.8-27b__sympy__sympy-18189.json` |
| z-ai/glm-5.2:free | django__django-17029 | fail | 1 | 1,177 | 35 | 34.1s | Agent loop error | `runs/z-ai-glm-5.2:free__django__django-17029.json` |
| z-ai/glm-5.2:free | 11 | pass | 2 | 1,516 | 622 | 116.0s | solved | `runs/z-ai-glm-5.2:free__mbpp-11.json` |
| z-ai/glm-5.2:free | 135 | pass | 2 | 993 | 72 | 40.2s | solved | `runs/z-ai-glm-5.2:free__mbpp-135.json` |
| z-ai/glm-5.2:free | 227 | pass | 2 | 1,042 | 110 | 29.4s | solved | `runs/z-ai-glm-5.2:free__mbpp-227.json` |
| z-ai/glm-5.2:free | 257 | pass | 2 | 1,042 | 136 | 46.4s | solved | `runs/z-ai-glm-5.2:free__mbpp-257.json` |
| z-ai/glm-5.2:free | 285 | pass | 2 | 1,307 | 394 | 34.2s | solved | `runs/z-ai-glm-5.2:free__mbpp-285.json` |
| z-ai/glm-5.2:free | 390 | pass | 2 | 1,245 | 216 | 36.4s | solved | `runs/z-ai-glm-5.2:free__mbpp-390.json` |
| z-ai/glm-5.2:free | 418 | pass | 2 | 1,072 | 78 | 46.7s | solved | `runs/z-ai-glm-5.2:free__mbpp-418.json` |
| z-ai/glm-5.2:free | 444 | pass | 2 | 1,420 | 185 | 31.5s | solved | `runs/z-ai-glm-5.2:free__mbpp-444.json` |
| z-ai/glm-5.2:free | 75 | pass | 2 | 1,177 | 118 | 30.8s | solved | `runs/z-ai-glm-5.2:free__mbpp-75.json` |
| z-ai/glm-5.2:free | sympy__sympy-18189 | fail | 1 | 1,866 | 46 | 33.3s | Agent loop error | `runs/z-ai-glm-5.2:free__sympy__sympy-18189.json` |

## Provider reliability

| Model | Runs | Avg response | Retries | Cells with data |
|---|---:|---:|---:|---:|
| codestral-2508 | 17 | 1487 ms | 0 | 17/16 |
| dots-studio/dots-3-note-preview:free | 17 | 4047 ms | 54 | 17/16 |
| google/gemma-4-31b-it:free | 15 | 70631 ms | 0 | 17/16 |
| ministral-14b-2512 | 17 | 1794 ms | 0 | 17/16 |
| ministral-3b-2512 | 17 | 660 ms | 0 | 17/16 |
| ministral-8b-2512 | 17 | 2308 ms | 0 | 17/16 |
| nex-agi/nex-n2.5-mini:free | 12 | 3128 ms | 43 | 17/16 |
| openai/gpt-oss-120b | 17 | 13376 ms | 0 | 17/16 |
| poolside/laguna-s-2.1:free | 17 | 21871 ms | 118 | 17/16 |
| qwen/qwen3.8-27b | 17 | 16226 ms | 0 | 17/16 |
| z-ai/glm-5.2:free | 11 | 21795 ms | 56 | 17/16 |

## Intermediary metrics

| Model | Task | Patched file first read/edited | Suite first green | Iterations from green to answer | Failures first dropped |
|---|---|---:|---:|---:|---:|
| codestral-2508 | django__django-11066 | step 4 | step 6 | 1 | — |
| codestral-2508 | django__django-17029 | — | — | — | — |
| codestral-2508 | 103 | — | — | — | — |
| codestral-2508 | 11 | — | — | — | — |
| codestral-2508 | 135 | — | — | — | — |
| codestral-2508 | 227 | — | — | — | — |
| codestral-2508 | 257 | — | — | — | — |
| codestral-2508 | 285 | — | — | — | — |
| codestral-2508 | 390 | — | — | — | — |
| codestral-2508 | 418 | — | — | — | — |
| codestral-2508 | 444 | — | — | — | — |
| codestral-2508 | 75 | — | — | — | — |
| codestral-2508 | pydata__xarray-4629 | step 4 | — | — | — |
| codestral-2508 | scikit-learn__scikit-learn-13439 | — | — | — | — |
| codestral-2508 | sympy__sympy-13480 | step 1 | — | — | — |
| codestral-2508 | sympy__sympy-14711 | — | — | — | — |
| codestral-2508 | sympy__sympy-18189 | step 2 | — | — | — |
| dots-studio/dots-3-note-preview:free | django__django-11066 | step 3 | step 7 | 1 | — |
| dots-studio/dots-3-note-preview:free | django__django-17029 | step 2 | step 9 | 1 | — |
| dots-studio/dots-3-note-preview:free | 103 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | 11 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | 135 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | 227 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | 257 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | 285 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | 390 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | 418 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | 444 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | 75 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | pydata__xarray-4629 | step 3 | — | — | — |
| dots-studio/dots-3-note-preview:free | scikit-learn__scikit-learn-13439 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | sympy__sympy-13480 | step 1 | — | — | — |
| dots-studio/dots-3-note-preview:free | sympy__sympy-14711 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | sympy__sympy-18189 | step 2 | — | — | — |
| google/gemma-4-31b-it:free | django__django-11066 | — | — | — | — |
| google/gemma-4-31b-it:free | django__django-17029 | — | — | — | — |
| google/gemma-4-31b-it:free | 103 | — | — | — | — |
| google/gemma-4-31b-it:free | 11 | — | — | — | — |
| google/gemma-4-31b-it:free | 135 | — | — | — | — |
| google/gemma-4-31b-it:free | 227 | — | — | — | — |
| google/gemma-4-31b-it:free | 257 | — | — | — | — |
| google/gemma-4-31b-it:free | 285 | — | — | — | — |
| google/gemma-4-31b-it:free | 390 | — | — | — | — |
| google/gemma-4-31b-it:free | 444 | — | — | — | — |
| google/gemma-4-31b-it:free | 75 | — | — | — | — |
| google/gemma-4-31b-it:free | pydata__xarray-4629 | — | — | — | — |
| google/gemma-4-31b-it:free | scikit-learn__scikit-learn-13439 | — | — | — | — |
| google/gemma-4-31b-it:free | sympy__sympy-13480 | — | — | — | — |
| google/gemma-4-31b-it:free | sympy__sympy-18189 | step 2 | — | — | — |
| ministral-14b-2512 | django__django-11066 | step 4 | step 6 | 1 | — |
| ministral-14b-2512 | django__django-17029 | step 2 | step 6 | 1 | — |
| ministral-14b-2512 | 103 | — | — | — | — |
| ministral-14b-2512 | 11 | — | — | — | — |
| ministral-14b-2512 | 135 | — | — | — | — |
| ministral-14b-2512 | 227 | — | — | — | — |
| ministral-14b-2512 | 257 | — | — | — | — |
| ministral-14b-2512 | 285 | — | — | — | — |
| ministral-14b-2512 | 390 | — | — | — | — |
| ministral-14b-2512 | 418 | — | — | — | — |
| ministral-14b-2512 | 444 | — | — | — | — |
| ministral-14b-2512 | 75 | — | — | — | — |
| ministral-14b-2512 | pydata__xarray-4629 | step 2 | — | — | — |
| ministral-14b-2512 | scikit-learn__scikit-learn-13439 | step 2 | — | — | — |
| ministral-14b-2512 | sympy__sympy-13480 | step 1 | — | — | — |
| ministral-14b-2512 | sympy__sympy-14711 | step 2 | — | — | — |
| ministral-14b-2512 | sympy__sympy-18189 | step 2 | — | — | — |
| ministral-3b-2512 | django__django-11066 | step 4 | — | — | — |
| ministral-3b-2512 | django__django-17029 | step 4 | — | — | — |
| ministral-3b-2512 | 103 | — | — | — | — |
| ministral-3b-2512 | 11 | — | — | — | — |
| ministral-3b-2512 | 135 | — | — | — | — |
| ministral-3b-2512 | 227 | — | — | — | — |
| ministral-3b-2512 | 257 | — | — | — | — |
| ministral-3b-2512 | 285 | — | — | — | — |
| ministral-3b-2512 | 390 | — | — | — | — |
| ministral-3b-2512 | 418 | — | — | — | — |
| ministral-3b-2512 | 444 | — | — | — | — |
| ministral-3b-2512 | 75 | — | — | — | — |
| ministral-3b-2512 | pydata__xarray-4629 | step 4 | — | — | — |
| ministral-3b-2512 | scikit-learn__scikit-learn-13439 | — | — | — | — |
| ministral-3b-2512 | sympy__sympy-13480 | — | — | — | — |
| ministral-3b-2512 | sympy__sympy-14711 | — | — | — | — |
| ministral-3b-2512 | sympy__sympy-18189 | — | — | — | — |
| ministral-8b-2512 | django__django-11066 | step 3 | step 5 | 1 | — |
| ministral-8b-2512 | django__django-17029 | step 2 | step 6 | 1 | — |
| ministral-8b-2512 | 103 | — | — | — | — |
| ministral-8b-2512 | 11 | — | — | — | — |
| ministral-8b-2512 | 135 | — | — | — | — |
| ministral-8b-2512 | 227 | — | — | — | — |
| ministral-8b-2512 | 257 | — | — | — | — |
| ministral-8b-2512 | 285 | — | — | — | — |
| ministral-8b-2512 | 390 | — | — | — | — |
| ministral-8b-2512 | 418 | — | — | — | — |
| ministral-8b-2512 | 444 | — | — | — | — |
| ministral-8b-2512 | 75 | — | — | — | — |
| ministral-8b-2512 | pydata__xarray-4629 | step 3 | — | — | — |
| ministral-8b-2512 | scikit-learn__scikit-learn-13439 | step 2 | — | — | — |
| ministral-8b-2512 | sympy__sympy-13480 | step 1 | — | — | — |
| ministral-8b-2512 | sympy__sympy-14711 | — | — | — | — |
| ministral-8b-2512 | sympy__sympy-18189 | step 2 | — | — | — |
| nex-agi/nex-n2.5-mini:free | django__django-11066 | — | step 28 | 2 | — |
| nex-agi/nex-n2.5-mini:free | django__django-17029 | — | step 15 | 1 | — |
| nex-agi/nex-n2.5-mini:free | 103 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | 11 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | 135 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | 227 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | 257 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | 285 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | 390 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | 418 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | 444 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | 75 | — | — | — | — |
| openai/gpt-oss-120b | django__django-11066 | — | — | — | — |
| openai/gpt-oss-120b | django__django-17029 | — | — | — | — |
| openai/gpt-oss-120b | 103 | — | — | — | — |
| openai/gpt-oss-120b | 11 | — | — | — | — |
| openai/gpt-oss-120b | 135 | — | — | — | — |
| openai/gpt-oss-120b | 227 | — | — | — | — |
| openai/gpt-oss-120b | 257 | — | — | — | — |
| openai/gpt-oss-120b | 285 | — | — | — | — |
| openai/gpt-oss-120b | 390 | — | — | — | — |
| openai/gpt-oss-120b | 418 | — | — | — | — |
| openai/gpt-oss-120b | 444 | — | — | — | — |
| openai/gpt-oss-120b | 75 | — | — | — | — |
| openai/gpt-oss-120b | pydata__xarray-4629 | — | — | — | — |
| openai/gpt-oss-120b | scikit-learn__scikit-learn-13439 | — | — | — | — |
| openai/gpt-oss-120b | sympy__sympy-13480 | — | — | — | — |
| openai/gpt-oss-120b | sympy__sympy-14711 | — | — | — | — |
| openai/gpt-oss-120b | sympy__sympy-18189 | — | — | — | — |
| poolside/laguna-s-2.1:free | django__django-11066 | — | — | — | — |
| poolside/laguna-s-2.1:free | django__django-17029 | — | — | — | — |
| poolside/laguna-s-2.1:free | 103 | — | — | — | — |
| poolside/laguna-s-2.1:free | 11 | — | — | — | — |
| poolside/laguna-s-2.1:free | 135 | — | — | — | — |
| poolside/laguna-s-2.1:free | 227 | — | — | — | — |
| poolside/laguna-s-2.1:free | 257 | — | — | — | — |
| poolside/laguna-s-2.1:free | 285 | — | — | — | — |
| poolside/laguna-s-2.1:free | 390 | — | — | — | — |
| poolside/laguna-s-2.1:free | 418 | — | — | — | — |
| poolside/laguna-s-2.1:free | 444 | — | — | — | — |
| poolside/laguna-s-2.1:free | 75 | — | — | — | — |
| poolside/laguna-s-2.1:free | pydata__xarray-4629 | step 1 | — | — | — |
| poolside/laguna-s-2.1:free | scikit-learn__scikit-learn-13439 | — | — | — | — |
| poolside/laguna-s-2.1:free | sympy__sympy-13480 | — | — | — | — |
| poolside/laguna-s-2.1:free | sympy__sympy-14711 | — | — | — | — |
| poolside/laguna-s-2.1:free | sympy__sympy-18189 | — | — | — | — |
| qwen/qwen3.8-27b | django__django-11066 | step 1 | step 3 | 1 | — |
| qwen/qwen3.8-27b | django__django-17029 | step 2 | step 6 | 1 | — |
| qwen/qwen3.8-27b | 103 | — | — | — | — |
| qwen/qwen3.8-27b | 11 | — | — | — | — |
| qwen/qwen3.8-27b | 135 | — | — | — | — |
| qwen/qwen3.8-27b | 227 | — | — | — | — |
| qwen/qwen3.8-27b | 257 | — | — | — | — |
| qwen/qwen3.8-27b | 285 | — | — | — | — |
| qwen/qwen3.8-27b | 390 | — | — | — | — |
| qwen/qwen3.8-27b | 418 | — | — | — | — |
| qwen/qwen3.8-27b | 444 | — | — | — | — |
| qwen/qwen3.8-27b | 75 | — | — | — | — |
| qwen/qwen3.8-27b | pydata__xarray-4629 | — | — | — | — |
| qwen/qwen3.8-27b | scikit-learn__scikit-learn-13439 | — | — | — | — |
| qwen/qwen3.8-27b | sympy__sympy-13480 | step 1 | — | — | — |
| qwen/qwen3.8-27b | sympy__sympy-14711 | — | — | — | — |
| qwen/qwen3.8-27b | sympy__sympy-18189 | step 1 | — | — | — |
| z-ai/glm-5.2:free | django__django-17029 | — | — | — | — |
| z-ai/glm-5.2:free | 11 | — | — | — | — |
| z-ai/glm-5.2:free | 135 | — | — | — | — |
| z-ai/glm-5.2:free | 227 | — | — | — | — |
| z-ai/glm-5.2:free | 257 | — | — | — | — |
| z-ai/glm-5.2:free | 285 | — | — | — | — |
| z-ai/glm-5.2:free | 390 | — | — | — | — |
| z-ai/glm-5.2:free | 418 | — | — | — | — |
| z-ai/glm-5.2:free | 444 | — | — | — | — |
| z-ai/glm-5.2:free | 75 | — | — | — | — |
| z-ai/glm-5.2:free | sympy__sympy-18189 | — | — | — | — |

> Read from `runs/*.json`. An em dash means the run does not contain what the metric needs — a task solved without ever running the suite has no green step to report.
