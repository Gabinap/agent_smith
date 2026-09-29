# Benchmark report

## How to reproduce

- **Commit** `4f1f9be` — Python 3.10.19 — Linux x86_64
- **Cells**: 11 models × (7 SWE-bench + 10 MBPP tasks), plus 3 models that left the catalogue — 238 cells, run 2026-09-24 to 2026-09-27, each judged by `moulinette_eval validate`
- **SWE-bench**: `django__django-11066`, `django__django-17029`, `pydata__xarray-4629`, `scikit-learn__scikit-learn-13439`, `sympy__sympy-13480`, `sympy__sympy-14711`, `sympy__sympy-18189`
- **MBPP**: 11, 75, 103, 135, 227, 257, 285, 390, 418, 444

| Benchmark | Iterations | Tokens in | Tokens out | Time | Temperature |
|---|---:|---:|---:|---:|---:|
| MBPP | 5 | 6,000 | 1,500 | 100s | 0.0 |
| SWE-bench | 30 | 300,000 | 10,000 | 840s | 0.0 |

```sh
uv run srcs/bench_matrix.py --benchmark mbpp
uv run srcs/bench_matrix.py --benchmark swebench
make validate && make report
```

> Free-tier quotas can end a cell early — counted as *no data*, not as a failure — and temperature 0 is not strictly deterministic: a re-run can move by a cell or two.

## Selection rationale

**Tasks.** SWE-bench: the moulinette's exam pool, plus `django__django-17029` outside it. MBPP has no exam pool: its ten tasks are every 25th id of the sorted test split.

