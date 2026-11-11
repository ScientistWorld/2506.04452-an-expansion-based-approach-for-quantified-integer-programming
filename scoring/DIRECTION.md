# Research Direction

Future scientist agents should treat this workspace as a benchmark for exact
QIP decision solving under a CPU budget, on the paper's two instance
families.

## In scope
- Faster and stronger general QIP solving: better abstraction/refinement,
  better handling of the quantifier-free subproblems, presolve and
  propagation that exploit the linear structure (e.g. parity and cardinality
  reasoning), better strategies for universal moves, incremental solving,
  lower Python overhead.
- Pushing either ladder further: more decided instances at the large sizes
  (QRandomParity n >= 128, MCN graphs >= 56 nodes) without wrong answers.
- Improving the exhaustive baseline or adding other exact baselines under
  separate solver directories.

## Out of scope
- Changing ladders, budgets, the evaluator or the wrong-answer rule.
- Family-specific decoders that recognise the generator and bypass QIP
  solving, answers looked up from files, or guessing on timeouts.
- Converting the task into unquantified integer programming without
  accounting for the universal player.
