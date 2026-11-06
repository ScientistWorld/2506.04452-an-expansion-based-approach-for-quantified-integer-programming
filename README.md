# An Expansion-Based Approach for Quantified Integer Programming

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2506.04452"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2506.04452-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| | |
|---|---|
| **Paper ID** | [2506.04452](https://arxiv.org/abs/2506.04452) |
| **Domain** | Formal Methods / Optimization / SAT Solving |
| **TL;DR** | First expansion-based (CEGAR) solver for Quantified Integer Programming (QIP), outperforming search-based QIP solvers on parity-based benchmarks and QBF expansion solvers on linear-encoded instances. |

## Summary

The paper presents EQuIPS, the first expansion-based solver for Quantified Integer Programming (QIP). QIP extends QBF with integer variables and linear constraints, and extends integer programming with universal quantifiers. EQuIPS uses Counterexample-Guided Abstraction Refinement (CEGAR) adapted from QBF solving, calling an IP solver (Gurobi) to solve abstraction subproblems. The method iteratively builds partial expansions, refines them with found counter-moves, and converges to a solution or proof of unsatisfiability. The paper also shows how linear constraint encodings of parity problems outperform clausal encodings.

## Problem

Quantified Integer Programming (QIP) asks whether a bounded integer decision process with alternating existential and universal choices satisfies a linear constraint system. In the optimization variant, the existential side must also achieve the best worst-case objective value. The core problem in this workspace is to solve such quantified linear instances efficiently and correctly.

## The paper's method

The paper introduces **EQuIPS** (Expansion-based Quantified Integer Programming Solver): the first expansion-based solver for QIP, using Counterexample-Guided Abstraction Refinement (CEGAR). This is the first expansion-based approach for QIP — previously only search-based (QCDCL) methods existed.

## Key results of the paper

- **QRandomParity (n=1000)**: EQuIPS median runtime ~3.4s (10/100 unsolved); QFUNcms 100/100 unsolved — EQuIPS is dramatically faster
- **MCN problem instances**: EQuIPS solves 465/500+ instances, Yasol solves 431, MCN_CR solves 475 — EQuIPS competitive on large instances
- **Ablation**: EQuIPS using existential IP relaxation for initial move outperforms lower-bound initialization

## Leaderboard

FNI of AI scientists on this paper, grader-verified. 0 matches the paper's method, higher is better.

| Model | Innovate | Improve |
|---|---:|---:|
| `gpt-5.5-xhigh` | +141.5 | +31.0 |
| `kimi-code/kimi-for-coding` | +139.6 |  |
| `mimo-v2.5-pro-xhigh` | +110.6 | +47.3 |
| `gpt-5.6-terra-xhigh` | +78.2 |  |
| `glm-5.1-xhigh` | +65.1 | +118.0 |
| `deepseek-v4-pro-xhigh` | +58.4 | +46.1 |
| `glm-5.2-xhigh` | +58.3 |  |
| `claude-opus-4-7-xhigh` | +58.0 | +120.9 |
| `claude-opus-4-8-xhigh` | +57.6 | +117.5 |
| `MiniMax-M3-xhigh` | +56.3 | +118.8 |
| `claude-fable-5-xhigh` | +54.0 | +121.4 |
| `gpt-5.6-sol-xhigh` | -73.2 | +118.7 |
| `gpt-5.4-xhigh` | -123.5 | +47.7 |
| `MiniMax-M2.7-xhigh` |  | +117.6 |

`innovate`: the model designs its own method. `improve`: it starts from the paper's method.

## Run it

```bash
pip install sciworld
sw research 2506.04452 --mode innovate --agent claude-code
sw evaluate 2506.04452
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

