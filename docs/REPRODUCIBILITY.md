# Reproducibility

## Portable mechanism check

Run from the repository root:

```bash
PYTHONPATH=src python examples/memory_walk.py
PYTHONPATH=src python -m unittest discover -s tests -v
```

This checks the released algorithm's source construction, navigation, address retention, and independent trace replay without installing model libraries. It uses scripted responses and a clearly named byte-counting fixture tokenizer. Fixture counts are **not Qwen tokens**, and outputs are not model benchmark results.

## Model-backed reproduction

`seshat.dictionary.run_dictionary(case, tokenizer, call)` exposes the implemented method. `case` contains a source and query; node construction consumes only the source. The tokenizer must be the actual Qwen tokenizer. The generation callback receives `(prompt, output_cap, task)` and returns a dictionary containing `text`, `prompt`, and any additional execution/token evidence collected by the adapter.

To reproduce the reported pilot, generate cases with `contract.golden()` (seed 18423), run frozen Qwen3-8B in BF16 with thinking disabled and greedy generation, keep the 32K call window and 8K cumulative read ceiling, and use the original controller/final prompts from the released modules. Score with both `score` and `independent_score`, replay `verify_trace`, and account for every controller and final-answer call. The raw-text and dictionary arms require their own predictions; this showcase does not redistribute historical per-example prediction payloads.

Model execution must occur on an actual GPU. Before accepting output, capture the same inference PID with model-sized GPU memory and positive-duration computation during the requested forward. Allocation alone is insufficient. Stop CPU-saturated/GPU-idle inference after startup rather than counting it as a result. Use exclusive physical GPUs and deterministic disjoint partitions, then merge exact IDs and bindings. No CPU model fallback is part of the protocol.

The private execution harness contains site-specific Slurm/Zen admission, vLLM request profiling, trace verification, scheduling recovery, and baseline-reuse bindings. It is not included as a portable one-command accuracy reproduction in this showcase. The released method and fixtures reproduce the memory mechanism; reproducing the historical 90.625% model result additionally requires weights, a generation adapter, baselines, and equivalent execution verification.

Dependencies for such a reproduction include the Qwen tokenizer, an appropriate GPU model-serving stack, and model weights acquired under their upstream license. These are intentionally outside the dependency-free example.
