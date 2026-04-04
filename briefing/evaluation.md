# Evaluation

## Metrics

The primary evaluation metric is **runtime** (in seconds) — lower is better. A solver succeeds on an instance if it returns the correct answer (SAT/UNSAT) within a time limit.

Secondary metrics:
- **Number of instances solved** within the time limit (higher is better)
- **Median runtime** across solved instances (lower is better)

## Baselines and Targets

### QRandomParity (Table 1)
QRandomParity is a family of QIP/QBF instances parameterized by n. Each n generates 100 random instances (varying the permutation σ). Solvers tested:

| Solver | Description |
|--------|-------------|
| EQuIPS (proposed) | Expansion-based QIP solver using CEGAR |
| QFUNcms | State-of-the-art QBF expansion solver with CryptoMiniSat backend |
| DepQBF | Search-based QBF solver |
| Yasol | Search-based QIP solver |
| z3 | SMT solver |

Target performance (median runtime in seconds, /N = instances unsolved out of 100):
- EQuIPS at n=100: ~0.06s
- EQuIPS at n=500: ~1.0s
- EQuIPS at n=1000: ~3.4s (10 unsolved)
- QFUNcms at n=1000: 100 unsolved

### Multilevel Critical Node Problem (MCN)
Robust optimization on graphs. Compare:
- EQuIPS (proposed, expansion-based QIP)
- Yasol (search-based QIP)
- MCN_CR (column-and-row generation baseline)

Target: EQuIPS should solve the most instances overall (reference: 465/500+ instances).

## Evaluation Protocol

1. Generate or load QRandomParity instances for various n values
2. Run each solver with a 1800-second (30-minute) timeout per instance
3. Record runtime and correctness (SOLVED/UNSOLVED)
4. Compute median runtime and number of solved instances
5. For MCN: run with a 2-hour timeout per instance

The scientist should focus on improving EQuIPS's runtime and number of solved instances.
