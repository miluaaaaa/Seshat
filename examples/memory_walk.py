"""Scripted memory navigation, not LLM inference or an accuracy evaluation."""
import json
from seshat.dictionary import build_nodes, linked_nodes
from seshat.lexical import store


def main():
    source = "\n".join([
        "The publication record identifies company ALPHA as the publisher of game ORBIT.",
        "The ownership record states that company ALPHA was acquired by company BETA.",
        "The archival record explicitly states that company BETA permanently closed in the year 1998.",
        "According to the company registration record, company BETA was originally founded in the year 1974.",
    ])
    records = store(source)
    nodes = build_nodes(records)
    current, visited, retained = ["ORBIT"], [], []
    while current:
        print("Read nodes:", json.dumps(current))
        for name in current:
            visited.append(name)
            retained.extend(f["source_id"] for f in nodes[name]["facts"])
        current = [n for n in linked_nodes(nodes, current) if n not in visited]
    retained = list(dict.fromkeys(retained))
    print("Retained source addresses:", json.dumps(retained))
    print("Original evidence:")
    for sid in retained:
        print(sid, records[sid])
    # This deterministic fixture reads a known closure fact; it is not a model answer.
    closure = next(f["value"] for f in nodes["BETA"]["facts"] if f["relation"] == "closed_in")
    print("Scripted fixture closure year:", closure)


if __name__ == "__main__":
    main()
