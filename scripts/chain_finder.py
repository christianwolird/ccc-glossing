"""
Find longest simple chains in an undirected graph given by pair lines like:

A <-> B
C <-> D

Usage:
    python3 longest_pair_chains.py pairs.txt
    python3 longest_pair_chains.py pairs.txt --top 3

Notes:
- Treats each "<->" line as an undirected edge.
- Computes exact longest simple paths component-by-component using subset DP.
- This is practical for the small/medium components that arise in your glossary-pair graph.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


def parse_pairs(path: Path) -> Dict[str, Set[str]]:
    adj: Dict[str, Set[str]] = defaultdict(set)

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "<->" not in line:
            raise ValueError(f"Line {lineno} does not contain '<->': {raw!r}")
        left, right = [x.strip() for x in line.split("<->", 1)]
        if not left or not right:
            raise ValueError(f"Line {lineno} has an empty endpoint: {raw!r}")
        if left == right:
            # Ignore self-loops
            continue
        adj[left].add(right)
        adj[right].add(left)

    return dict(adj)


def connected_components(adj: Dict[str, Set[str]]) -> List[List[str]]:
    seen: Set[str] = set()
    comps: List[List[str]] = []

    for start in sorted(adj):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        comp: List[str] = []

        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)

        comps.append(sorted(comp))

    return comps


def reconstruct_path(
    end_state: Tuple[int, int],
    prev: Dict[Tuple[int, int], int],
    comp_nodes: List[str],
) -> List[str]:
    mask, end = end_state
    out_idx: List[int] = []

    while True:
        out_idx.append(end)
        p = prev[(mask, end)]
        if p == -2:
            break
        mask ^= (1 << end)
        end = p

    out_idx.reverse()
    return [comp_nodes[i] for i in out_idx]


def all_max_paths_in_component(comp_nodes: List[str], adj: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Exact subset-DP for all longest simple paths in one connected component.

    DP state:
      (mask, end) is reachable if there is a simple path visiting exactly the
      vertices in mask and ending at vertex index end.
    """
    idx = {u: i for i, u in enumerate(comp_nodes)}
    m = len(comp_nodes)

    nbrmask = [0] * m
    for u in comp_nodes:
        i = idx[u]
        mask = 0
        for v in adj[u]:
            if v in idx:
                mask |= 1 << idx[v]
        nbrmask[i] = mask

    prev: Dict[Tuple[int, int], int] = {}
    best_len = 0
    best_states: List[Tuple[int, int]] = []

    for i in range(m):
        state = (1 << i, i)
        prev[state] = -2
        best_len = 1
        best_states = [state]

    for mask in range(1, 1 << m):
        ends = [i for i in range(m) if (mask, i) in prev]
        if not ends:
            continue

        size = mask.bit_count()
        if size > best_len:
            best_len = size
            best_states = [(mask, ends[0])]
        elif size == best_len:
            for e in ends:
                best_states.append((mask, e))

        for end in ends:
            avail = nbrmask[end] & ~mask
            while avail:
                bit = avail & -avail
                nxt = bit.bit_length() - 1
                newmask = mask | bit
                state = (newmask, nxt)
                if state not in prev:
                    prev[state] = end
                avail -= bit

    # Reconstruct and canonicalize reversal duplicates
    unique: Dict[Tuple[str, ...], List[str]] = {}
    for state in best_states:
        path = reconstruct_path(state, prev, comp_nodes)
        rev = list(reversed(path))
        key = tuple(path) if tuple(path) <= tuple(rev) else tuple(rev)
        unique[key] = list(key)

    return sorted(unique.values())


def top_longest_paths(adj: Dict[str, Set[str]], top_k: int) -> List[List[str]]:
    comps = connected_components(adj)
    all_paths: List[List[str]] = []

    for comp in comps:
        all_paths.extend(all_max_paths_in_component(comp, adj))

    # Sort longest first, then lexicographically for stability
    all_paths.sort(key=lambda p: (-len(p), p))
    return all_paths[:top_k]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs_file", type=Path, help="Text file with lines 'A <-> B'")
    parser.add_argument("--top", type=int, default=3, help="How many longest chains to print")
    args = parser.parse_args()

    adj = parse_pairs(args.pairs_file)
    comps = connected_components(adj)
    paths = top_longest_paths(adj, args.top)

    print(f"Nodes: {len(adj)}")
    print(f"Connected components: {len(comps)}")
    print("Component sizes:", sorted((len(c) for c in comps), reverse=True))
    print()

    for i, path in enumerate(paths, start=1):
        print(f"Chain {i}")
        print(f"  vertices: {len(path)}")
        print(f"  edges:    {len(path) - 1}")
        print("  " + " -> ".join(path))
        print()


if __name__ == "__main__":
    main()
