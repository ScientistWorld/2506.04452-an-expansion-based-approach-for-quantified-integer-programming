# Evaluation

## Scored Experiments

The active scored experiment is:
- `qrandomparity_n10`

It is a fixed 100-instance QRandomParity batch at size parameter `n=10`. The
scored output must report one result entry per method that ran on that batch.
This is a scaled replacement for the paper's larger QRandomParity settings,
chosen because the open-source backend stack reproduces a clean runtime gap here
without collapsing into a trivial benchmark.

## Metrics

The scored experiment uses:
- `median_runtime_s`: median runtime over solved instances, lower is better
- `instances_solved`: number of instances solved within the timeout, higher is better
- `mean_runtime_s`: mean runtime over solved instances, lower is better
- `p90_runtime_s`: 90th percentile capped runtime over the full batch, lower is better

The primary metric is runtime, but solved count is a required companion metric
so a method cannot improve the score by timing out on harder cases. `p90` is
the anti-shortcut guardrail because it penalizes long-tail slowdowns and
timeouts on the fixed batch.

## Protocol

1. Generate the benchmark instances with the provided QRandomParity generator.
2. Run the candidate solver and the search-style exact baseline on the same
   fixed 100-instance batch.
3. Use the configured timeout for every instance in the batch.
4. Record, for each instance, whether it was solved and how long it took.
5. Aggregate per experiment into the four runtime / coverage metrics above.

## Interpretation

Improvements should preserve correctness while reducing runtime and maintaining
strong solved coverage on the same benchmark family. Results from easier or
harder instance sizes can still be useful for development, but they are not
part of the scored contract unless added explicitly under a new experiment
name.
