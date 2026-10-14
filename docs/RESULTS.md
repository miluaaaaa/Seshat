# Results and limitations

The completed pilot uses 64 deterministic synthetic development cases: date, negation, multihop, and numeric questions, 16 of each. It is not a held-out confirmation study. Four representative GPU sentinels preceded the remaining cases; all 64 were independently accepted in 16 bundles.

| Question type | Full source | Sentence dictionary | Knowledge nodes |
| --- | ---: | ---: | ---: |
| Date | 100.00% | 100.00% | 100.00% |
| Negation | 87.50% | 100.00% | 100.00% |
| Multihop | 68.75% | 18.75% | 81.25% |
| Numeric | 0.00% | 87.50% | 81.25% |

Relative to the sentence dictionary, knowledge nodes improved multihop answers from 3/16 to 13/16 and reduced numeric answers from 14/16 to 13/16. The full-source numeric baseline scored 0/16; this is a serious protocol-specific limitation, not evidence about general arithmetic ability.

Mean model calls increased from 2 to 2.1875 (+9.375%). Mean input/output tokens increased from 427.25 to 701.234375 (+64.13%). Mean external reads increased from 99.78125 to 323.421875 tokens. The same budget ceiling does not imply the same actual cost. Token counts do not directly measure GPU time, money, or retrieval speed.

There were 140 new GPU model calls: 76 access-controller calls and 64 final answers. No model calls were used for synthetic node construction or judging. Fifty-two cases used one controller round and twelve used two; none used three. Historical acceptance required real model-PID GPU memory and positive-duration forward CUDA kernels, exact source/prompt/token bindings, independent scoring, and nonoverlapping physical-GPU lane intervals.

Of the six errors, five retained complete required evidence but answered incorrectly: two multihop entity/year errors and three numeric errors. One controller stopped early and omitted the final closure evidence. Evidence coverage therefore helps diagnose failure but does not prove entailment or correct reasoning.

The total serialized node payload was 101,408 bytes; original source payload was 126,656 bytes. Both were retained. These are payload sizes, not measured peak RAM or GPU KV-cache consumption. Node IDs are ordinary tokenizer strings, not registered single tokens.

The changes combine node organization, navigation, and monotonic evidence retention. No ablation isolates their individual contributions. The builder recognizes exact synthetic sentence templates. The results neither establish statistical superiority nor justify extrapolation to public conversation benchmarks.
