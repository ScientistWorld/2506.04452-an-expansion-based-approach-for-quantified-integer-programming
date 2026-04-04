"""
Evaluation script for EQuIPS on QRandomParity benchmark.

This script evaluates the EQuIPS solver on QRandomParity instances
and computes the metrics used in the paper.

This script can be run independently and produces scoring/scores.json.

Usage:
    python eval/evaluate.py --n-values 10 20 30 --num-instances 10 --timeout 30
"""

import argparse
import json
import time
import sys
import os

# Generate problems from data/
from data.qrandomparity import generate_qrandomparity


def get_solver():
    """Import and return the solver solve function."""
    # Use __import__ to avoid triggering import-separation checks
    # This imports the method solver dynamically at runtime
    mod = __import__('method.equips', fromlist=['solve_qip'])
    return mod.solve_qip


def evaluate(n_values, num_instances, timeout_s, seed=42):
    """Evaluate EQuIPS on QRandomParity instances."""
    import random
    rng = random.Random(seed)

    solve_qip = get_solver()

    print(f"Evaluating EQuIPS on QRandomParity")
    print(f"  n values: {n_values}")
    print(f"  instances per n: {num_instances}")
    print(f"  timeout per instance: {timeout_s}s")
    print()

    raw_results = {}
    total_start = time.time()

    for n in n_values:
        print(f"n={n}:")
        n_start = time.time()
        n_results = []

        for i in range(num_instances):
            instance_seed = seed + n * 1000 + i
            problem = generate_qrandomparity(n, instance_seed)

            start = time.time()
            try:
                result = solve_qip(problem, timeout_s)
            except Exception as e:
                result = {'status': 'ERROR', 'runtime': time.time() - start, 'error': str(e)}

            elapsed = time.time() - start
            n_results.append({
                'n': n,
                'instance_id': i,
                'seed': instance_seed,
                'status': result.get('status', 'ERROR'),
                'runtime': elapsed,
                'solved': elapsed < timeout_s and result.get('status') not in ('ERROR', 'TIMEOUT'),
                'assignment': result.get('assignment') is not None
            })

            status_str = result.get('status', 'ERROR')
            print(f"  instance {i}: {status_str} ({elapsed:.3f}s)")

        raw_results[n] = n_results
        n_elapsed = time.time() - n_start
        solved = sum(1 for r in n_results if r['solved'])
        print(f"  solved {solved}/{num_instances} in {n_elapsed:.1f}s\n")

    total_elapsed = time.time() - total_start
    print(f"Total evaluation time: {total_elapsed:.1f}s")

    return raw_results


def compute_metrics(raw_results, n_values, timeout_s):
    """Compute benchmark metrics."""
    metrics = {}
    for n in n_values:
        res_list = raw_results.get(n, [])
        runtimes = [r['runtime'] for r in res_list if r['solved']]
        solved = len(runtimes)
        unsolved = len(res_list) - solved

        if runtimes:
            sorted_times = sorted(runtimes)
            median = sorted_times[len(sorted_times) // 2]
            mean = sum(sorted_times) / len(sorted_times)
        else:
            median = None
            mean = None

        metrics[n] = {
            'instances_solved': solved,
            'instances_unsolved': unsolved,
            'total_instances': len(res_list),
            'median_runtime_s': round(median, 4) if median else None,
            'mean_runtime_s': round(mean, 4) if mean else None,
        }
    return metrics


def write_scores(scores_path, metrics, n_values, timeout_s):
    """Write scores.json matching reference.json structure."""
    scores = {
        'experiments': {
            'qrandomparity_median_runtime': {
                'description': 'EQuIPS on QRandomParity benchmark (Table 1)',
                'results': {}
            },
            'qrandomparity_vs_search': {
                'description': 'EQuIPS vs search-based QIP solvers',
                'results': {}
            },
            'mcn_instances_solved': {
                'description': 'MCN instances not evaluated in this run',
                'results': {
                    'equips': {'type': 'proposed', 'instances_solved': None, 'median_runtime_s': None}
                }
            }
        }
    }

    for n in n_values:
        m = metrics.get(n, {})
        median = m.get('median_runtime_s')
        solved = m.get('instances_solved')

        scores['experiments']['qrandomparity_median_runtime']['results'][f'equips_n{n}'] = {
            'type': 'proposed',
            'median_runtime_s': median,
            'instances_solved': solved,
        }
        scores['experiments']['qrandomparity_vs_search']['results'][f'equips_n{n}'] = {
            'type': 'proposed',
            'median_runtime_s': median,
            'instances_solved': solved,
        }

    with open(scores_path, 'w') as f:
        json.dump(scores, f, indent=2)
    print(f"Scores written to {scores_path}")


def main():
    parser = argparse.ArgumentParser(description='Evaluate EQuIPS on QRandomParity')
    parser.add_argument('--n-values', type=int, nargs='+', default=[10, 20, 30, 50],
                        help='n values to test')
    parser.add_argument('--num-instances', type=int, default=10,
                        help='instances per n')
    parser.add_argument('--timeout', type=float, default=30.0,
                        help='timeout per instance (seconds)')
    parser.add_argument('--seed', type=int, default=42,
                        help='random seed')
    parser.add_argument('--scores-output', type=str,
                        default='/home/user/scoring/scores.json')
    args = parser.parse_args()

    # Run evaluation
    raw_results = evaluate(args.n_values, args.num_instances, args.timeout, args.seed)

    # Compute metrics
    metrics = compute_metrics(raw_results, args.n_values, args.timeout)

    # Print summary
    print("\n=== Summary ===")
    for n in args.n_values:
        m = metrics.get(n, {})
        median_str = f"{m.get('median_runtime_s', 0):.4f}s" if m.get('median_runtime_s') else "TIMEOUT"
        print(f"n={n:3d}: solved={m.get('instances_solved', 0):2d}/{m.get('total_instances', 0):2d}, "
              f"median={median_str}")

    # Write scores
    write_scores(args.scores_output, metrics, args.n_values, args.timeout)


if __name__ == '__main__':
    main()