**Models.** 11, on the free tiers of four providers (OpenRouter, Mistral, Groq, Together), chosen for spread: several vendors, a size ladder (`ministral` 3B, 8B, 14B), a code model (`codestral`). Each candidate was screened on one task per benchmark; left out were models that could not follow the protocol (`gpt-oss-20b` answers with native tool calls, `allam-2-7b` invents the sandbox's output), paid-only models, and aliases of models already in. Version ids are pinned where the provider offers them.

## What the agent is given

The prompt carries the task's `hints_text`, an input the subject defines. On 3 of the 7 tasks it gives the fix away:

| Task | `hints_text` | What it gives |
|---|---:|---|
| django__django-11066 | 2,075 chars | a link to the upstream fix |
| django__django-17029 | 44 chars | discussion |
| pydata__xarray-4629 | 0 chars | — |
| scikit-learn__scikit-learn-13439 | 285 chars | discussion |
| sympy__sympy-13480 | 146 chars | the line and the change to make |
| sympy__sympy-14711 | 0 chars | — |
| sympy__sympy-18189 | 2,027 chars | the fix's own diff |

The ablation removes them: `ministral-14b-2512` resolves 16/21 without, 16/21 with (p = 1.00).

No run fetched anything from outside its task; one `git log --all …` (`stealth/space-bunny-alpha`) found nothing.

## Summary

| Model | SWE-bench (/7) | MBPP (/10) | Total | Cells with no data |
|---|---:|---:|---:|---:|
| Prism-ML/Ternary-Bonsai-27B | 3 | 2 | **5** | — |
| codestral-2508 | 2 | 7 | **9** | — |
| dots-studio/dots-3-note-preview:free | 4 | 6 | **10** | — |
| google/gemma-4-31b-it:free | 3 | 6 | **9** | — |
| ministral-14b-2512 | 7 | 7 | **14** | — |
| ministral-3b-2512 | 2 | 7 | **9** | — |
| ministral-8b-2512 | 6 | 9 | **15** | — |
| openai/gpt-oss-120b | 1 | 9 | **10** | 1 |
| poolside/laguna-s-2.1:free | 2 | 9 | **11** | — |
| qwen/qwen3.8-27b:free | 3 | 8 | **11** | 2 |
| stealth/space-bunny-alpha | 4 | 9 | **13** | — |
| **all** | | | **116 / 187** | 3 |

Models that left the catalogue during the campaign — withdrawn by their provider, beyond what the account could pay for, or moved to another provider. Their cells ran while they were catalogued, and are kept apart rather than dropped:

| Model | SWE-bench (/7) | MBPP (/10) | Total | Cells with no data |
|---|---:|---:|---:|---:|
| nex-agi/nex-n2.5-mini:free | 1 | 9 | **10** | 3 |
| qwen/qwen3.8-27b | 2 | 10 | **12** | 5 |
| z-ai/glm-5.2:free | 2 | 10 | **12** | 5 |
| **all** | | | **34 / 51** | 13 |

> `pass` means the moulinette returned both `Correctness: PASSED` and `Metrics: VALID`. `fail (budget)` means the answer was correct but a budget was overrun, which the moulinette counts as a failure.

## Provider reliability

| Model | Runs | Avg response | Retries | Cells with data |
|---|---:|---:|---:|---:|
| Prism-ML/Ternary-Bonsai-27B | 17 | 10179 ms | 0 | 17/17 |
| codestral-2508 | 17 | 1756 ms | 0 | 17/17 |
| dots-studio/dots-3-note-preview:free | 17 | 5263 ms | 39 | 17/17 |
| google/gemma-4-31b-it:free | 17 | 66485 ms | 0 | 17/17 |
| ministral-14b-2512 | 17 | 2233 ms | 0 | 17/17 |
| ministral-3b-2512 | 17 | 725 ms | 0 | 17/17 |
| ministral-8b-2512 | 17 | 2505 ms | 0 | 17/17 |
| nex-agi/nex-n2.5-mini:free | 17 | 3269 ms | 43 | 14/17 |
| openai/gpt-oss-120b | 17 | 6113 ms | 0 | 16/17 |
| poolside/laguna-s-2.1:free | 17 | 14283 ms | 84 | 17/17 |
| qwen/qwen3.8-27b | 17 | 13330 ms | 0 | 12/17 |
| qwen/qwen3.8-27b:free | 17 | 17936 ms | 38 | 15/17 |
| stealth/space-bunny-alpha | 17 | 33749 ms | 0 | 17/17 |
| z-ai/glm-5.2:free | 17 | 22821 ms | 67 | 12/17 |

## Results per cell

<details>
<summary>SWE-bench — every (model, task) cell, with the solution.json behind it</summary>

| Model | Task | Result | Iterations | Tokens in | Tokens out | Wall time | Stopped because | Evidence |
|---|---|---|---:|---:|---:|---:|---|---|
| Prism-ML/Ternary-Bonsai-27B | django__django-11066 | fail | 7 | 18,163 | 990 | 28.3s | solved | [`Prism-ML-Ternary-Bonsai-27B__django__django-11066.json`](runs/Prism-ML-Ternary-Bonsai-27B/Prism-ML-Ternary-Bonsai-27B__django__django-11066.json) |
| Prism-ML/Ternary-Bonsai-27B | django__django-17029 | pass | 7 | 14,387 | 822 | 18.2s | solved | [`Prism-ML-Ternary-Bonsai-27B__django__django-17029.json`](runs/Prism-ML-Ternary-Bonsai-27B/Prism-ML-Ternary-Bonsai-27B__django__django-17029.json) |
| Prism-ML/Ternary-Bonsai-27B | pydata__xarray-4629 | fail | 1 | 1,894 | 10,000 | 350.2s | Output token limit reached | [`Prism-ML-Ternary-Bonsai-27B__pydata__xarray-4629.json`](runs/Prism-ML-Ternary-Bonsai-27B/Prism-ML-Ternary-Bonsai-27B__pydata__xarray-4629.json) |
| Prism-ML/Ternary-Bonsai-27B | scikit-learn__scikit-learn-13439 | fail | 19 | 98,238 | 10,000 | 131.4s | Output token limit reached | [`Prism-ML-Ternary-Bonsai-27B__scikit-learn__scikit-learn-13439.json`](runs/Prism-ML-Ternary-Bonsai-27B/Prism-ML-Ternary-Bonsai-27B__scikit-learn__scikit-learn-13439.json) |
| Prism-ML/Ternary-Bonsai-27B | sympy__sympy-13480 | pass | 4 | 145,094 | 443 | 77.1s | solved | [`Prism-ML-Ternary-Bonsai-27B__sympy__sympy-13480.json`](runs/Prism-ML-Ternary-Bonsai-27B/Prism-ML-Ternary-Bonsai-27B__sympy__sympy-13480.json) |
| Prism-ML/Ternary-Bonsai-27B | sympy__sympy-14711 | fail | 30 | 134,432 | 2,932 | 63.3s | Iterations limit reached | [`Prism-ML-Ternary-Bonsai-27B__sympy__sympy-14711.json`](runs/Prism-ML-Ternary-Bonsai-27B/Prism-ML-Ternary-Bonsai-27B__sympy__sympy-14711.json) |
| Prism-ML/Ternary-Bonsai-27B | sympy__sympy-18189 | pass | 5 | 174,169 | 596 | 146.5s | solved | [`Prism-ML-Ternary-Bonsai-27B__sympy__sympy-18189.json`](runs/Prism-ML-Ternary-Bonsai-27B/Prism-ML-Ternary-Bonsai-27B__sympy__sympy-18189.json) |
| codestral-2508 | django__django-11066 | pass | 7 | 16,294 | 405 | 12.7s | solved | [`codestral-2508__django__django-11066.json`](runs/codestral-2508/codestral-2508__django__django-11066.json) |
| codestral-2508 | django__django-17029 | fail | 30 | 137,356 | 6,504 | 83.5s | Iterations limit reached | [`codestral-2508__django__django-17029.json`](runs/codestral-2508/codestral-2508__django__django-17029.json) |
| codestral-2508 | pydata__xarray-4629 | pass | 7 | 31,343 | 364 | 11.4s | solved | [`codestral-2508__pydata__xarray-4629.json`](runs/codestral-2508/codestral-2508__pydata__xarray-4629.json) |
| codestral-2508 | scikit-learn__scikit-learn-13439 | fail | 30 | 130,685 | 3,022 | 164.3s | Iterations limit reached | [`codestral-2508__scikit-learn__scikit-learn-13439.json`](runs/codestral-2508/codestral-2508__scikit-learn__scikit-learn-13439.json) |
| codestral-2508 | sympy__sympy-13480 | fail | 4 | 148,612 | 282 | 49.6s | Input token limit reached | [`codestral-2508__sympy__sympy-13480.json`](runs/codestral-2508/codestral-2508__sympy__sympy-13480.json) |
| codestral-2508 | sympy__sympy-14711 | fail | 16 | 273,344 | 1,558 | 46.7s | Input token limit reached | [`codestral-2508__sympy__sympy-14711.json`](runs/codestral-2508/codestral-2508__sympy__sympy-14711.json) |
| codestral-2508 | sympy__sympy-18189 | fail | 7 | 186,910 | 487 | 129.6s | Input token limit reached | [`codestral-2508__sympy__sympy-18189.json`](runs/codestral-2508/codestral-2508__sympy__sympy-18189.json) |
| dots-studio/dots-3-note-preview:free | django__django-11066 | pass | 8 | 19,715 | 963 | 32.4s | solved | [`dots-studio-dots-3-note-preview:free__django__django-11066.json`](runs/dots-studio-dots-3-note-preview:free/dots-studio-dots-3-note-preview:free__django__django-11066.json) |
| dots-studio/dots-3-note-preview:free | django__django-17029 | pass | 10 | 23,224 | 1,648 | 41.3s | solved | [`dots-studio-dots-3-note-preview:free__django__django-17029.json`](runs/dots-studio-dots-3-note-preview:free/dots-studio-dots-3-note-preview:free__django__django-17029.json) |
| dots-studio/dots-3-note-preview:free | pydata__xarray-4629 | pass | 6 | 29,261 | 690 | 27.0s | solved | [`dots-studio-dots-3-note-preview:free__pydata__xarray-4629.json`](runs/dots-studio-dots-3-note-preview:free/dots-studio-dots-3-note-preview:free__pydata__xarray-4629.json) |
| dots-studio/dots-3-note-preview:free | scikit-learn__scikit-learn-13439 | pass | 10 | 193,123 | 7,254 | 127.6s | solved | [`dots-studio-dots-3-note-preview:free__scikit-learn__scikit-learn-13439.json`](runs/dots-studio-dots-3-note-preview:free/dots-studio-dots-3-note-preview:free__scikit-learn__scikit-learn-13439.json) |
| dots-studio/dots-3-note-preview:free | sympy__sympy-13480 | fail | 5 | 151,467 | 887 | 78.5s | Input token limit reached | [`dots-studio-dots-3-note-preview:free__sympy__sympy-13480.json`](runs/dots-studio-dots-3-note-preview:free/dots-studio-dots-3-note-preview:free__sympy__sympy-13480.json) |
| dots-studio/dots-3-note-preview:free | sympy__sympy-14711 | fail | 30 | 145,751 | 6,319 | 124.0s | Iterations limit reached | [`dots-studio-dots-3-note-preview:free__sympy__sympy-14711.json`](runs/dots-studio-dots-3-note-preview:free/dots-studio-dots-3-note-preview:free__sympy__sympy-14711.json) |
| dots-studio/dots-3-note-preview:free | sympy__sympy-18189 | fail | 7 | 189,785 | 1,120 | 168.9s | Input token limit reached | [`dots-studio-dots-3-note-preview:free__sympy__sympy-18189.json`](runs/dots-studio-dots-3-note-preview:free/dots-studio-dots-3-note-preview:free__sympy__sympy-18189.json) |
| google/gemma-4-31b-it:free | django__django-11066 | pass | 5 | 12,942 | 477 | 406.0s | solved | [`google-gemma-4-31b-it:free__django__django-11066.json`](runs/google-gemma-4-31b-it:free/google-gemma-4-31b-it:free__django__django-11066.json) |
| google/gemma-4-31b-it:free | django__django-17029 | fail | 12 | 23,909 | 868 | 809.7s | Time limit reached | [`google-gemma-4-31b-it:free__django__django-17029.json`](runs/google-gemma-4-31b-it:free/google-gemma-4-31b-it:free__django__django-17029.json) |
| google/gemma-4-31b-it:free | pydata__xarray-4629 | fail | 4 | 9,945 | 1,759 | 233.8s | Empty final answer | [`google-gemma-4-31b-it:free__pydata__xarray-4629.json`](runs/google-gemma-4-31b-it:free/google-gemma-4-31b-it:free__pydata__xarray-4629.json) |
| google/gemma-4-31b-it:free | scikit-learn__scikit-learn-13439 | fail | 5 | 9,307 | 1,630 | 470.9s | Empty final answer | [`google-gemma-4-31b-it:free__scikit-learn__scikit-learn-13439.json`](runs/google-gemma-4-31b-it:free/google-gemma-4-31b-it:free__scikit-learn__scikit-learn-13439.json) |
| google/gemma-4-31b-it:free | sympy__sympy-13480 | pass | 7 | 6,388 | 605 | 435.6s | solved | [`google-gemma-4-31b-it:free__sympy__sympy-13480.json`](runs/google-gemma-4-31b-it:free/google-gemma-4-31b-it:free__sympy__sympy-13480.json) |
| google/gemma-4-31b-it:free | sympy__sympy-14711 | fail | 12 | 7,995 | 454 | 786.3s | Time limit reached | [`google-gemma-4-31b-it:free__sympy__sympy-14711.json`](runs/google-gemma-4-31b-it:free/google-gemma-4-31b-it:free__sympy__sympy-14711.json) |
| google/gemma-4-31b-it:free | sympy__sympy-18189 | pass | 6 | 18,709 | 3,061 | 655.0s | solved | [`google-gemma-4-31b-it:free__sympy__sympy-18189.json`](runs/google-gemma-4-31b-it:free/google-gemma-4-31b-it:free__sympy__sympy-18189.json) |
| ministral-14b-2512 | django__django-11066 | pass | 7 | 17,793 | 855 | 21.5s | solved | [`ministral-14b-2512__django__django-11066.json`](runs/ministral-14b-2512/ministral-14b-2512__django__django-11066.json) |
| ministral-14b-2512 | django__django-17029 | pass | 7 | 14,865 | 785 | 14.3s | solved | [`ministral-14b-2512__django__django-17029.json`](runs/ministral-14b-2512/ministral-14b-2512__django__django-17029.json) |
| ministral-14b-2512 | pydata__xarray-4629 | pass | 6 | 28,203 | 383 | 13.2s | solved | [`ministral-14b-2512__pydata__xarray-4629.json`](runs/ministral-14b-2512/ministral-14b-2512__pydata__xarray-4629.json) |
| ministral-14b-2512 | scikit-learn__scikit-learn-13439 | pass | 25 | 285,039 | 2,533 | 92.0s | solved | [`ministral-14b-2512__scikit-learn__scikit-learn-13439.json`](runs/ministral-14b-2512/ministral-14b-2512__scikit-learn__scikit-learn-13439.json) |
| ministral-14b-2512 | sympy__sympy-13480 | pass | 4 | 148,748 | 341 | 61.4s | solved | [`ministral-14b-2512__sympy__sympy-13480.json`](runs/ministral-14b-2512/ministral-14b-2512__sympy__sympy-13480.json) |
| ministral-14b-2512 | sympy__sympy-14711 | pass | 10 | 35,568 | 1,401 | 27.9s | solved | [`ministral-14b-2512__sympy__sympy-14711.json`](runs/ministral-14b-2512/ministral-14b-2512__sympy__sympy-14711.json) |
| ministral-14b-2512 | sympy__sympy-18189 | pass | 19 | 241,718 | 2,305 | 164.2s | solved | [`ministral-14b-2512__sympy__sympy-18189.json`](runs/ministral-14b-2512/ministral-14b-2512__sympy__sympy-18189.json) |
| ministral-3b-2512 | django__django-11066 | fail | 25 | 102,678 | 5,189 | 32.5s | solved | [`ministral-3b-2512__django__django-11066.json`](runs/ministral-3b-2512/ministral-3b-2512__django__django-11066.json) |
| ministral-3b-2512 | django__django-17029 | pass | 26 | 77,424 | 1,775 | 45.1s | solved | [`ministral-3b-2512__django__django-17029.json`](runs/ministral-3b-2512/ministral-3b-2512__django__django-17029.json) |
| ministral-3b-2512 | pydata__xarray-4629 | pass | 7 | 28,308 | 217 | 6.8s | solved | [`ministral-3b-2512__pydata__xarray-4629.json`](runs/ministral-3b-2512/ministral-3b-2512__pydata__xarray-4629.json) |
| ministral-3b-2512 | scikit-learn__scikit-learn-13439 | fail | 30 | 63,398 | 1,121 | 21.0s | Iterations limit reached | [`ministral-3b-2512__scikit-learn__scikit-learn-13439.json`](runs/ministral-3b-2512/ministral-3b-2512__scikit-learn__scikit-learn-13439.json) |
| ministral-3b-2512 | sympy__sympy-13480 | fail | 30 | 67,201 | 2,200 | 34.7s | Iterations limit reached | [`ministral-3b-2512__sympy__sympy-13480.json`](runs/ministral-3b-2512/ministral-3b-2512__sympy__sympy-13480.json) |
| ministral-3b-2512 | sympy__sympy-14711 | fail | 30 | 62,422 | 1,468 | 17.6s | Iterations limit reached | [`ministral-3b-2512__sympy__sympy-14711.json`](runs/ministral-3b-2512/ministral-3b-2512__sympy__sympy-14711.json) |
| ministral-3b-2512 | sympy__sympy-18189 | fail | 30 | 99,534 | 2,848 | 24.2s | Iterations limit reached | [`ministral-3b-2512__sympy__sympy-18189.json`](runs/ministral-3b-2512/ministral-3b-2512__sympy__sympy-18189.json) |
| ministral-8b-2512 | django__django-11066 | pass | 6 | 14,436 | 599 | 12.4s | solved | [`ministral-8b-2512__django__django-11066.json`](runs/ministral-8b-2512/ministral-8b-2512__django__django-11066.json) |
| ministral-8b-2512 | django__django-17029 | pass | 7 | 14,747 | 747 | 13.6s | solved | [`ministral-8b-2512__django__django-17029.json`](runs/ministral-8b-2512/ministral-8b-2512__django__django-17029.json) |
| ministral-8b-2512 | pydata__xarray-4629 | pass | 5 | 24,554 | 565 | 29.9s | solved | [`ministral-8b-2512__pydata__xarray-4629.json`](runs/ministral-8b-2512/ministral-8b-2512__pydata__xarray-4629.json) |
| ministral-8b-2512 | scikit-learn__scikit-learn-13439 | pass | 14 | 172,702 | 1,498 | 66.5s | solved | [`ministral-8b-2512__scikit-learn__scikit-learn-13439.json`](runs/ministral-8b-2512/ministral-8b-2512__scikit-learn__scikit-learn-13439.json) |
| ministral-8b-2512 | sympy__sympy-13480 | pass | 4 | 148,911 | 447 | 60.0s | solved | [`ministral-8b-2512__sympy__sympy-13480.json`](runs/ministral-8b-2512/ministral-8b-2512__sympy__sympy-13480.json) |
| ministral-8b-2512 | sympy__sympy-14711 | fail | 30 | 292,368 | 7,906 | 126.8s | Iterations limit reached | [`ministral-8b-2512__sympy__sympy-14711.json`](runs/ministral-8b-2512/ministral-8b-2512__sympy__sympy-14711.json) |
| ministral-8b-2512 | sympy__sympy-18189 | pass | 10 | 196,326 | 1,257 | 132.7s | solved | [`ministral-8b-2512__sympy__sympy-18189.json`](runs/ministral-8b-2512/ministral-8b-2512__sympy__sympy-18189.json) |
| nex-agi/nex-n2.5-mini:free | django__django-11066 | fail | 30 | 198,251 | 3,484 | 76.1s | Iterations limit reached | [`nex-agi-nex-n2.5-mini:free__django__django-11066.json`](runs/nex-agi-nex-n2.5-mini:free/nex-agi-nex-n2.5-mini:free__django__django-11066.json) |
| nex-agi/nex-n2.5-mini:free | django__django-17029 | fail | 27 | 297,380 | 3,548 | 61.0s | Input token limit reached | [`nex-agi-nex-n2.5-mini:free__django__django-17029.json`](runs/nex-agi-nex-n2.5-mini:free/nex-agi-nex-n2.5-mini:free__django__django-17029.json) |
| nex-agi/nex-n2.5-mini:free | pydata__xarray-4629 | pass | 8 | 47,285 | 557 | 34.8s | solved | [`nex-agi-nex-n2.5-mini:free__pydata__xarray-4629.json`](runs/nex-agi-nex-n2.5-mini:free/nex-agi-nex-n2.5-mini:free__pydata__xarray-4629.json) |
| nex-agi/nex-n2.5-mini:free | scikit-learn__scikit-learn-13439 | fail | 0 | 0 | 0 | 1.0s | Agent loop error | [`nex-agi-nex-n2.5-mini:free__scikit-learn__scikit-learn-13439.json`](runs/nex-agi-nex-n2.5-mini:free/nex-agi-nex-n2.5-mini:free__scikit-learn__scikit-learn-13439.json) |
| nex-agi/nex-n2.5-mini:free | sympy__sympy-13480 | fail | 0 | 0 | 0 | 0.9s | Agent loop error | [`nex-agi-nex-n2.5-mini:free__sympy__sympy-13480.json`](runs/nex-agi-nex-n2.5-mini:free/nex-agi-nex-n2.5-mini:free__sympy__sympy-13480.json) |
| nex-agi/nex-n2.5-mini:free | sympy__sympy-14711 | fail | 1 | 2,231 | 10,000 | 62.7s | Output token limit reached | [`nex-agi-nex-n2.5-mini:free__sympy__sympy-14711.json`](runs/nex-agi-nex-n2.5-mini:free/nex-agi-nex-n2.5-mini:free__sympy__sympy-14711.json) |
| nex-agi/nex-n2.5-mini:free | sympy__sympy-18189 | fail | 0 | 0 | 0 | 0.9s | Agent loop error | [`nex-agi-nex-n2.5-mini:free__sympy__sympy-18189.json`](runs/nex-agi-nex-n2.5-mini:free/nex-agi-nex-n2.5-mini:free__sympy__sympy-18189.json) |
| openai/gpt-oss-120b | django__django-11066 | fail | 2 | 4,564 | 1,314 | 4.4s | Empty final answer | [`openai-gpt-oss-120b__django__django-11066.json`](runs/openai-gpt-oss-120b/openai-gpt-oss-120b__django__django-11066.json) |
| openai/gpt-oss-120b | django__django-17029 | fail | 2 | 4,921 | 4,480 | 60.1s | Empty final answer | [`openai-gpt-oss-120b__django__django-17029.json`](runs/openai-gpt-oss-120b/openai-gpt-oss-120b__django__django-17029.json) |
| openai/gpt-oss-120b | pydata__xarray-4629 | pass | 2 | 4,368 | 903 | 4.2s | solved | [`openai-gpt-oss-120b__pydata__xarray-4629.json`](runs/openai-gpt-oss-120b/openai-gpt-oss-120b__pydata__xarray-4629.json) |
| openai/gpt-oss-120b | scikit-learn__scikit-learn-13439 | fail | 3 | 8,022 | 10,000 | 60.0s | Output token limit reached | [`openai-gpt-oss-120b__scikit-learn__scikit-learn-13439.json`](runs/openai-gpt-oss-120b/openai-gpt-oss-120b__scikit-learn__scikit-learn-13439.json) |
| openai/gpt-oss-120b | sympy__sympy-13480 | fail | 4 | 6,260 | 636 | 46.2s | Agent loop error | [`openai-gpt-oss-120b__sympy__sympy-13480.json`](runs/openai-gpt-oss-120b/openai-gpt-oss-120b__sympy__sympy-13480.json) |
| openai/gpt-oss-120b | sympy__sympy-14711 | fail | 2 | 4,701 | 3,525 | 10.8s | Empty final answer | [`openai-gpt-oss-120b__sympy__sympy-14711.json`](runs/openai-gpt-oss-120b/openai-gpt-oss-120b__sympy__sympy-14711.json) |
| openai/gpt-oss-120b | sympy__sympy-18189 | fail | 3 | 6,589 | 6,525 | 73.9s | Output token limit reached | [`openai-gpt-oss-120b__sympy__sympy-18189.json`](runs/openai-gpt-oss-120b/openai-gpt-oss-120b__sympy__sympy-18189.json) |
| poolside/laguna-s-2.1:free | django__django-11066 | fail | 1 | 1,900 | 10,000 | 187.6s | Output token limit reached | [`poolside-laguna-s-2.1:free__django__django-11066.json`](runs/poolside-laguna-s-2.1:free/poolside-laguna-s-2.1:free__django__django-11066.json) |
| poolside/laguna-s-2.1:free | django__django-17029 | fail | 1 | 1,258 | 10,000 | 195.6s | Output token limit reached | [`poolside-laguna-s-2.1:free__django__django-17029.json`](runs/poolside-laguna-s-2.1:free/poolside-laguna-s-2.1:free__django__django-17029.json) |
| poolside/laguna-s-2.1:free | pydata__xarray-4629 | pass | 5 | 24,564 | 881 | 83.7s | solved | [`poolside-laguna-s-2.1:free__pydata__xarray-4629.json`](runs/poolside-laguna-s-2.1:free/poolside-laguna-s-2.1:free__pydata__xarray-4629.json) |
| poolside/laguna-s-2.1:free | scikit-learn__scikit-learn-13439 | fail | 30 | 166,426 | 2,776 | 164.6s | Iterations limit reached | [`poolside-laguna-s-2.1:free__scikit-learn__scikit-learn-13439.json`](runs/poolside-laguna-s-2.1:free/poolside-laguna-s-2.1:free__scikit-learn__scikit-learn-13439.json) |
| poolside/laguna-s-2.1:free | sympy__sympy-13480 | pass | 5 | 140,001 | 477 | 210.2s | solved | [`poolside-laguna-s-2.1:free__sympy__sympy-13480.json`](runs/poolside-laguna-s-2.1:free/poolside-laguna-s-2.1:free__sympy__sympy-13480.json) |
| poolside/laguna-s-2.1:free | sympy__sympy-14711 | fail | 1 | 1,297 | 10,000 | 204.4s | Output token limit reached | [`poolside-laguna-s-2.1:free__sympy__sympy-14711.json`](runs/poolside-laguna-s-2.1:free/poolside-laguna-s-2.1:free__sympy__sympy-14711.json) |
| poolside/laguna-s-2.1:free | sympy__sympy-18189 | fail | 30 | 107,681 | 2,493 | 144.9s | Iterations limit reached | [`poolside-laguna-s-2.1:free__sympy__sympy-18189.json`](runs/poolside-laguna-s-2.1:free/poolside-laguna-s-2.1:free__sympy__sympy-18189.json) |
| qwen/qwen3.8-27b | django__django-11066 | pass | 4 | 9,322 | 230 | 20.9s | solved | [`qwen-qwen3.8-27b__django__django-11066.json`](runs/qwen-qwen3.8-27b/qwen-qwen3.8-27b__django__django-11066.json) |
| qwen/qwen3.8-27b | django__django-17029 | pass | 7 | 13,238 | 412 | 112.0s | solved | [`qwen-qwen3.8-27b__django__django-17029.json`](runs/qwen-qwen3.8-27b/qwen-qwen3.8-27b__django__django-17029.json) |
| qwen/qwen3.8-27b | pydata__xarray-4629 | fail | 4 | 8,631 | 149 | 32.0s | Agent loop error | [`qwen-qwen3.8-27b__pydata__xarray-4629.json`](runs/qwen-qwen3.8-27b/qwen-qwen3.8-27b__pydata__xarray-4629.json) |
| qwen/qwen3.8-27b | scikit-learn__scikit-learn-13439 | fail | 14 | 57,751 | 567 | 473.9s | Agent loop error | [`qwen-qwen3.8-27b__scikit-learn__scikit-learn-13439.json`](runs/qwen-qwen3.8-27b/qwen-qwen3.8-27b__scikit-learn__scikit-learn-13439.json) |
| qwen/qwen3.8-27b | sympy__sympy-13480 | fail | 3 | 4,360 | 137 | 69.2s | Agent loop error | [`qwen-qwen3.8-27b__sympy__sympy-13480.json`](runs/qwen-qwen3.8-27b/qwen-qwen3.8-27b__sympy__sympy-13480.json) |
| qwen/qwen3.8-27b | sympy__sympy-14711 | fail | 7 | 15,100 | 414 | 98.8s | Agent loop error | [`qwen-qwen3.8-27b__sympy__sympy-14711.json`](runs/qwen-qwen3.8-27b/qwen-qwen3.8-27b__sympy__sympy-14711.json) |
| qwen/qwen3.8-27b | sympy__sympy-18189 | fail | 5 | 15,021 | 400 | 202.2s | Agent loop error | [`qwen-qwen3.8-27b__sympy__sympy-18189.json`](runs/qwen-qwen3.8-27b/qwen-qwen3.8-27b__sympy__sympy-18189.json) |
| qwen/qwen3.8-27b:free | django__django-11066 | pass | 8 | 22,740 | 790 | 63.3s | solved | [`qwen-qwen3.8-27b:free__django__django-11066.json`](runs/qwen-qwen3.8-27b:free/qwen-qwen3.8-27b:free__django__django-11066.json) |
| qwen/qwen3.8-27b:free | django__django-17029 | pass | 8 | 19,086 | 669 | 60.7s | solved | [`qwen-qwen3.8-27b:free__django__django-17029.json`](runs/qwen-qwen3.8-27b:free/qwen-qwen3.8-27b:free__django__django-17029.json) |
| qwen/qwen3.8-27b:free | pydata__xarray-4629 | not judged | 0 | 0 | 0 | 16.8s | Agent loop error | [`qwen-qwen3.8-27b:free__pydata__xarray-4629.json`](runs/qwen-qwen3.8-27b:free/qwen-qwen3.8-27b:free__pydata__xarray-4629.json) |
| qwen/qwen3.8-27b:free | scikit-learn__scikit-learn-13439 | fail | 1 | 1,504 | 9,612 | 575.1s | Time limit reached | [`qwen-qwen3.8-27b:free__scikit-learn__scikit-learn-13439.json`](runs/qwen-qwen3.8-27b:free/qwen-qwen3.8-27b:free__scikit-learn__scikit-learn-13439.json) |
| qwen/qwen3.8-27b:free | sympy__sympy-13480 | not judged | 3 | 4,950 | 343 | 83.7s | Agent loop error | [`qwen-qwen3.8-27b:free__sympy__sympy-13480.json`](runs/qwen-qwen3.8-27b:free/qwen-qwen3.8-27b:free__sympy__sympy-13480.json) |
| qwen/qwen3.8-27b:free | sympy__sympy-14711 | fail | 20 | 115,727 | 8,152 | 241.2s | Output token limit reached | [`qwen-qwen3.8-27b:free__sympy__sympy-14711.json`](runs/qwen-qwen3.8-27b:free/qwen-qwen3.8-27b:free__sympy__sympy-14711.json) |
| qwen/qwen3.8-27b:free | sympy__sympy-18189 | pass | 10 | 197,833 | 1,248 | 190.2s | solved | [`qwen-qwen3.8-27b:free__sympy__sympy-18189.json`](runs/qwen-qwen3.8-27b:free/qwen-qwen3.8-27b:free__sympy__sympy-18189.json) |
| stealth/space-bunny-alpha | django__django-11066 | pass | 13 | 46,314 | 926 | 143.0s | solved | [`stealth-space-bunny-alpha__django__django-11066.json`](runs/stealth-space-bunny-alpha/stealth-space-bunny-alpha__django__django-11066.json) |
| stealth/space-bunny-alpha | django__django-17029 | fail | 9 | 22,811 | 488 | 764.1s | Time limit reached | [`stealth-space-bunny-alpha__django__django-17029.json`](runs/stealth-space-bunny-alpha/stealth-space-bunny-alpha__django__django-17029.json) |
| stealth/space-bunny-alpha | pydata__xarray-4629 | pass | 19 | 97,835 | 1,785 | 430.1s | solved | [`stealth-space-bunny-alpha__pydata__xarray-4629.json`](runs/stealth-space-bunny-alpha/stealth-space-bunny-alpha__pydata__xarray-4629.json) |
| stealth/space-bunny-alpha | scikit-learn__scikit-learn-13439 | fail | 8 | 19,534 | 462 | 856.8s | Time limit reached | [`stealth-space-bunny-alpha__scikit-learn__scikit-learn-13439.json`](runs/stealth-space-bunny-alpha/stealth-space-bunny-alpha__scikit-learn__scikit-learn-13439.json) |
| stealth/space-bunny-alpha | sympy__sympy-13480 | pass | 6 | 126,170 | 393 | 62.1s | solved | [`stealth-space-bunny-alpha__sympy__sympy-13480.json`](runs/stealth-space-bunny-alpha/stealth-space-bunny-alpha__sympy__sympy-13480.json) |
| stealth/space-bunny-alpha | sympy__sympy-14711 | fail | 8 | 16,401 | 786 | 693.6s | Time limit reached | [`stealth-space-bunny-alpha__sympy__sympy-14711.json`](runs/stealth-space-bunny-alpha/stealth-space-bunny-alpha__sympy__sympy-14711.json) |
| stealth/space-bunny-alpha | sympy__sympy-18189 | pass | 7 | 154,687 | 524 | 255.2s | solved | [`stealth-space-bunny-alpha__sympy__sympy-18189.json`](runs/stealth-space-bunny-alpha/stealth-space-bunny-alpha__sympy__sympy-18189.json) |
| z-ai/glm-5.2:free | django__django-11066 | pass | 4 | 8,625 | 129 | 77.0s | solved | [`z-ai-glm-5.2:free__django__django-11066.json`](runs/z-ai-glm-5.2:free/z-ai-glm-5.2:free__django__django-11066.json) |
| z-ai/glm-5.2:free | django__django-17029 | fail | 0 | 0 | 0 | 1.1s | Agent loop error | [`z-ai-glm-5.2:free__django__django-17029.json`](runs/z-ai-glm-5.2:free/z-ai-glm-5.2:free__django__django-17029.json) |
| z-ai/glm-5.2:free | pydata__xarray-4629 | pass | 4 | 19,946 | 133 | 144.0s | solved | [`z-ai-glm-5.2:free__pydata__xarray-4629.json`](runs/z-ai-glm-5.2:free/z-ai-glm-5.2:free__pydata__xarray-4629.json) |
| z-ai/glm-5.2:free | scikit-learn__scikit-learn-13439 | fail | 0 | 0 | 0 | 1.0s | Agent loop error | [`z-ai-glm-5.2:free__scikit-learn__scikit-learn-13439.json`](runs/z-ai-glm-5.2:free/z-ai-glm-5.2:free__scikit-learn__scikit-learn-13439.json) |
| z-ai/glm-5.2:free | sympy__sympy-13480 | fail | 0 | 0 | 0 | 1.4s | Agent loop error | [`z-ai-glm-5.2:free__sympy__sympy-13480.json`](runs/z-ai-glm-5.2:free/z-ai-glm-5.2:free__sympy__sympy-13480.json) |
| z-ai/glm-5.2:free | sympy__sympy-14711 | fail | 0 | 0 | 0 | 0.9s | Agent loop error | [`z-ai-glm-5.2:free__sympy__sympy-14711.json`](runs/z-ai-glm-5.2:free/z-ai-glm-5.2:free__sympy__sympy-14711.json) |
| z-ai/glm-5.2:free | sympy__sympy-18189 | fail | 0 | 0 | 0 | 0.9s | Agent loop error | [`z-ai-glm-5.2:free__sympy__sympy-18189.json`](runs/z-ai-glm-5.2:free/z-ai-glm-5.2:free__sympy__sympy-18189.json) |

</details>

<details>
<summary>MBPP — every (model, task) cell, with the solution.json behind it</summary>

| Model | Task | Result | Iterations | Tokens in | Tokens out | Wall time | Stopped because | Evidence |
|---|---|---|---:|---:|---:|---:|---|---|
| Prism-ML/Ternary-Bonsai-27B | 103 | fail | 1 | 501 | 1,500 | 38.3s | Output token limit reached | [`Prism-ML-Ternary-Bonsai-27B__mbpp-103.json`](runs/Prism-ML-Ternary-Bonsai-27B/mbpp_task/Prism-ML-Ternary-Bonsai-27B__mbpp-103.json) |
| Prism-ML/Ternary-Bonsai-27B | 11 | fail | 1 | 504 | 1,500 | 30.5s | Output token limit reached | [`Prism-ML-Ternary-Bonsai-27B__mbpp-11.json`](runs/Prism-ML-Ternary-Bonsai-27B/mbpp_task/Prism-ML-Ternary-Bonsai-27B__mbpp-11.json) |
| Prism-ML/Ternary-Bonsai-27B | 135 | fail | 1 | 491 | 922 | 25.9s | Output token limit reached | [`Prism-ML-Ternary-Bonsai-27B__mbpp-135.json`](runs/Prism-ML-Ternary-Bonsai-27B/mbpp_task/Prism-ML-Ternary-Bonsai-27B__mbpp-135.json) |
| Prism-ML/Ternary-Bonsai-27B | 227 | pass | 2 | 1,065 | 201 | 5.2s | solved | [`Prism-ML-Ternary-Bonsai-27B__mbpp-227.json`](runs/Prism-ML-Ternary-Bonsai-27B/mbpp_task/Prism-ML-Ternary-Bonsai-27B__mbpp-227.json) |
| Prism-ML/Ternary-Bonsai-27B | 257 | pass | 2 | 1,060 | 182 | 6.2s | solved | [`Prism-ML-Ternary-Bonsai-27B__mbpp-257.json`](runs/Prism-ML-Ternary-Bonsai-27B/mbpp_task/Prism-ML-Ternary-Bonsai-27B__mbpp-257.json) |
| Prism-ML/Ternary-Bonsai-27B | 285 | fail | 1 | 502 | 1,500 | 19.9s | Output token limit reached | [`Prism-ML-Ternary-Bonsai-27B__mbpp-285.json`](runs/Prism-ML-Ternary-Bonsai-27B/mbpp_task/Prism-ML-Ternary-Bonsai-27B__mbpp-285.json) |
| Prism-ML/Ternary-Bonsai-27B | 390 | fail | 1 | 546 | 1,247 | 20.5s | Output token limit reached | [`Prism-ML-Ternary-Bonsai-27B__mbpp-390.json`](runs/Prism-ML-Ternary-Bonsai-27B/mbpp_task/Prism-ML-Ternary-Bonsai-27B__mbpp-390.json) |
| Prism-ML/Ternary-Bonsai-27B | 418 | fail | 1 | 525 | 787 | 13.6s | Output token limit reached | [`Prism-ML-Ternary-Bonsai-27B__mbpp-418.json`](runs/Prism-ML-Ternary-Bonsai-27B/mbpp_task/Prism-ML-Ternary-Bonsai-27B__mbpp-418.json) |
| Prism-ML/Ternary-Bonsai-27B | 444 | fail | 1 | 663 | 1,500 | 23.0s | Output token limit reached | [`Prism-ML-Ternary-Bonsai-27B__mbpp-444.json`](runs/Prism-ML-Ternary-Bonsai-27B/mbpp_task/Prism-ML-Ternary-Bonsai-27B__mbpp-444.json) |
| Prism-ML/Ternary-Bonsai-27B | 75 | fail | 1 | 576 | 1,076 | 34.4s | Output token limit reached | [`Prism-ML-Ternary-Bonsai-27B__mbpp-75.json`](runs/Prism-ML-Ternary-Bonsai-27B/mbpp_task/Prism-ML-Ternary-Bonsai-27B__mbpp-75.json) |
| codestral-2508 | 103 | fail | 5 | 3,935 | 435 | 8.4s | Iterations limit reached | [`codestral-2508__mbpp-103.json`](runs/codestral-2508/mbpp_task/codestral-2508__mbpp-103.json) |
| codestral-2508 | 11 | pass | 2 | 1,040 | 158 | 3.2s | solved | [`codestral-2508__mbpp-11.json`](runs/codestral-2508/mbpp_task/codestral-2508__mbpp-11.json) |
| codestral-2508 | 135 | pass | 2 | 956 | 54 | 1.5s | solved | [`codestral-2508__mbpp-135.json`](runs/codestral-2508/mbpp_task/codestral-2508__mbpp-135.json) |
| codestral-2508 | 227 | pass | 2 | 995 | 60 | 1.3s | solved | [`codestral-2508__mbpp-227.json`](runs/codestral-2508/mbpp_task/codestral-2508__mbpp-227.json) |
| codestral-2508 | 257 | pass | 2 | 980 | 46 | 1.0s | solved | [`codestral-2508__mbpp-257.json`](runs/codestral-2508/mbpp_task/codestral-2508__mbpp-257.json) |
| codestral-2508 | 285 | fail | 5 | 3,465 | 190 | 4.0s | Iterations limit reached | [`codestral-2508__mbpp-285.json`](runs/codestral-2508/mbpp_task/codestral-2508__mbpp-285.json) |
| codestral-2508 | 390 | pass | 2 | 1,079 | 60 | 1.2s | solved | [`codestral-2508__mbpp-390.json`](runs/codestral-2508/mbpp_task/codestral-2508__mbpp-390.json) |
| codestral-2508 | 418 | pass | 2 | 1,040 | 54 | 1.1s | solved | [`codestral-2508__mbpp-418.json`](runs/codestral-2508/mbpp_task/codestral-2508__mbpp-418.json) |
| codestral-2508 | 444 | fail | 5 | 5,035 | 135 | 2.7s | Iterations limit reached | [`codestral-2508__mbpp-444.json`](runs/codestral-2508/mbpp_task/codestral-2508__mbpp-444.json) |
| codestral-2508 | 75 | pass | 2 | 1,174 | 114 | 1.4s | solved | [`codestral-2508__mbpp-75.json`](runs/codestral-2508/mbpp_task/codestral-2508__mbpp-75.json) |
| dots-studio/dots-3-note-preview:free | 103 | fail | 1 | 471 | 1,500 | 21.4s | Output token limit reached | [`dots-studio-dots-3-note-preview:free__mbpp-103.json`](runs/dots-studio-dots-3-note-preview:free/mbpp_task/dots-studio-dots-3-note-preview:free__mbpp-103.json) |
| dots-studio/dots-3-note-preview:free | 11 | fail | 1 | 472 | 1,500 | 20.3s | Output token limit reached | [`dots-studio-dots-3-note-preview:free__mbpp-11.json`](runs/dots-studio-dots-3-note-preview:free/mbpp_task/dots-studio-dots-3-note-preview:free__mbpp-11.json) |
| dots-studio/dots-3-note-preview:free | 135 | pass | 2 | 972 | 392 | 10.5s | solved | [`dots-studio-dots-3-note-preview:free__mbpp-135.json`](runs/dots-studio-dots-3-note-preview:free/mbpp_task/dots-studio-dots-3-note-preview:free__mbpp-135.json) |
| dots-studio/dots-3-note-preview:free | 227 | pass | 2 | 1,023 | 300 | 8.8s | solved | [`dots-studio-dots-3-note-preview:free__mbpp-227.json`](runs/dots-studio-dots-3-note-preview:free/mbpp_task/dots-studio-dots-3-note-preview:free__mbpp-227.json) |
| dots-studio/dots-3-note-preview:free | 257 | pass | 2 | 990 | 152 | 7.4s | solved | [`dots-studio-dots-3-note-preview:free__mbpp-257.json`](runs/dots-studio-dots-3-note-preview:free/mbpp_task/dots-studio-dots-3-note-preview:free__mbpp-257.json) |
| dots-studio/dots-3-note-preview:free | 285 | fail | 1 | 470 | 1,120 | 18.4s | Output token limit reached | [`dots-studio-dots-3-note-preview:free__mbpp-285.json`](runs/dots-studio-dots-3-note-preview:free/mbpp_task/dots-studio-dots-3-note-preview:free__mbpp-285.json) |
| dots-studio/dots-3-note-preview:free | 390 | pass | 2 | 1,080 | 641 | 13.4s | solved | [`dots-studio-dots-3-note-preview:free__mbpp-390.json`](runs/dots-studio-dots-3-note-preview:free/mbpp_task/dots-studio-dots-3-note-preview:free__mbpp-390.json) |
| dots-studio/dots-3-note-preview:free | 418 | pass | 2 | 1,031 | 384 | 12.1s | solved | [`dots-studio-dots-3-note-preview:free__mbpp-418.json`](runs/dots-studio-dots-3-note-preview:free/mbpp_task/dots-studio-dots-3-note-preview:free__mbpp-418.json) |
| dots-studio/dots-3-note-preview:free | 444 | fail | 1 | 631 | 1,178 | 18.1s | Output token limit reached | [`dots-studio-dots-3-note-preview:free__mbpp-444.json`](runs/dots-studio-dots-3-note-preview:free/mbpp_task/dots-studio-dots-3-note-preview:free__mbpp-444.json) |
| dots-studio/dots-3-note-preview:free | 75 | pass | 2 | 1,151 | 404 | 11.1s | solved | [`dots-studio-dots-3-note-preview:free__mbpp-75.json`](runs/dots-studio-dots-3-note-preview:free/mbpp_task/dots-studio-dots-3-note-preview:free__mbpp-75.json) |
| google/gemma-4-31b-it:free | 103 | pass | 2 | 1,455 | 589 | 95.5s | solved | [`google-gemma-4-31b-it:free__mbpp-103.json`](runs/google-gemma-4-31b-it:free/mbpp_task/google-gemma-4-31b-it:free__mbpp-103.json) |
| google/gemma-4-31b-it:free | 11 | fail | 1 | 518 | 166 | 81.6s | Time limit reached | [`google-gemma-4-31b-it:free__mbpp-11.json`](runs/google-gemma-4-31b-it:free/mbpp_task/google-gemma-4-31b-it:free__mbpp-11.json) |
| google/gemma-4-31b-it:free | 135 | pass | 2 | 1,085 | 94 | 75.3s | solved | [`google-gemma-4-31b-it:free__mbpp-135.json`](runs/google-gemma-4-31b-it:free/mbpp_task/google-gemma-4-31b-it:free__mbpp-135.json) |
| google/gemma-4-31b-it:free | 227 | pass | 2 | 1,131 | 129 | 87.8s | solved | [`google-gemma-4-31b-it:free__mbpp-227.json`](runs/google-gemma-4-31b-it:free/mbpp_task/google-gemma-4-31b-it:free__mbpp-227.json) |
| google/gemma-4-31b-it:free | 257 | fail | 1 | 0 | 0 | 62.4s | Time limit reached | [`google-gemma-4-31b-it:free__mbpp-257.json`](runs/google-gemma-4-31b-it:free/mbpp_task/google-gemma-4-31b-it:free__mbpp-257.json) |
| google/gemma-4-31b-it:free | 285 | pass | 2 | 1,225 | 221 | 52.7s | solved | [`google-gemma-4-31b-it:free__mbpp-285.json`](runs/google-gemma-4-31b-it:free/mbpp_task/google-gemma-4-31b-it:free__mbpp-285.json) |
| google/gemma-4-31b-it:free | 390 | pass | 2 | 1,183 | 77 | 92.4s | solved | [`google-gemma-4-31b-it:free__mbpp-390.json`](runs/google-gemma-4-31b-it:free/mbpp_task/google-gemma-4-31b-it:free__mbpp-390.json) |
| google/gemma-4-31b-it:free | 418 | fail | 1 | 542 | 73 | 62.5s | Time limit reached | [`google-gemma-4-31b-it:free__mbpp-418.json`](runs/google-gemma-4-31b-it:free/mbpp_task/google-gemma-4-31b-it:free__mbpp-418.json) |
| google/gemma-4-31b-it:free | 444 | fail | 2 | 680 | 87 | 101.8s | Time limit reached | [`google-gemma-4-31b-it:free__mbpp-444.json`](runs/google-gemma-4-31b-it:free/mbpp_task/google-gemma-4-31b-it:free__mbpp-444.json) |
| google/gemma-4-31b-it:free | 75 | pass | 2 | 1,271 | 133 | 54.7s | solved | [`google-gemma-4-31b-it:free__mbpp-75.json`](runs/google-gemma-4-31b-it:free/mbpp_task/google-gemma-4-31b-it:free__mbpp-75.json) |
| ministral-14b-2512 | 103 | fail | 4 | 3,354 | 1,345 | 13.1s | Output token limit reached | [`ministral-14b-2512__mbpp-103.json`](runs/ministral-14b-2512/mbpp_task/ministral-14b-2512__mbpp-103.json) |
| ministral-14b-2512 | 11 | fail | 2 | 1,019 | 116 | 3.5s | solved | [`ministral-14b-2512__mbpp-11.json`](runs/ministral-14b-2512/mbpp_task/ministral-14b-2512__mbpp-11.json) |
| ministral-14b-2512 | 135 | pass | 2 | 956 | 54 | 1.0s | solved | [`ministral-14b-2512__mbpp-135.json`](runs/ministral-14b-2512/mbpp_task/ministral-14b-2512__mbpp-135.json) |
| ministral-14b-2512 | 227 | pass | 2 | 995 | 60 | 1.1s | solved | [`ministral-14b-2512__mbpp-227.json`](runs/ministral-14b-2512/mbpp_task/ministral-14b-2512__mbpp-227.json) |
| ministral-14b-2512 | 257 | pass | 2 | 980 | 46 | 2.0s | solved | [`ministral-14b-2512__mbpp-257.json`](runs/ministral-14b-2512/mbpp_task/ministral-14b-2512__mbpp-257.json) |
| ministral-14b-2512 | 285 | pass | 4 | 2,538 | 239 | 3.3s | solved | [`ministral-14b-2512__mbpp-285.json`](runs/ministral-14b-2512/mbpp_task/ministral-14b-2512__mbpp-285.json) |
| ministral-14b-2512 | 390 | pass | 2 | 1,079 | 60 | 2.1s | solved | [`ministral-14b-2512__mbpp-390.json`](runs/ministral-14b-2512/mbpp_task/ministral-14b-2512__mbpp-390.json) |
| ministral-14b-2512 | 418 | pass | 2 | 1,043 | 60 | 1.2s | solved | [`ministral-14b-2512__mbpp-418.json`](runs/ministral-14b-2512/mbpp_task/ministral-14b-2512__mbpp-418.json) |
| ministral-14b-2512 | 444 | fail | 5 | 5,359 | 372 | 5.3s | Iterations limit reached | [`ministral-14b-2512__mbpp-444.json`](runs/ministral-14b-2512/mbpp_task/ministral-14b-2512__mbpp-444.json) |
| ministral-14b-2512 | 75 | pass | 2 | 1,159 | 84 | 1.4s | solved | [`ministral-14b-2512__mbpp-75.json`](runs/ministral-14b-2512/mbpp_task/ministral-14b-2512__mbpp-75.json) |
| ministral-3b-2512 | 103 | fail | 2 | 1,089 | 814 | 3.8s | Output token limit reached | [`ministral-3b-2512__mbpp-103.json`](runs/ministral-3b-2512/mbpp_task/ministral-3b-2512__mbpp-103.json) |
| ministral-3b-2512 | 11 | fail | 5 | 3,885 | 513 | 6.1s | Iterations limit reached | [`ministral-3b-2512__mbpp-11.json`](runs/ministral-3b-2512/mbpp_task/ministral-3b-2512__mbpp-11.json) |
| ministral-3b-2512 | 135 | pass | 2 | 956 | 54 | 0.8s | solved | [`ministral-3b-2512__mbpp-135.json`](runs/ministral-3b-2512/mbpp_task/ministral-3b-2512__mbpp-135.json) |
| ministral-3b-2512 | 227 | pass | 2 | 995 | 60 | 1.2s | solved | [`ministral-3b-2512__mbpp-227.json`](runs/ministral-3b-2512/mbpp_task/ministral-3b-2512__mbpp-227.json) |
| ministral-3b-2512 | 257 | pass | 2 | 981 | 48 | 0.9s | solved | [`ministral-3b-2512__mbpp-257.json`](runs/ministral-3b-2512/mbpp_task/ministral-3b-2512__mbpp-257.json) |
| ministral-3b-2512 | 285 | pass | 4 | 2,720 | 292 | 2.0s | solved | [`ministral-3b-2512__mbpp-285.json`](runs/ministral-3b-2512/mbpp_task/ministral-3b-2512__mbpp-285.json) |
| ministral-3b-2512 | 390 | pass | 2 | 1,079 | 60 | 1.4s | solved | [`ministral-3b-2512__mbpp-390.json`](runs/ministral-3b-2512/mbpp_task/ministral-3b-2512__mbpp-390.json) |
| ministral-3b-2512 | 418 | pass | 2 | 1,074 | 122 | 1.2s | solved | [`ministral-3b-2512__mbpp-418.json`](runs/ministral-3b-2512/mbpp_task/ministral-3b-2512__mbpp-418.json) |
| ministral-3b-2512 | 444 | fail | 5 | 5,712 | 563 | 4.0s | Iterations limit reached | [`ministral-3b-2512__mbpp-444.json`](runs/ministral-3b-2512/mbpp_task/ministral-3b-2512__mbpp-444.json) |
| ministral-3b-2512 | 75 | pass | 2 | 1,159 | 84 | 1.0s | solved | [`ministral-3b-2512__mbpp-75.json`](runs/ministral-3b-2512/mbpp_task/ministral-3b-2512__mbpp-75.json) |
| ministral-8b-2512 | 103 | fail | 5 | 4,984 | 1,189 | 12.1s | Iterations limit reached | [`ministral-8b-2512__mbpp-103.json`](runs/ministral-8b-2512/mbpp_task/ministral-8b-2512__mbpp-103.json) |
| ministral-8b-2512 | 11 | pass | 2 | 1,063 | 204 | 4.5s | solved | [`ministral-8b-2512__mbpp-11.json`](runs/ministral-8b-2512/mbpp_task/ministral-8b-2512__mbpp-11.json) |
| ministral-8b-2512 | 135 | pass | 2 | 956 | 54 | 1.2s | solved | [`ministral-8b-2512__mbpp-135.json`](runs/ministral-8b-2512/mbpp_task/ministral-8b-2512__mbpp-135.json) |
| ministral-8b-2512 | 227 | pass | 2 | 995 | 60 | 1.2s | solved | [`ministral-8b-2512__mbpp-227.json`](runs/ministral-8b-2512/mbpp_task/ministral-8b-2512__mbpp-227.json) |
| ministral-8b-2512 | 257 | pass | 2 | 981 | 48 | 1.1s | solved | [`ministral-8b-2512__mbpp-257.json`](runs/ministral-8b-2512/mbpp_task/ministral-8b-2512__mbpp-257.json) |
| ministral-8b-2512 | 285 | pass | 4 | 2,893 | 414 | 4.8s | solved | [`ministral-8b-2512__mbpp-285.json`](runs/ministral-8b-2512/mbpp_task/ministral-8b-2512__mbpp-285.json) |
| ministral-8b-2512 | 390 | pass | 2 | 1,079 | 60 | 1.4s | solved | [`ministral-8b-2512__mbpp-390.json`](runs/ministral-8b-2512/mbpp_task/ministral-8b-2512__mbpp-390.json) |
| ministral-8b-2512 | 418 | pass | 2 | 1,062 | 98 | 1.4s | solved | [`ministral-8b-2512__mbpp-418.json`](runs/ministral-8b-2512/mbpp_task/ministral-8b-2512__mbpp-418.json) |
| ministral-8b-2512 | 444 | pass | 3 | 2,775 | 550 | 5.6s | solved | [`ministral-8b-2512__mbpp-444.json`](runs/ministral-8b-2512/mbpp_task/ministral-8b-2512__mbpp-444.json) |
| ministral-8b-2512 | 75 | pass | 2 | 1,159 | 84 | 1.4s | solved | [`ministral-8b-2512__mbpp-75.json`](runs/ministral-8b-2512/mbpp_task/ministral-8b-2512__mbpp-75.json) |
| nex-agi/nex-n2.5-mini:free | 103 | pass | 3 | 4,196 | 1,094 | 14.4s | solved | [`nex-agi-nex-n2.5-mini:free__mbpp-103.json`](runs/nex-agi-nex-n2.5-mini:free/mbpp_task/nex-agi-nex-n2.5-mini:free__mbpp-103.json) |
| nex-agi/nex-n2.5-mini:free | 11 | pass | 2 | 1,260 | 437 | 8.5s | solved | [`nex-agi-nex-n2.5-mini:free__mbpp-11.json`](runs/nex-agi-nex-n2.5-mini:free/mbpp_task/nex-agi-nex-n2.5-mini:free__mbpp-11.json) |
| nex-agi/nex-n2.5-mini:free | 135 | pass | 2 | 1,582 | 186 | 6.7s | solved | [`nex-agi-nex-n2.5-mini:free__mbpp-135.json`](runs/nex-agi-nex-n2.5-mini:free/mbpp_task/nex-agi-nex-n2.5-mini:free__mbpp-135.json) |
| nex-agi/nex-n2.5-mini:free | 227 | pass | 2 | 1,990 | 488 | 8.7s | solved | [`nex-agi-nex-n2.5-mini:free__mbpp-227.json`](runs/nex-agi-nex-n2.5-mini:free/mbpp_task/nex-agi-nex-n2.5-mini:free__mbpp-227.json) |
| nex-agi/nex-n2.5-mini:free | 257 | pass | 2 | 1,519 | 825 | 11.7s | solved | [`nex-agi-nex-n2.5-mini:free__mbpp-257.json`](runs/nex-agi-nex-n2.5-mini:free/mbpp_task/nex-agi-nex-n2.5-mini:free__mbpp-257.json) |
| nex-agi/nex-n2.5-mini:free | 285 | fail | 1 | 885 | 752 | 10.2s | Output token limit reached | [`nex-agi-nex-n2.5-mini:free__mbpp-285.json`](runs/nex-agi-nex-n2.5-mini:free/mbpp_task/nex-agi-nex-n2.5-mini:free__mbpp-285.json) |
| nex-agi/nex-n2.5-mini:free | 390 | pass | 2 | 2,074 | 300 | 7.5s | solved | [`nex-agi-nex-n2.5-mini:free__mbpp-390.json`](runs/nex-agi-nex-n2.5-mini:free/mbpp_task/nex-agi-nex-n2.5-mini:free__mbpp-390.json) |
| nex-agi/nex-n2.5-mini:free | 418 | pass | 2 | 2,124 | 403 | 8.8s | solved | [`nex-agi-nex-n2.5-mini:free__mbpp-418.json`](runs/nex-agi-nex-n2.5-mini:free/mbpp_task/nex-agi-nex-n2.5-mini:free__mbpp-418.json) |
| nex-agi/nex-n2.5-mini:free | 444 | pass | 3 | 4,790 | 372 | 8.8s | solved | [`nex-agi-nex-n2.5-mini:free__mbpp-444.json`](runs/nex-agi-nex-n2.5-mini:free/mbpp_task/nex-agi-nex-n2.5-mini:free__mbpp-444.json) |
| nex-agi/nex-n2.5-mini:free | 75 | pass | 2 | 2,237 | 414 | 8.3s | solved | [`nex-agi-nex-n2.5-mini:free__mbpp-75.json`](runs/nex-agi-nex-n2.5-mini:free/mbpp_task/nex-agi-nex-n2.5-mini:free__mbpp-75.json) |
| openai/gpt-oss-120b | 103 | fail | 3 | 3,046 | 1,135 | 3.5s | Output token limit reached | [`openai-gpt-oss-120b__mbpp-103.json`](runs/openai-gpt-oss-120b/mbpp_task/openai-gpt-oss-120b__mbpp-103.json) |
| openai/gpt-oss-120b | 11 | pass | 2 | 1,440 | 453 | 2.5s | solved | [`openai-gpt-oss-120b__mbpp-11.json`](runs/openai-gpt-oss-120b/mbpp_task/openai-gpt-oss-120b__mbpp-11.json) |
| openai/gpt-oss-120b | 135 | pass | 2 | 1,187 | 157 | 1.1s | solved | [`openai-gpt-oss-120b__mbpp-135.json`](runs/openai-gpt-oss-120b/mbpp_task/openai-gpt-oss-120b__mbpp-135.json) |
| openai/gpt-oss-120b | 227 | pass | 2 | 1,168 | 133 | 1.0s | solved | [`openai-gpt-oss-120b__mbpp-227.json`](runs/openai-gpt-oss-120b/mbpp_task/openai-gpt-oss-120b__mbpp-227.json) |
| openai/gpt-oss-120b | 257 | pass | 2 | 1,133 | 83 | 1.8s | solved | [`openai-gpt-oss-120b__mbpp-257.json`](runs/openai-gpt-oss-120b/mbpp_task/openai-gpt-oss-120b__mbpp-257.json) |
| openai/gpt-oss-120b | 285 | pass | 2 | 1,336 | 273 | 2.2s | solved | [`openai-gpt-oss-120b__mbpp-285.json`](runs/openai-gpt-oss-120b/mbpp_task/openai-gpt-oss-120b__mbpp-285.json) |
| openai/gpt-oss-120b | 390 | pass | 1 | 582 | 201 | 2.9s | solved | [`openai-gpt-oss-120b__mbpp-390.json`](runs/openai-gpt-oss-120b/mbpp_task/openai-gpt-oss-120b__mbpp-390.json) |
| openai/gpt-oss-120b | 418 | pass | 2 | 1,294 | 197 | 2.1s | solved | [`openai-gpt-oss-120b__mbpp-418.json`](runs/openai-gpt-oss-120b/mbpp_task/openai-gpt-oss-120b__mbpp-418.json) |
| openai/gpt-oss-120b | 444 | pass | 2 | 1,872 | 488 | 2.4s | solved | [`openai-gpt-oss-120b__mbpp-444.json`](runs/openai-gpt-oss-120b/mbpp_task/openai-gpt-oss-120b__mbpp-444.json) |
| openai/gpt-oss-120b | 75 | pass | 2 | 1,427 | 261 | 1.9s | solved | [`openai-gpt-oss-120b__mbpp-75.json`](runs/openai-gpt-oss-120b/mbpp_task/openai-gpt-oss-120b__mbpp-75.json) |
| poolside/laguna-s-2.1:free | 103 | fail | 1 | 503 | 834 | 22.8s | Output token limit reached | [`poolside-laguna-s-2.1:free__mbpp-103.json`](runs/poolside-laguna-s-2.1:free/mbpp_task/poolside-laguna-s-2.1:free__mbpp-103.json) |
| poolside/laguna-s-2.1:free | 11 | pass | 2 | 1,543 | 626 | 29.3s | solved | [`poolside-laguna-s-2.1:free__mbpp-11.json`](runs/poolside-laguna-s-2.1:free/mbpp_task/poolside-laguna-s-2.1:free__mbpp-11.json) |
| poolside/laguna-s-2.1:free | 135 | pass | 2 | 1,128 | 165 | 11.8s | solved | [`poolside-laguna-s-2.1:free__mbpp-135.json`](runs/poolside-laguna-s-2.1:free/mbpp_task/poolside-laguna-s-2.1:free__mbpp-135.json) |
| poolside/laguna-s-2.1:free | 227 | pass | 2 | 1,103 | 121 | 14.7s | solved | [`poolside-laguna-s-2.1:free__mbpp-227.json`](runs/poolside-laguna-s-2.1:free/mbpp_task/poolside-laguna-s-2.1:free__mbpp-227.json) |
| poolside/laguna-s-2.1:free | 257 | pass | 2 | 1,142 | 153 | 19.4s | solved | [`poolside-laguna-s-2.1:free__mbpp-257.json`](runs/poolside-laguna-s-2.1:free/mbpp_task/poolside-laguna-s-2.1:free__mbpp-257.json) |
| poolside/laguna-s-2.1:free | 285 | pass | 2 | 1,456 | 482 | 17.0s | solved | [`poolside-laguna-s-2.1:free__mbpp-285.json`](runs/poolside-laguna-s-2.1:free/mbpp_task/poolside-laguna-s-2.1:free__mbpp-285.json) |
| poolside/laguna-s-2.1:free | 390 | pass | 2 | 1,427 | 371 | 15.0s | solved | [`poolside-laguna-s-2.1:free__mbpp-390.json`](runs/poolside-laguna-s-2.1:free/mbpp_task/poolside-laguna-s-2.1:free__mbpp-390.json) |
| poolside/laguna-s-2.1:free | 418 | pass | 2 | 1,364 | 321 | 21.6s | solved | [`poolside-laguna-s-2.1:free__mbpp-418.json`](runs/poolside-laguna-s-2.1:free/mbpp_task/poolside-laguna-s-2.1:free__mbpp-418.json) |
| poolside/laguna-s-2.1:free | 444 | pass | 2 | 1,749 | 449 | 30.3s | solved | [`poolside-laguna-s-2.1:free__mbpp-444.json`](runs/poolside-laguna-s-2.1:free/mbpp_task/poolside-laguna-s-2.1:free__mbpp-444.json) |
| poolside/laguna-s-2.1:free | 75 | pass | 2 | 1,251 | 105 | 21.4s | solved | [`poolside-laguna-s-2.1:free__mbpp-75.json`](runs/poolside-laguna-s-2.1:free/mbpp_task/poolside-laguna-s-2.1:free__mbpp-75.json) |
| qwen/qwen3.8-27b | 103 | pass | 2 | 1,338 | 472 | 1.5s | solved | [`qwen-qwen3.8-27b__mbpp-103.json`](runs/qwen-qwen3.8-27b/mbpp_task/qwen-qwen3.8-27b__mbpp-103.json) |
| qwen/qwen3.8-27b | 11 | pass | 2 | 1,175 | 223 | 1.7s | solved | [`qwen-qwen3.8-27b__mbpp-11.json`](runs/qwen-qwen3.8-27b/mbpp_task/qwen-qwen3.8-27b__mbpp-11.json) |
| qwen/qwen3.8-27b | 135 | pass | 2 | 1,048 | 63 | 0.6s | solved | [`qwen-qwen3.8-27b__mbpp-135.json`](runs/qwen-qwen3.8-27b/mbpp_task/qwen-qwen3.8-27b__mbpp-135.json) |
| qwen/qwen3.8-27b | 227 | pass | 2 | 1,073 | 65 | 0.6s | solved | [`qwen-qwen3.8-27b__mbpp-227.json`](runs/qwen-qwen3.8-27b/mbpp_task/qwen-qwen3.8-27b__mbpp-227.json) |
| qwen/qwen3.8-27b | 257 | pass | 2 | 1,068 | 51 | 0.7s | solved | [`qwen-qwen3.8-27b__mbpp-257.json`](runs/qwen-qwen3.8-27b/mbpp_task/qwen-qwen3.8-27b__mbpp-257.json) |
| qwen/qwen3.8-27b | 285 | pass | 2 | 1,077 | 77 | 0.6s | solved | [`qwen-qwen3.8-27b__mbpp-285.json`](runs/qwen-qwen3.8-27b/mbpp_task/qwen-qwen3.8-27b__mbpp-285.json) |
| qwen/qwen3.8-27b | 390 | pass | 2 | 1,159 | 65 | 0.5s | solved | [`qwen-qwen3.8-27b__mbpp-390.json`](runs/qwen-qwen3.8-27b/mbpp_task/qwen-qwen3.8-27b__mbpp-390.json) |
| qwen/qwen3.8-27b | 418 | pass | 2 | 1,111 | 53 | 0.7s | solved | [`qwen-qwen3.8-27b__mbpp-418.json`](runs/qwen-qwen3.8-27b/mbpp_task/qwen-qwen3.8-27b__mbpp-418.json) |
| qwen/qwen3.8-27b | 444 | pass | 2 | 1,404 | 87 | 8.8s | solved | [`qwen-qwen3.8-27b__mbpp-444.json`](runs/qwen-qwen3.8-27b/mbpp_task/qwen-qwen3.8-27b__mbpp-444.json) |
| qwen/qwen3.8-27b | 75 | pass | 2 | 1,230 | 87 | 9.7s | solved | [`qwen-qwen3.8-27b__mbpp-75.json`](runs/qwen-qwen3.8-27b/mbpp_task/qwen-qwen3.8-27b__mbpp-75.json) |
| qwen/qwen3.8-27b:free | 103 | fail | 1 | 539 | 960 | 40.8s | Output token limit reached | [`qwen-qwen3.8-27b:free__mbpp-103.json`](runs/qwen-qwen3.8-27b:free/mbpp_task/qwen-qwen3.8-27b:free__mbpp-103.json) |
| qwen/qwen3.8-27b:free | 11 | pass | 2 | 1,448 | 564 | 25.6s | solved | [`qwen-qwen3.8-27b:free__mbpp-11.json`](runs/qwen-qwen3.8-27b:free/mbpp_task/qwen-qwen3.8-27b:free__mbpp-11.json) |
| qwen/qwen3.8-27b:free | 135 | pass | 2 | 1,253 | 236 | 9.1s | solved | [`qwen-qwen3.8-27b:free__mbpp-135.json`](runs/qwen-qwen3.8-27b:free/mbpp_task/qwen-qwen3.8-27b:free__mbpp-135.json) |
| qwen/qwen3.8-27b:free | 227 | pass | 2 | 1,224 | 171 | 8.8s | solved | [`qwen-qwen3.8-27b:free__mbpp-227.json`](runs/qwen-qwen3.8-27b:free/mbpp_task/qwen-qwen3.8-27b:free__mbpp-227.json) |
| qwen/qwen3.8-27b:free | 257 | pass | 2 | 1,197 | 204 | 14.0s | solved | [`qwen-qwen3.8-27b:free__mbpp-257.json`](runs/qwen-qwen3.8-27b:free/mbpp_task/qwen-qwen3.8-27b:free__mbpp-257.json) |
| qwen/qwen3.8-27b:free | 285 | pass | 2 | 1,639 | 640 | 18.2s | solved | [`qwen-qwen3.8-27b:free__mbpp-285.json`](runs/qwen-qwen3.8-27b:free/mbpp_task/qwen-qwen3.8-27b:free__mbpp-285.json) |
| qwen/qwen3.8-27b:free | 390 | pass | 2 | 1,780 | 766 | 21.3s | solved | [`qwen-qwen3.8-27b:free__mbpp-390.json`](runs/qwen-qwen3.8-27b:free/mbpp_task/qwen-qwen3.8-27b:free__mbpp-390.json) |
| qwen/qwen3.8-27b:free | 418 | pass | 2 | 1,532 | 585 | 21.4s | solved | [`qwen-qwen3.8-27b:free__mbpp-418.json`](runs/qwen-qwen3.8-27b:free/mbpp_task/qwen-qwen3.8-27b:free__mbpp-418.json) |
| qwen/qwen3.8-27b:free | 444 | fail | 1 | 701 | 1,303 | 47.3s | Output token limit reached | [`qwen-qwen3.8-27b:free__mbpp-444.json`](runs/qwen-qwen3.8-27b:free/mbpp_task/qwen-qwen3.8-27b:free__mbpp-444.json) |
| qwen/qwen3.8-27b:free | 75 | pass | 2 | 1,577 | 458 | 22.6s | solved | [`qwen-qwen3.8-27b:free__mbpp-75.json`](runs/qwen-qwen3.8-27b:free/mbpp_task/qwen-qwen3.8-27b:free__mbpp-75.json) |
| stealth/space-bunny-alpha | 103 | fail | 2 | 1,572 | 940 | 10.9s | Output token limit reached | [`stealth-space-bunny-alpha__mbpp-103.json`](runs/stealth-space-bunny-alpha/mbpp_task/stealth-space-bunny-alpha__mbpp-103.json) |
| stealth/space-bunny-alpha | 11 | pass | 2 | 1,437 | 320 | 5.7s | solved | [`stealth-space-bunny-alpha__mbpp-11.json`](runs/stealth-space-bunny-alpha/mbpp_task/stealth-space-bunny-alpha__mbpp-11.json) |
| stealth/space-bunny-alpha | 135 | pass | 2 | 1,314 | 192 | 5.1s | solved | [`stealth-space-bunny-alpha__mbpp-135.json`](runs/stealth-space-bunny-alpha/mbpp_task/stealth-space-bunny-alpha__mbpp-135.json) |
| stealth/space-bunny-alpha | 227 | pass | 2 | 1,274 | 172 | 4.2s | solved | [`stealth-space-bunny-alpha__mbpp-227.json`](runs/stealth-space-bunny-alpha/mbpp_task/stealth-space-bunny-alpha__mbpp-227.json) |
| stealth/space-bunny-alpha | 257 | pass | 2 | 1,251 | 79 | 4.1s | solved | [`stealth-space-bunny-alpha__mbpp-257.json`](runs/stealth-space-bunny-alpha/mbpp_task/stealth-space-bunny-alpha__mbpp-257.json) |
| stealth/space-bunny-alpha | 285 | pass | 2 | 1,416 | 383 | 6.9s | solved | [`stealth-space-bunny-alpha__mbpp-285.json`](runs/stealth-space-bunny-alpha/mbpp_task/stealth-space-bunny-alpha__mbpp-285.json) |
| stealth/space-bunny-alpha | 390 | pass | 2 | 1,442 | 166 | 4.9s | solved | [`stealth-space-bunny-alpha__mbpp-390.json`](runs/stealth-space-bunny-alpha/mbpp_task/stealth-space-bunny-alpha__mbpp-390.json) |
| stealth/space-bunny-alpha | 418 | pass | 2 | 1,371 | 115 | 3.5s | solved | [`stealth-space-bunny-alpha__mbpp-418.json`](runs/stealth-space-bunny-alpha/mbpp_task/stealth-space-bunny-alpha__mbpp-418.json) |
| stealth/space-bunny-alpha | 444 | pass | 2 | 1,775 | 275 | 5.7s | solved | [`stealth-space-bunny-alpha__mbpp-444.json`](runs/stealth-space-bunny-alpha/mbpp_task/stealth-space-bunny-alpha__mbpp-444.json) |
| stealth/space-bunny-alpha | 75 | pass | 2 | 1,464 | 152 | 4.6s | solved | [`stealth-space-bunny-alpha__mbpp-75.json`](runs/stealth-space-bunny-alpha/mbpp_task/stealth-space-bunny-alpha__mbpp-75.json) |
| z-ai/glm-5.2:free | 103 | pass | 2 | 1,567 | 766 | 38.8s | solved | [`z-ai-glm-5.2:free__mbpp-103.json`](runs/z-ai-glm-5.2:free/mbpp_task/z-ai-glm-5.2:free__mbpp-103.json) |
| z-ai/glm-5.2:free | 11 | pass | 2 | 1,516 | 622 | 116.0s | solved | [`z-ai-glm-5.2:free__mbpp-11.json`](runs/z-ai-glm-5.2:free/mbpp_task/z-ai-glm-5.2:free__mbpp-11.json) |
| z-ai/glm-5.2:free | 135 | pass | 2 | 993 | 72 | 40.2s | solved | [`z-ai-glm-5.2:free__mbpp-135.json`](runs/z-ai-glm-5.2:free/mbpp_task/z-ai-glm-5.2:free__mbpp-135.json) |
| z-ai/glm-5.2:free | 227 | pass | 2 | 1,042 | 110 | 29.4s | solved | [`z-ai-glm-5.2:free__mbpp-227.json`](runs/z-ai-glm-5.2:free/mbpp_task/z-ai-glm-5.2:free__mbpp-227.json) |
| z-ai/glm-5.2:free | 257 | pass | 2 | 1,042 | 136 | 46.4s | solved | [`z-ai-glm-5.2:free__mbpp-257.json`](runs/z-ai-glm-5.2:free/mbpp_task/z-ai-glm-5.2:free__mbpp-257.json) |
| z-ai/glm-5.2:free | 285 | pass | 2 | 1,307 | 394 | 34.2s | solved | [`z-ai-glm-5.2:free__mbpp-285.json`](runs/z-ai-glm-5.2:free/mbpp_task/z-ai-glm-5.2:free__mbpp-285.json) |
| z-ai/glm-5.2:free | 390 | pass | 2 | 1,245 | 216 | 36.4s | solved | [`z-ai-glm-5.2:free__mbpp-390.json`](runs/z-ai-glm-5.2:free/mbpp_task/z-ai-glm-5.2:free__mbpp-390.json) |
| z-ai/glm-5.2:free | 418 | pass | 2 | 1,072 | 78 | 46.7s | solved | [`z-ai-glm-5.2:free__mbpp-418.json`](runs/z-ai-glm-5.2:free/mbpp_task/z-ai-glm-5.2:free__mbpp-418.json) |
| z-ai/glm-5.2:free | 444 | pass | 2 | 1,420 | 185 | 31.5s | solved | [`z-ai-glm-5.2:free__mbpp-444.json`](runs/z-ai-glm-5.2:free/mbpp_task/z-ai-glm-5.2:free__mbpp-444.json) |
| z-ai/glm-5.2:free | 75 | pass | 2 | 1,177 | 118 | 30.8s | solved | [`z-ai-glm-5.2:free__mbpp-75.json`](runs/z-ai-glm-5.2:free/mbpp_task/z-ai-glm-5.2:free__mbpp-75.json) |

</details>

## Intermediary metrics

> SWE-bench only: these metrics read a unified diff and a test suite, which an MBPP cell has neither of. An em dash means the run does not contain what the metric needs — a task solved without ever running the suite has no green step to report.

<details>
<summary>Per SWE-bench cell</summary>

| Model | Task | Patched file first read/edited | Suite first green | Iterations from green to answer | Failures first dropped |
|---|---|---:|---:|---:|---:|
| Prism-ML/Ternary-Bonsai-27B | django__django-11066 | step 2 | step 6 | 1 | — |
| Prism-ML/Ternary-Bonsai-27B | django__django-17029 | step 2 | step 6 | 1 | — |
| Prism-ML/Ternary-Bonsai-27B | pydata__xarray-4629 | — | — | — | — |
| Prism-ML/Ternary-Bonsai-27B | scikit-learn__scikit-learn-13439 | — | — | — | — |
| Prism-ML/Ternary-Bonsai-27B | sympy__sympy-13480 | step 1 | — | — | — |
| Prism-ML/Ternary-Bonsai-27B | sympy__sympy-14711 | — | — | — | — |
| Prism-ML/Ternary-Bonsai-27B | sympy__sympy-18189 | step 2 | — | — | — |
| codestral-2508 | django__django-11066 | step 4 | step 6 | 1 | — |
| codestral-2508 | django__django-17029 | — | — | — | — |
| codestral-2508 | pydata__xarray-4629 | step 4 | — | — | — |
| codestral-2508 | scikit-learn__scikit-learn-13439 | — | — | — | — |
| codestral-2508 | sympy__sympy-13480 | — | — | — | — |
| codestral-2508 | sympy__sympy-14711 | — | — | — | — |
| codestral-2508 | sympy__sympy-18189 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | django__django-11066 | step 3 | step 7 | 1 | — |
| dots-studio/dots-3-note-preview:free | django__django-17029 | step 2 | step 9 | 1 | — |
| dots-studio/dots-3-note-preview:free | pydata__xarray-4629 | step 3 | — | — | — |
| dots-studio/dots-3-note-preview:free | scikit-learn__scikit-learn-13439 | step 2 | — | — | — |
| dots-studio/dots-3-note-preview:free | sympy__sympy-13480 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | sympy__sympy-14711 | — | — | — | — |
| dots-studio/dots-3-note-preview:free | sympy__sympy-18189 | — | — | — | — |
| google/gemma-4-31b-it:free | django__django-11066 | step 2 | step 4 | 1 | — |
| google/gemma-4-31b-it:free | django__django-17029 | — | — | — | — |
| google/gemma-4-31b-it:free | pydata__xarray-4629 | — | — | — | — |
| google/gemma-4-31b-it:free | scikit-learn__scikit-learn-13439 | — | — | — | — |
| google/gemma-4-31b-it:free | sympy__sympy-13480 | step 2 | — | — | — |
| google/gemma-4-31b-it:free | sympy__sympy-14711 | — | — | — | — |
| google/gemma-4-31b-it:free | sympy__sympy-18189 | step 2 | — | — | — |
| ministral-14b-2512 | django__django-11066 | step 4 | step 6 | 1 | — |
| ministral-14b-2512 | django__django-17029 | step 2 | step 6 | 1 | — |
| ministral-14b-2512 | pydata__xarray-4629 | step 2 | — | — | — |
| ministral-14b-2512 | scikit-learn__scikit-learn-13439 | step 2 | — | — | — |
| ministral-14b-2512 | sympy__sympy-13480 | step 1 | — | — | — |
| ministral-14b-2512 | sympy__sympy-14711 | step 2 | — | — | — |
| ministral-14b-2512 | sympy__sympy-18189 | step 2 | — | — | — |
| ministral-3b-2512 | django__django-11066 | step 4 | — | — | — |
| ministral-3b-2512 | django__django-17029 | step 4 | step 25 | 1 | — |
| ministral-3b-2512 | pydata__xarray-4629 | step 4 | — | — | — |
| ministral-3b-2512 | scikit-learn__scikit-learn-13439 | — | — | — | — |
| ministral-3b-2512 | sympy__sympy-13480 | — | — | — | — |
| ministral-3b-2512 | sympy__sympy-14711 | — | — | — | — |
| ministral-3b-2512 | sympy__sympy-18189 | — | — | — | — |
| ministral-8b-2512 | django__django-11066 | step 3 | step 5 | 1 | — |
| ministral-8b-2512 | django__django-17029 | step 2 | step 6 | 1 | — |
| ministral-8b-2512 | pydata__xarray-4629 | step 2 | — | — | — |
| ministral-8b-2512 | scikit-learn__scikit-learn-13439 | step 2 | — | — | — |
| ministral-8b-2512 | sympy__sympy-13480 | step 1 | — | — | — |
| ministral-8b-2512 | sympy__sympy-14711 | — | — | — | — |
| ministral-8b-2512 | sympy__sympy-18189 | step 2 | — | — | — |
| nex-agi/nex-n2.5-mini:free | django__django-11066 | — | step 28 | 2 | — |
| nex-agi/nex-n2.5-mini:free | django__django-17029 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | pydata__xarray-4629 | step 3 | — | — | — |
| nex-agi/nex-n2.5-mini:free | scikit-learn__scikit-learn-13439 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | sympy__sympy-13480 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | sympy__sympy-14711 | — | — | — | — |
| nex-agi/nex-n2.5-mini:free | sympy__sympy-18189 | — | — | — | — |
| openai/gpt-oss-120b | django__django-11066 | — | — | — | — |
| openai/gpt-oss-120b | django__django-17029 | — | — | — | — |
| openai/gpt-oss-120b | pydata__xarray-4629 | step 1 | — | — | — |
| openai/gpt-oss-120b | scikit-learn__scikit-learn-13439 | — | — | — | — |
| openai/gpt-oss-120b | sympy__sympy-13480 | — | — | — | — |
| openai/gpt-oss-120b | sympy__sympy-14711 | — | — | — | — |
| openai/gpt-oss-120b | sympy__sympy-18189 | — | — | — | — |
| poolside/laguna-s-2.1:free | django__django-11066 | — | — | — | — |
| poolside/laguna-s-2.1:free | django__django-17029 | — | — | — | — |
| poolside/laguna-s-2.1:free | pydata__xarray-4629 | step 1 | — | — | — |
| poolside/laguna-s-2.1:free | scikit-learn__scikit-learn-13439 | — | — | — | — |
| poolside/laguna-s-2.1:free | sympy__sympy-13480 | step 1 | — | — | — |
| poolside/laguna-s-2.1:free | sympy__sympy-14711 | — | — | — | — |
| poolside/laguna-s-2.1:free | sympy__sympy-18189 | — | — | — | — |
| qwen/qwen3.8-27b | django__django-11066 | step 1 | step 3 | 1 | — |
| qwen/qwen3.8-27b | django__django-17029 | step 2 | step 6 | 1 | — |
| qwen/qwen3.8-27b | pydata__xarray-4629 | — | — | — | — |
| qwen/qwen3.8-27b | scikit-learn__scikit-learn-13439 | — | — | — | — |
| qwen/qwen3.8-27b | sympy__sympy-13480 | — | — | — | — |
| qwen/qwen3.8-27b | sympy__sympy-14711 | — | — | — | — |
| qwen/qwen3.8-27b | sympy__sympy-18189 | — | — | — | — |
| qwen/qwen3.8-27b:free | django__django-11066 | step 4 | step 7 | 1 | — |
| qwen/qwen3.8-27b:free | django__django-17029 | step 2 | step 7 | 1 | — |
| qwen/qwen3.8-27b:free | pydata__xarray-4629 | — | — | — | — |
| qwen/qwen3.8-27b:free | scikit-learn__scikit-learn-13439 | — | — | — | — |
| qwen/qwen3.8-27b:free | sympy__sympy-13480 | — | — | — | — |
| qwen/qwen3.8-27b:free | sympy__sympy-14711 | — | — | — | — |
| qwen/qwen3.8-27b:free | sympy__sympy-18189 | step 1 | — | — | — |
| stealth/space-bunny-alpha | django__django-11066 | step 2 | step 12 | 1 | — |
| stealth/space-bunny-alpha | django__django-17029 | — | — | — | — |
| stealth/space-bunny-alpha | pydata__xarray-4629 | step 3 | — | — | — |
| stealth/space-bunny-alpha | scikit-learn__scikit-learn-13439 | — | — | — | — |
| stealth/space-bunny-alpha | sympy__sympy-13480 | step 2 | — | — | — |
| stealth/space-bunny-alpha | sympy__sympy-14711 | — | — | — | — |
| stealth/space-bunny-alpha | sympy__sympy-18189 | step 2 | — | — | — |
| z-ai/glm-5.2:free | django__django-11066 | step 1 | step 3 | 1 | — |
| z-ai/glm-5.2:free | django__django-17029 | — | — | — | — |
| z-ai/glm-5.2:free | pydata__xarray-4629 | step 1 | — | — | — |
| z-ai/glm-5.2:free | scikit-learn__scikit-learn-13439 | — | — | — | — |
| z-ai/glm-5.2:free | sympy__sympy-13480 | — | — | — | — |
| z-ai/glm-5.2:free | sympy__sympy-14711 | — | — | — | — |
| z-ai/glm-5.2:free | sympy__sympy-18189 | — | — | — | — |

</details>

## Ablation

`ministral-14b-2512` on the 7 SWE-bench tasks, 3 runs each, variants interleaved, temperature 0. Each variant removes one component, and every run is judged by the moulinette.

| Variant | Changed | Resolved | 95 % CI | p (Holm) | Δ iterations [95 % CI] | Δ tokens [95 % CI] |
|---|---|---:|---|---:|---:|---:|
| baseline | nothing — the agent as shipped | 16/21 | 55% – 89% |  |  |  |
| no-reasoning-guide | no `REASONING_GUIDE` in the system prompt | 6/21 | 14% – 50% | 0.014 | +16.0 [+7.0, +22.7] | -57,837 [-103,956, +26,644] |
| fewer-tools | `find_references`, `list_files`, `run_command` hidden | 19/21 | 71% – 97% | 0.820 | +0.0 [+0.0, +1.7] | +6,333 [-315, +42,943] |
| no-hints | no `hints_text` in the task prompt | 16/21 | 55% – 89% | 1.000 | -0.3 [-6.7, +4.7] | -1,217 [-4,964, +41,839] |

- **Resolved**: runs the moulinette validated, out of 7 tasks × 3 runs.
- **95 % CI**: where the true pass rate lies, with 95 % confidence (Wilson interval). Widely overlapping intervals mean the data cannot tell two variants apart. With k passes out of n runs, $\hat p = k/n$ and $z = 1.96$:

  $$\frac{\hat p + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat p(1-\hat p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$

- **p (Holm)**: the chance of a gap at least this large if removing the component changed nothing (Fisher's exact test), corrected for making 3 comparisons at once (Holm). Below 0.05, the difference is significant. Fisher keeps the totals fixed (N runs, K passes, $n_b$ of the runs in the baseline) and adds up the probability of every split at most as likely as the one observed, $k_b$ baseline passes:

  $$P(x) = \frac{\binom{K}{x}\binom{N-K}{n_b-x}}{\binom{N}{n_b}} \qquad p = \sum_{P(x) \le P(k_b)} P(x)$$

  Holm then sorts the m p-values, $p_{(1)} \le \dots \le p_{(m)}$, and scales each by the tests still left:

  $$\tilde p_{(i)} = \max_{j \le i} \min\bigl(1,\ (m - j + 1)\, p_{(j)}\bigr)$$

- **Δ iterations, Δ tokens**: median per-task change against the baseline, positive when the variant costs more, with its 95 % bootstrap interval (10,000 resamples of the tasks). An interval that excludes 0 is a real change.

- **no-reasoning-guide changes the outcome**: 6/21 against 16/21 (p = 0.014), +16 iterations at the median.
- **fewer-tools: no effect detected** (19/21, p = 0.82).
- **no-hints: no effect detected** (16/21, p = 1.00).

The baseline itself splits on 3 of 7 tasks across its repetitions, which is why only a large effect shows at this scale: *no effect detected* is not *no effect*.

<details>
<summary>Resolved per task and variant</summary>

| Task | baseline | no-reasoning-guide | fewer-tools | no-hints |
|---|---:|---:|---:|---:|
| django__django-11066 | 3/3 | 0/3 | 3/3 | 3/3 |
| django__django-17029 | 3/3 | 0/3 | 3/3 | 3/3 |
| pydata__xarray-4629 | 3/3 | 2/3 | 3/3 | 3/3 |
| scikit-learn__scikit-learn-13439 | 1/3 | 0/3 | 2/3 | 3/3 |
| sympy__sympy-13480 | 3/3 | 1/3 | 3/3 | 2/3 |
| sympy__sympy-14711 | 2/3 | 0/3 | 3/3 | 2/3 |
| sympy__sympy-18189 | 1/3 | 3/3 | 2/3 | 0/3 |

</details>

## Conclusions

- **Selected: `ministral-8b-2512`** (15/17), with `ministral-14b-2512` for SWE-bench (7/7) — the best scores, on a provider with no cell lost. They are the agent's defaults.
- **Disregarded**: below the median, `google/gemma-4-31b-it:free` (9/17), `codestral-2508` (9/17), `ministral-3b-2512` (9/17), `Prism-ML/Ternary-Bonsai-27B` (5/17); and the 3 models no longer served.
- **`success` is not a verdict**: 39 resolutions claimed on SWE-bench, 37 confirmed by the moulinette.
- **What the agent needs** (ablation): the reasoning guide — without it, 10 of 21 runs are lost; not the three rarely used tools nor the hints, no effect detected.
- **One run per cell is not a measure**: `ministral-14b-2512` resolved 7/7 SWE-bench tasks in the campaign, 16/21 over three repetitions.
- **Free tiers move**: 3 models left the catalogue in three days. Cells with no data: 1 on Groq Console, 2 on Open Router, none on Mistral Studio, Together.
