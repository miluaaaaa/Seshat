# Implemented method

The released code is the `knowledge_nodes_v1` synthetic method, adapted only to package-relative imports and portable host configuration. The source manifest records hashes of the original and released method modules.

1. Split the source into complete sentences and assign stable local addresses such as `S000`.
2. Compile source-only typed facts into nodes. Distinguish founding from closure, preserve explicit negation, and direct publisher/acquisition links from subject to object.
3. Rank source sentences with BM25 and read the owner nodes of up to three initial hits.
4. Ask the model whether the evidence is sufficient or which displayed, unvisited directed targets to visit. Reject invented addresses and invalid output schemas.
5. Retain all source addresses associated with visited nodes. Reserve budget for their final reread, then answer using the original sentences.

The model can make up to three access decisions. Node-page tokens and final original-sentence rereads count against the cumulative 8,192-token ceiling. Model input/output costs include controller and answer calls. The synthetic fixture's node compilation is deterministic and requires no model calls.

`dictionary.py` implements nodes, directed navigation, controller prompts, cumulative page/reread accounting, and trace verification. `lexical.py` implements sentence storage and BM25. `contract.py` deterministically generates the 64 cases and independently scores strict JSON answers. `node_verifier.py` parses sources separately from the builder.

## What this does not implement

- Arbitrary new sentences encoded into a single learned semantic token.
- Reasoning from an opaque ID without reading its associated facts or text.
- A trained memory-access policy or modified Qwen weights.
- A complete LLM Wiki implementation.
- A demonstrated KV-cache compression or inference-speed improvement.

The active real-data variant replaces template parsing with source-only Qwen extraction of typed relations and exact quotations. That changes construction cost and extraction reliability; its results must be evaluated separately from the synthetic version.
