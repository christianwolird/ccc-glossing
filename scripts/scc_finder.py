import json
from pathlib import Path
from collections import defaultdict


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "clean" / "references.json"


def load_graph(path: Path) -> dict[str, list[str]]:
    graph = json.loads(path.read_text(encoding="utf-8"))

    all_nodes = set(graph.keys())
    for refs in graph.values():
        all_nodes.update(refs)

    for node in all_nodes:
        graph.setdefault(node, [])

    return graph


def tarjans_scc(graph: dict[str, list[str]]) -> list[list[str]]:
    index = 0
    stack = []
    on_stack = set()
    indices = {}
    lowlink = {}
    sccs = []

    def strongconnect(v):
        nonlocal index

        indices[v] = index
        lowlink[v] = index
        index += 1

        stack.append(v)
        on_stack.add(v)

        for w in graph[v]:
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])

        if lowlink[v] == indices[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(sorted(comp))

    for v in sorted(graph):
        if v not in indices:
            strongconnect(v)

    return sorted(sccs, key=lambda c: (-len(c), c))


def build_condensation_graph(graph, sccs):
    node_to_scc = {}
    for i, comp in enumerate(sccs):
        for node in comp:
            node_to_scc[node] = i

    dag = defaultdict(set)

    for u, outs in graph.items():
        su = node_to_scc[u]
        for v in outs:
            sv = node_to_scc[v]
            if su != sv:
                dag[su].add(sv)

    for i in range(len(sccs)):
        dag.setdefault(i, set())

    return node_to_scc, dag


def main():
    graph = load_graph(INPUT)
    sccs = tarjans_scc(graph)
    _, dag = build_condensation_graph(graph, sccs)

    # collect nontrivial SCCs
    nontrivial = [(i, comp) for i, comp in enumerate(sccs) if len(comp) >= 2]

    # assign new labels 1..k
    id_map = {old_i: new_i+1 for new_i, (old_i, _) in enumerate(nontrivial)}
    nontrivial_set = set(id_map.keys())

    print("NONTRIVIAL SCCs\n")
    for new_i, (old_i, comp) in enumerate(nontrivial, start=1):
        print(f"{new_i}: {comp}")

    print("\nEDGES BETWEEN NONTRIVIAL SCCs\n")

    edges = set()
    for old_src in nontrivial_set:
        for old_dst in dag[old_src]:
            if old_dst in nontrivial_set:
                edges.add((id_map[old_src], id_map[old_dst]))

    for src, dst in sorted(edges):
        print(f"{src} -> {dst}")

    print(f"\nTotal nontrivial SCCs: {len(nontrivial)}")
    print(f"Total edges between them: {len(edges)}")


if __name__ == "__main__":
    main()
