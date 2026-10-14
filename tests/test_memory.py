"""Structural and semantic regression checks; no model inference is performed."""
import json
import unittest
from seshat.contract import golden, render_fact
from seshat.dictionary import (
    build_nodes, decision, golden_dictionary, linked_nodes,
    run_dictionary, verify_trace,
)
from seshat.lexical import store
from seshat.node_verifier import independent_nodes


class ByteFixtureTokenizer:
    """Deterministic test counter; deliberately not advertised as Qwen tokens."""
    def encode(self, text, add_special_tokens=False):
        return list(text.encode("utf-8"))


class MemoryTests(unittest.TestCase):
    def test_all_sources_and_independent_parsers(self):
        cases = golden_dictionary()
        self.assertEqual(len(cases), 64)
        self.assertEqual(len({c["source_sha256"] for c in cases}), 64)
        for c in cases:
            records = store(c["source"])
            self.assertEqual("\n".join(records.values()), c["source"])
            self.assertEqual(build_nodes(records), independent_nodes(records))

    def test_direction_and_relation_types(self):
        records = store("\n".join([
            render_fact(["G", "P", "A"]), render_fact(["A", "A", "B"]),
            render_fact(["B", "F", "1974"]), render_fact(["B", "C", "1998"]),
            render_fact(["B", "L", "no"]),
        ]))
        nodes = build_nodes(records)
        self.assertEqual(linked_nodes(nodes, ["G"]), ["A"])
        self.assertEqual(linked_nodes(nodes, ["A"]), ["B"])
        self.assertEqual(linked_nodes(nodes, ["B"]), [])
        self.assertEqual({f["relation"]: f["value"] for f in nodes["B"]["facts"]},
                         {"founded_in": "1974", "closed_in": "1998", "has_license": "no"})

    def test_unknown_sources_and_invented_addresses_fail_closed(self):
        with self.assertRaises(AssertionError):
            build_nodes(store("Unrecognized free-form source sentence."))
        for value in ["broken", '{"ready":false,"next_nodes":["FAKE"]}',
                      '{"ready":false,"next_nodes":["A","A"]}']:
            self.assertFalse(decision(value, ["A"])["valid"])
        self.assertTrue(decision('{"ready":false,"next_nodes":["A"]}', ["A"])["valid"])

    def test_trace_replay_and_monotonic_evidence(self):
        tok = ByteFixtureTokenizer()
        # Scripted access explores actual displayed links. No gold answer drives access.
        for case in golden():
            def call(prompt, cap, task):
                if task == "node_access_controller":
                    fragment = prompt.split("Unvisited directed-link targets you may read next: ", 1)[1]
                    available = json.JSONDecoder().raw_decode(fragment)[0]
                    text = json.dumps({"ready": not available, "next_nodes": available[:3]})
                else:
                    text = '{"answer":"UNKNOWN"}'
                return {"prompt": prompt, "text": text}
            result = run_dictionary(case, tok, call)
            verify_trace(case, result, tok)
            self.assertLessEqual(result["external_read_tokens"], 8192)
            expected = {f["source_id"] for n in result["visited_nodes"]
                        for f in build_nodes(store(case["source"]))[n]["facts"]}
            self.assertEqual(set(result["kept_ids"]), expected)
            result["kept_ids"] = ["NONEXISTENT"]
            with self.assertRaises(AssertionError):
                verify_trace(case, result, tok)


if __name__ == "__main__":
    unittest.main()
