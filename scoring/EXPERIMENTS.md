# Experiment Overview

Both experiments count correctly decided QIP decision instances within a
fixed CPU budget per instance, along a ladder of growing sizes.  A single
wrong decision fails the whole run, so a method cannot trade correctness for
coverage.

## qrandomparity_ladder
Establishes whether a solver can decide quantified parity instances (the
paper's QRandomParity family and planted variants of it) as their size grows
from 10 to 1000 outer variables, the range of the paper's own experiments.
The paper's claim is that a QIP solver working on the linear encoding handles
this family far beyond what search over assignments can reach; the ladder
measures how far up a method gets, on TRUE and FALSE instances alike, and
whether it also copes with variants that add a cardinality relation.

## mcn_ladder
Establishes whether a solver can decide trilevel multilevel critical node
instances (defender-attacker-defender on a graph, attacker restricted by a
budget) at their exact optimum and one above it, as graphs grow from 8 to 96
nodes.  This is the paper's optimization showcase, where its method is
competitive but not best; the ladder rewards solvers that certify optimality
on larger graphs than the reference does.
