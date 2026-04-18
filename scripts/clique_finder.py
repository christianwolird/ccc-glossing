import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path


INPUT = Path("data/clean/references.json")


def load_graph(path: Path) -> dict[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: list(dict.fromkeys(v)) for k, v in data.items()}


def mutual_pairs(graph: dict[str, list[str]]) -> list[tuple[str, str]]:
    """
    Return all unordered pairs {a,b} such that a -> b and b -> a.
    """
    adj = {u: set(vs) for u, vs in graph.items()}
    pairs = []

    for a in sorted(graph):
        for b in adj[a]:
            if b in adj and a in adj[b] and a < b:
                pairs.append((a, b))

    return pairs


def pair_neighbor_map(pairs: list[tuple[str, str]]) -> dict[str, set[str]]:
    """
    Build the undirected adjacency map of the mutual-pair graph.
    """
    nbrs: dict[str, set[str]] = defaultdict(set)
    for a, b in pairs:
        nbrs[a].add(b)
        nbrs[b].add(a)
    return nbrs


def triangles_from_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    """
    Find all 3-cliques in the undirected graph whose edges are the mutual pairs.
    For each pair (a,b), every common neighbor c of a and b gives a triangle.
    """
    nbrs = pair_neighbor_map(pairs)
    triangles = set()

    for a, b in pairs:
        common = nbrs[a] & nbrs[b]
        for c in common:
            tri = tuple(sorted((a, b, c)))
            triangles.add(tri)

    return sorted(triangles)


def main() -> None:
    graph = load_graph(INPUT)

    pairs = mutual_pairs(graph)
    triangles = triangles_from_pairs(pairs)

    print("\nMUTUAL PAIRS")
    print(f"Count: {len(pairs)}")
    for a, b in pairs:
        print(f"{a} <-> {b}")

    print("\n3-CLIQUES")
    print(f"Count: {len(triangles)}")
    for tri in triangles:
        print(tri)


if __name__ == "__main__":
    main()
