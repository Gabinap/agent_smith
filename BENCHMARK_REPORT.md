# Benchmark report

## How to reproduce

- **Commit**: `eea9512` — **Python**: 3.10.19 — **platform**: Linux x86_64
- **Campaign**: 11 catalogued models x (7 SWE-bench + 10 MBPP) tasks, plus 3 that left the catalogue during it — 238 cells in all, run between 2026-09-24T02:05 and 2026-09-27T01:23
- **Verdicts**: 236/238 cells judged by `moulinette_eval validate`; the Result column is its verdict, never the run's own `success` field
- **Models** (provider and key names in `srcs/call_llm/providers.json`, secrets in `.env`): `Prism-ML/Ternary-Bonsai-27B`, `codestral-2508`, `dots-studio/dots-3-note-preview:free`, `google/gemma-4-31b-it:free`, `ministral-14b-2512`, `ministral-3b-2512`, `ministral-8b-2512`, `openai/gpt-oss-120b`, `poolside/laguna-s-2.1:free`, `qwen/qwen3.8-27b:free`, `stealth/space-bunny-alpha`
- **Left the catalogue during the campaign**: `nex-agi/nex-n2.5-mini:free`, `qwen/qwen3.8-27b`, `z-ai/glm-5.2:free`
- **SWE-bench tasks**: `django__django-11066`, `django__django-17029`, `pydata__xarray-4629`, `scikit-learn__scikit-learn-13439`, `sympy__sympy-13480`, `sympy__sympy-14711`, `sympy__sympy-18189`
- **MBPP tasks**: 11, 75, 103, 135, 227, 257, 285, 390, 418, 444 (every 25th id of the sorted test split)

Budgets the agents enforce, and the sampling temperature:

| Benchmark | Iterations | Tokens in | Tokens out | Time | Temperature |
|---|---:|---:|---:|---:|---:|
| MBPP | 5 | 6,000 | 1,500 | 100s | 0.0 |
| SWE-bench | 30 | 300,000 | 10,000 | 840s | 0.0 |

```sh
make install                                  # deps and venv
uv run srcs/bench_matrix.py --benchmark mbpp      # 110 cells
uv run srcs/bench_matrix.py --benchmark swebench  #  77 cells
uv run srcs/bench_validate.py                 # moulinette verdicts
make report                                   # this file
```

> Two caveats for anyone re-running this. The free tiers cap daily requests, so a cell can die on a quota rather than on the model — those cells carry an `error` and are counted in *Cells with no data*, not as failures. And temperature 0 is not a guarantee: the same id, same prompt, returned two different answers in three calls on one provider, so counts can move by a cell or two between campaigns.

## Selection rationale

**SWE-bench — 7 tasks.** The moulinette's exam pool (`EXAM_POOL`), which `moulinette_eval select` draws the exam's tasks from and from nowhere else, plus `django__django-17029` outside it, to see the agent on ground the exam cannot serve.

**MBPP — 10 tasks.** MBPP has no exam pool: the exam draws 5 tasks at random from the whole test split (257 tasks, ids 11 to 479). The ten here are every 25th id of that split once sorted — a spread sample rather than a lucky cluster.

**Models — 11, on the free tiers of four providers** (OpenRouter, Mistral, Groq, Together), so that anyone can re-run the campaign at no cost. Chosen for spread rather than for rank: several vendors, a size ladder inside one family (`ministral` 3B, 8B and 14B), and a code-specialised model (`codestral`). Every candidate was first screened on MBPP task 11 and `django__django-11066`, and left out when it could not follow the protocol at all:

