# Research Direction

Future scientist agents should treat this workspace as a benchmark for exact
QIP decision solving under a fixed computation budget (counted instructions),
on the paper's two instance families.

## In scope
- Faster and stronger general QIP solving: better abstraction/refinement,
  better handling of the quantifier-free subproblems, presolve and
  propagation that exploit the linear structure (e.g. parity and cardinality
  reasoning), better strategies for choosing moves and counter-moves,
  incremental solving, lower interpreter and start-up overhead.
- Pushing either ladder further: more decided instances at the large sizes
  (QRandomParity n >= 128, MCN graphs >= 40 nodes) without wrong answers.
  The MCN ladder is where the reference is weakest; no simple change to its
  sub-solvers has yet moved it by more than solver-seed noise.
- Improving the exhaustive baseline or adding other exact baselines under
  separate solver directories.

## Out of scope
- Changing ladders, budgets, the evaluator or the wrong-answer rule.
- Family-specific decoders that recognise the generator and bypass QIP
  solving, answers looked up from files, state carried between instances, or
  guessing on timeouts.
- Converting the task into unquantified integer programming without
  accounting for the universal player.
