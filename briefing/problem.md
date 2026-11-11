# Problem Definition

## Research Question

Quantified Integer Programming (QIP) asks whether the existential player of a
bounded integer game wins: variables are assigned block by block in a fixed
order, alternating between an existential and a universal player, and the
existential player wins if the final assignment satisfies a linear constraint
system.  The universal player's choices may additionally be restricted by
their own linear constraints (an uncertainty set).  An optimization version
asks for the best worst-case objective value; its decision version ("can the
existential player guarantee an objective of at least K?") is again a QIP.

The task is to decide QIP instances correctly and quickly: a better solver
decides more instances, and larger ones, within a fixed CPU budget.

## Problem Setting

Each instance is a QIP decision problem in the QLP text format (the format of
the paper's released solver and of the QIP solver Yasol):
- bounded integer (here binary) variables in an ordered quantifier prefix
  (`EXISTS`, `ALL`, `ORDER` sections; a new block starts at every alternation),
- a linear existential constraint system (`SUBJECT TO`),
- optionally linear constraints on the universal variables (`UNCERTAINTY
  SUBJECT TO`).
The answer is TRUE if the existential (first) player has a winning strategy,
FALSE otherwise.  Variable names and constraint order carry no information.

Two instance families are used, both from the paper's experiments:
- **QRandomParity** (paper Section 4): two parity computations over the same
  outer variables, in different orders, linked to one universal bit, in a
  linear encoding.  Besides the paper's own (FALSE) instance, each size has
  TRUE and FALSE variants with additional parity relations and with an
  additional cardinality relation, so the answer has to be derived from the
  constraints.  Sizes range from n = 10 to n = 1000 outer variables.
- **Multilevel critical node (MCN)** (paper Section 5.2): a defender
  vaccinates nodes, an attacker infects nodes within a budget (the universal
  player with an uncertainty set), the defender protects nodes; the decision
  asks whether at least K nodes can be guaranteed to be saved, with K at the
  exact optimum or one above it.  Graphs have 8 to 96 nodes.

The public generator (`data/benchmark.py`) and the train split
(`data/train_instances.json`, with answers) show the instance distribution;
the hidden test uses the same generator with secret seeds.

## Success Criteria

A successful solver:
- never returns a wrong TRUE/FALSE decision (one wrong decision fails the run),
- decides as many instances as possible within 10 s of CPU time each,
- keeps working as instances grow (the score counts instances across a ladder
  of sizes), on both families.
