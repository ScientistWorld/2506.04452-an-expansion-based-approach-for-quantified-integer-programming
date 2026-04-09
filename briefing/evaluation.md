# Evaluation

## Scored Experiments

The gym currently scores two QRandomParity settings:
- `qrandomparity_n100`
- `qrandomparity_n200`

Each setting consists of a batch of procedurally generated instances at a fixed size parameter `n`. The scored output must report one result entry per method for each experiment it actually ran.

## Metrics

Each scored experiment uses:
- `median_runtime_s`: median runtime over solved instances, lower is better
- `instances_solved`: number of instances solved within the timeout, higher is better

The primary metric is runtime, but solved count is a required companion metric so a method cannot improve the score by timing out on harder cases.

## Protocol

1. Generate the benchmark instances with the provided QRandomParity generator.
2. Run the candidate solver on the fixed instance batch for each scored `n`.
3. Use the configured timeout for every instance in the batch.
4. Record, for each instance, whether it was solved and how long it took.
5. Aggregate per experiment into solved count and median runtime.

## Interpretation

Improvements should preserve correctness while reducing runtime and maintaining strong solved coverage on the same benchmark family. Results from easier instance sizes or different problem families can be useful for development, but they are not part of the scored contract unless added explicitly to `reference.json` and `scores.json`.