- `openai/gpt-oss-20b` answers with native tool calls, which the API rejects since the agent declares no `tools`;
- `allam-2-7b` writes the sandbox's output itself instead of waiting for it;
- models reachable only on a paid plan, or only through an alias of a model already in (`mistral-code-latest` is `codestral`, by the provider's own `aliases` field).

Version ids are pinned wherever the provider offers them (`codestral-2508`, `ministral-*-2512`), so a re-run meets the same weights rather than whatever `-latest` points to that day.

## What the agent is given

The prompt carries the task's `hints_text` — a field of the task input the subject itself defines (*Optional hints about the issue*). It is legitimate input, but not a neutral one: on 3 of the 7 tasks it gives the fix away.

| Task | `hints_text` | What it gives | Resolved |
|---|---:|---|---:|
| django__django-11066 | 2,075 chars | a link to the upstream fix | 7/11 (64 %) |
| django__django-17029 | 44 chars | discussion | 6/11 (55 %) |
| pydata__xarray-4629 | 0 chars | — | 8/11 (73 %) |
| scikit-learn__scikit-learn-13439 | 285 chars | discussion | 3/11 (27 %) |
| sympy__sympy-13480 | 146 chars | the line and the change to make | 6/11 (55 %) |
| sympy__sympy-14711 | 0 chars | — | 1/11 (9 %) |
| sympy__sympy-18189 | 2,027 chars | the fix's own diff | 6/11 (55 %) |

Those 3 tasks resolve at 19/33 (58 %), the other 4 at 18/44 (41 %). The hint helps, without deciding everything: the task resolved most often has no hint at all, and even handed the diff, 5 models of 11 still fail `sympy__sympy-18189`. Scores here are therefore not comparable with SWE-bench's standard setting, which gives the issue alone.

**No run reached outside its task.** Across every SWE-bench step, the agent's code contains no URL fetch, no `curl` or `wget`, no `git fetch` or `pull`; 1 step searched the whole local history — `git log --all …` by `stealth/space-bunny-alpha` on `django__django-11066` — and found nothing, the container holding no commit past the task's base.

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

## Ablation: the sandbox pipe fix

**The change.** The sandbox runs the model's code in a child process and returns the result through a pipe. The parent used to wait for the child to exit before reading, but a child whose result outgrows the pipe's buffer cannot exit until someone reads it: the two waited on each other until the time limit, which then reported a timeout. On a large test log — `run_tests` returns 356,000 characters on `sympy__sympy-13480` — the agent got that timeout instead of its test results. The fix reads before joining.

**Held constant.** Same models, same tasks, same prompts, temperature 0. Between the two series the only other change to the agent is a guard that stops an iteration forecast to overrun the time budget; it concerns the two cells that stopped on *Time limit reached* before. Six of the 23 cells are left out: their re-run produced no data (a model withdrawn from its provider, a token-per-minute cap).

| | Before | After |
|---|---:|---:|
| Cells resolved (of 17) | 11 | 10 |
| Gained / lost | | +3 / −4 |
| Median input tokens | 53,494 | 148,911 |
| Median iterations | 16 | 7 |
| Stopped on the input budget | 0 | 4 |

**What it shows.** Seeing its test results let the agent solve 3 cells it had failed blind. But on sympy, pytest and scikit-learn the agent receives the test log whole: `summarise_tests` only recognises unittest's summary, and otherwise forwards the full output. That log is resent with the conversation on every turn, so the median input tripled and 4 runs that had solved their task now stopped on their input budget — the 4 cells lost. Net, the fix is a wash on this sample, and within the spread temperature 0 already shows between identical calls. The lesson is the next change it points to: test feedback helps only once it is summarised for every runner, which this campaign's code does not yet do.

<details>
<summary>Per cell, with both solution.json files</summary>

| Model | Task | Before | After | Input tokens | Stopped because | Evidence |
|---|---|---|---|---:|---|---|
| codestral-2508 | scikit-learn__scikit-learn-13439 | fail | fail | 166,619 → 130,685 | Iterations limit reached | [before](ablation/pipe_deadlock/before/codestral-2508__scikit-learn__scikit-learn-13439.json) · [after](runs/codestral-2508/codestral-2508__scikit-learn__scikit-learn-13439.json) |
| codestral-2508 | sympy__sympy-13480 | pass | fail | 53,494 → 148,612 | Input token limit reached | [before](ablation/pipe_deadlock/before/codestral-2508__sympy__sympy-13480.json) · [after](runs/codestral-2508/codestral-2508__sympy__sympy-13480.json) |
| codestral-2508 | sympy__sympy-18189 | pass | fail | 55,618 → 186,910 | Input token limit reached | [before](ablation/pipe_deadlock/before/codestral-2508__sympy__sympy-18189.json) · [after](runs/codestral-2508/codestral-2508__sympy__sympy-18189.json) |
| dots-studio-dots-3-note-preview:free | scikit-learn__scikit-learn-13439 | fail | pass | 151,436 → 193,123 | solved | [before](ablation/pipe_deadlock/before/dots-studio-dots-3-note-preview:free__scikit-learn__scikit-learn-13439.json) · [after](runs/dots-studio-dots-3-note-preview:free/dots-studio-dots-3-note-preview:free__scikit-learn__scikit-learn-13439.json) |
| dots-studio-dots-3-note-preview:free | sympy__sympy-13480 | pass | fail | 18,485 → 151,467 | Input token limit reached | [before](ablation/pipe_deadlock/before/dots-studio-dots-3-note-preview:free__sympy__sympy-13480.json) · [after](runs/dots-studio-dots-3-note-preview:free/dots-studio-dots-3-note-preview:free__sympy__sympy-13480.json) |
| dots-studio-dots-3-note-preview:free | sympy__sympy-18189 | pass | fail | 193,802 → 189,785 | Input token limit reached | [before](ablation/pipe_deadlock/before/dots-studio-dots-3-note-preview:free__sympy__sympy-18189.json) · [after](runs/dots-studio-dots-3-note-preview:free/dots-studio-dots-3-note-preview:free__sympy__sympy-18189.json) |
| google-gemma-4-31b-it:free | scikit-learn__scikit-learn-13439 | fail | fail | 50,237 → 9,307 | Empty final answer | [before](ablation/pipe_deadlock/before/google-gemma-4-31b-it:free__scikit-learn__scikit-learn-13439.json) · [after](runs/google-gemma-4-31b-it:free/google-gemma-4-31b-it:free__scikit-learn__scikit-learn-13439.json) |
| ministral-14b-2512 | scikit-learn__scikit-learn-13439 | pass | pass | 42,798 → 285,039 | solved | [before](ablation/pipe_deadlock/before/ministral-14b-2512__scikit-learn__scikit-learn-13439.json) · [after](runs/ministral-14b-2512/ministral-14b-2512__scikit-learn__scikit-learn-13439.json) |
| ministral-14b-2512 | sympy__sympy-13480 | pass | pass | 32,285 → 148,748 | solved | [before](ablation/pipe_deadlock/before/ministral-14b-2512__sympy__sympy-13480.json) · [after](runs/ministral-14b-2512/ministral-14b-2512__sympy__sympy-13480.json) |
| ministral-14b-2512 | sympy__sympy-18189 | pass | pass | 78,723 → 241,718 | solved | [before](ablation/pipe_deadlock/before/ministral-14b-2512__sympy__sympy-18189.json) · [after](runs/ministral-14b-2512/ministral-14b-2512__sympy__sympy-18189.json) |
| ministral-3b-2512 | django__django-17029 | pass | pass | 62,020 → 77,424 | solved | [before](ablation/pipe_deadlock/before/ministral-3b-2512__django__django-17029.json) · [after](runs/ministral-3b-2512/ministral-3b-2512__django__django-17029.json) |
| ministral-3b-2512 | sympy__sympy-13480 | fail | fail | 16,260 → 67,201 | Iterations limit reached | [before](ablation/pipe_deadlock/before/ministral-3b-2512__sympy__sympy-13480.json) · [after](runs/ministral-3b-2512/ministral-3b-2512__sympy__sympy-13480.json) |
| ministral-8b-2512 | pydata__xarray-4629 | pass | pass | 35,346 → 24,554 | solved | [before](ablation/pipe_deadlock/before/ministral-8b-2512__pydata__xarray-4629.json) · [after](runs/ministral-8b-2512/ministral-8b-2512__pydata__xarray-4629.json) |
| ministral-8b-2512 | scikit-learn__scikit-learn-13439 | fail | pass | 122,125 → 172,702 | solved | [before](ablation/pipe_deadlock/before/ministral-8b-2512__scikit-learn__scikit-learn-13439.json) · [after](runs/ministral-8b-2512/ministral-8b-2512__scikit-learn__scikit-learn-13439.json) |
| ministral-8b-2512 | sympy__sympy-13480 | pass | pass | 43,440 → 148,911 | solved | [before](ablation/pipe_deadlock/before/ministral-8b-2512__sympy__sympy-13480.json) · [after](runs/ministral-8b-2512/ministral-8b-2512__sympy__sympy-13480.json) |
| ministral-8b-2512 | sympy__sympy-18189 | pass | pass | 50,336 → 196,326 | solved | [before](ablation/pipe_deadlock/before/ministral-8b-2512__sympy__sympy-18189.json) · [after](runs/ministral-8b-2512/ministral-8b-2512__sympy__sympy-18189.json) |
| nex-agi-nex-n2.5-mini:free | scikit-learn__scikit-learn-13439 | — | — | — | excluded: the re-run produced no data | [before](ablation/pipe_deadlock/before/nex-agi-nex-n2.5-mini:free__scikit-learn__scikit-learn-13439.json) |
| nex-agi-nex-n2.5-mini:free | sympy__sympy-13480 | — | — | — | excluded: the re-run produced no data | [before](ablation/pipe_deadlock/before/nex-agi-nex-n2.5-mini:free__sympy__sympy-13480.json) |
| nex-agi-nex-n2.5-mini:free | sympy__sympy-18189 | — | — | — | excluded: the re-run produced no data | [before](ablation/pipe_deadlock/before/nex-agi-nex-n2.5-mini:free__sympy__sympy-18189.json) |
| openai-gpt-oss-120b | sympy__sympy-13480 | — | — | — | excluded: the re-run produced no data | [before](ablation/pipe_deadlock/before/openai-gpt-oss-120b__sympy__sympy-13480.json) |
| poolside-laguna-s-2.1:free | sympy__sympy-13480 | fail | pass | 153,337 → 140,001 | solved | [before](ablation/pipe_deadlock/before/poolside-laguna-s-2.1:free__sympy__sympy-13480.json) · [after](runs/poolside-laguna-s-2.1:free/poolside-laguna-s-2.1:free__sympy__sympy-13480.json) |
| qwen-qwen3.8-27b | sympy__sympy-13480 | — | — | — | excluded: the re-run produced no data | [before](ablation/pipe_deadlock/before/qwen-qwen3.8-27b__sympy__sympy-13480.json) |
| qwen-qwen3.8-27b | sympy__sympy-18189 | — | — | — | excluded: the re-run produced no data | [before](ablation/pipe_deadlock/before/qwen-qwen3.8-27b__sympy__sympy-18189.json) |

</details>

## Conclusions

- **Best overall: `ministral-8b-2512`**, 15 of 17 cells; best on SWE-bench: `ministral-14b-2512`, 7 of 7. Both are small Mistral models, ahead of `qwen3.8-27b`, `gemma-4-31b-it` and `gpt-oss-120b`; inside the same family the 3B trails well behind, so size matters, but only up to a point.
- **A run's own `success` field is not a verdict.** On SWE-bench it claims 39 resolutions where the moulinette confirms 37: `success` only means the model called `final_answer` with something. Every figure here is the moulinette's verdict.
- **Seeing the tests helps only once the log is summarised.** In the ablation, test results won three cells and cost four, the loss coming from how the log was forwarded rather than from the feedback itself. Tasks solved without the tests ever running were those whose hint gives the fix away — the hint, not the absence of tests, explains them.
- **Free tiers are a moving target.** 3 models left the catalogue within three days of campaign — withdrawn by their provider, or capped below what a SWE-bench task needs. Cells with no data by provider: 1 Groq Console, 2 Open Router; none on Mistral Studio, Together.

**Selection.** For this agent we would run `ministral-8b-2512`, with `ministral-14b-2512` where SWE-bench matters most: the best scores of the campaign, on a provider that left no cell without data and whose limits never bound. Among the free OpenRouter models, the strongest results come with the least dependable access — worth benchmarking, not worth depending on.
