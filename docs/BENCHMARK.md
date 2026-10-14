# Public-benchmark protocol in progress

Scope: LongMemEval-S, all 500 questions; LoCoMo, categories 1–4, all 1,540 questions across ten conversations. LoCoMo category counts are 282, 321, 96, and 841. Category 5 is excluded explicitly. No questions are selected using model scores.

Four arms yield 8,160 answer predictions: BM25, Seshat knowledge nodes, budget-adapted UnifiedMem flat retrieval, and budget-adapted UnifiedMem graph retrieval. Each arm first passes eleven representative GPU semantic sentinels, reused in its full count. The frozen answer/controller/construction model is Qwen3-8B with thinking disabled, greedy BF16 generation, a 32,768-token single-call window, and a cumulative 8,192-token external-read ceiling. UnifiedMem's pretrained Contriever retrieval component also performs GPU inference.

Sources preserve all conversation roles and original dates. Address labels do not reveal answer/abstention status. Construction cannot read questions, gold answers, support labels, or LoCoMo's derived summaries. Source chunks are bounded at 1,024 Qwen tokens with lossless character-boundary splitting of long turns.

The real Seshat variant builds typed, directed nodes using source-only model extraction. Exact quotations bind facts to source chunks. Invalid extraction is recorded, and the source chunk is retained. Initial BM25 seeds lead to node pages; later visits follow displayed directed targets or other pages of the same entity. Visited source addresses are retained for the final answer. Repeated pages, candidate directories, and final original rereads count toward external reads. Construction is separately charged, not treated as free preprocessing.

UnifiedMem arms directly reuse its released flat/GraphRAG components but adapt output caps, decoding, chunking, roles, tokenizer, answer prompt, and read budget. They must be labeled **budget-adapted baselines**, not native paper reproductions. Exact-ID coverage, independent scoring, actual model-PID GPU compute, and source/prompt/token bindings are required before acceptance.

LongMemEval uses the official category-specific judging prompts with a local Qwen judge and is labeled **Qwen-judged provisional**. It is not interchangeable with GPT-4o or other paper judges. LoCoMo reports official token F1, independently checked, and local Qwen accuracy separately. Dataset metrics are not averaged together. Evidence coverage uses LongMemEval support-session recall and LoCoMo complete-turn recall; neither proves semantic entailment.

Report all construction, retrieval embedding, controller, answer, calibration, failed-attempt, and judge calls and input/output tokens. Paired analysis must use identical IDs and bootstrap by source document/conversation. Parts of LongMemEval were used in earlier development, so this is not wholly unseen confirmation data.

No final results for this matrix are released yet. The synthetic score is not a substitute for this evaluation.

Official resources: [LongMemEval](https://github.com/xiaowu0162/LongMemEval), [LoCoMo](https://github.com/snap-research/locomo), and [UnifiedMem](https://github.com/AvatarMemory/UnifiedMem).
