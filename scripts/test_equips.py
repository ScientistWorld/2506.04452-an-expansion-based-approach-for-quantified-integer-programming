#!/usr/bin/env python3
"""Quick test of EQuIPS solver on small QRandomParity instances."""

import os
import sys
import time
sys.path.insert(0, '/home/user')

from data.qrandomparity import generate_qrandomparity
from method.equips import solve_qip, solve_qip_optimization


def test_basic():
    """Test basic QIP solving."""
    print("=== EQuIPS Basic Test ===")

    # Test 1: Simple SAT instance
    print("\nTest 1: Simple SAT QIP")
    from data.qrandomparity import QIPProblem, Variable, Constraint

    # exists x, y : x + y <= 3, x >= 0, y >= 0
    p = QIPProblem(
        variables=[
            Variable('x', 0, 5, 'E'),
            Variable('y', 0, 5, 'E'),
        ],
        constraints=[
            Constraint({'x': 1, 'y': 1}, 3),
        ]
    )
    result = solve_qip(p, timeout_s=5)
    print(f"  Result: {result}")
    assert result['status'] == 'SAT', f"Expected SAT, got {result['status']}"
    print("  PASS")

    # Test 2: Simple UNSAT instance
    print("\nTest 2: Simple UNSAT QIP")
    p2 = QIPProblem(
        variables=[Variable('x', 0, 5, 'E')],
        constraints=[Constraint({'x': 1}, -1)]  # x <= -1 impossible
    )
    result2 = solve_qip(p2, timeout_s=5)
    print(f"  Result: {result2}")
    assert result2['status'] == 'UNSAT', f"Expected UNSAT, got {result2['status']}"
    print("  PASS")


def test_qrandomparity():
    """Test QRandomParity instances."""
    print("\n=== QRandomParity Tests ===")

    for n in [5, 10, 15]:
        print(f"\nTest: n={n}")
        for seed in range(3):
            problem = generate_qrandomparity(n, seed)
            start = time.time()
            result = solve_qip(problem, timeout_s=10.0)
            elapsed = time.time() - start
            print(f"  seed={seed}: {result['status']} ({elapsed:.3f}s)")


def test_optimization():
    """Test decision-to-optimization reduction for both min and max senses."""
    print("\n=== Optimization Tests ===")

    from data.qrandomparity import QIPProblem, Variable, Constraint

    maximize_problem = QIPProblem(
        variables=[Variable('x', 0, 3, 'E')],
        constraints=[],
        objective={'x': 1},
        objective_sense='max',
    )
    maximize_result = solve_qip_optimization(maximize_problem, timeout_s=5)
    print(f"  Max result: {maximize_result}")
    assert maximize_result['status'] == 'SAT', f"Expected SAT, got {maximize_result['status']}"
    assert maximize_result['optimal_value'] == 3, maximize_result

    minimize_problem = QIPProblem(
        variables=[Variable('x', 0, 3, 'E')],
        constraints=[Constraint({'x': -1}, -1)],
        objective={'x': 1},
        objective_sense='min',
    )
    minimize_result = solve_qip_optimization(minimize_problem, timeout_s=5)
    print(f"  Min result: {minimize_result}")
    assert minimize_result['status'] == 'SAT', f"Expected SAT, got {minimize_result['status']}"
    assert minimize_result['optimal_value'] == 1, minimize_result


if __name__ == '__main__':
    test_basic()
    test_optimization()
    if os.environ.get("EQUIPS_TEST_MODE", "full") != "quick":
        test_qrandomparity()
    print("\n=== All tests passed ===")
