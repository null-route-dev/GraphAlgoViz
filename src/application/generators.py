"""Random graph generators built on the standard library only.

The three generators cover the classic random graph models:

- Erdős–Rényi: every pair of nodes is connected with probability p.
- Barabási–Albert: each new node attaches to m existing nodes chosen
  with probability proportional to their current degree.
- Watts–Strogatz: a ring lattice is rewired with probability p to
  produce a small-world graph.

Every generator accepts an optional seed for reproducibility. When
the seed is None, the output differs between calls; when it is an
integer, repeated calls with the same parameters produce identical
graphs, which keeps tests deterministic.
"""

import random
from dataclasses import dataclass
from enum import Enum

from domain.entities.edge import Edge
from domain.entities.graph import Graph
from domain.entities.node import Node

DEFAULT_PROBABILITY = 0.2
DEFAULT_EDGES_PER_NEW_NODE = 2
DEFAULT_NEIGHBORS_PER_NODE = 4
DEFAULT_REWIRING_PROBABILITY = 0.1


class GeneratorKind(Enum):
    """Supported random graph models."""

    ERDOS_RENYI = "erdos_renyi"
    BARABASI_ALBERT = "barabasi_albert"
    WATTS_STROGATZ = "watts_strogatz"


@dataclass(frozen=True)
class GeneratorRequest:
    """Parameters for a single graph generation.

    Only the fields relevant to ``kind`` are used by the dispatcher;
    the rest keep their defaults.

    Args:
        kind: Which generator to run.
        node_count: Total number of nodes.
        probability: Edge probability for Erdős–Rényi.
        edges_per_new_node: Attachment count for Barabási–Albert.
        neighbors_per_node: Ring degree for Watts–Strogatz.
        rewiring_probability: Rewiring chance for Watts–Strogatz.
        seed: Optional random seed for reproducibility.
    """

    kind: GeneratorKind
    node_count: int
    probability: float = DEFAULT_PROBABILITY
    edges_per_new_node: int = DEFAULT_EDGES_PER_NEW_NODE
    neighbors_per_node: int = DEFAULT_NEIGHBORS_PER_NODE
    rewiring_probability: float = DEFAULT_REWIRING_PROBABILITY
    seed: int | None = None


def generate_erdos_renyi(
    node_count: int,
    probability: float,
    seed: int | None = None,
) -> Graph:
    """Generate an Erdős–Rényi random graph.

    Args:
        node_count: Total number of nodes. Must be at least 2.
        probability: Probability that any two nodes are connected.
        seed: Optional random seed.

    Returns:
        A graph with ``node_count`` nodes and random edges.

    Raises:
        ValueError: If node_count is less than 2, or probability is
            not in [0, 1].
    """
    if node_count < 2:
        raise ValueError("node_count must be at least 2")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be in [0, 1]")
    rng = random.Random(seed)
    graph = Graph()
    for i in range(1, node_count + 1):
        graph.add_node(Node(id=i))
    for u in range(1, node_count + 1):
        for v in range(u + 1, node_count + 1):
            if rng.random() < probability:
                graph.add_edge(Edge(source=u, target=v))
    return graph


def generate_barabasi_albert(
    node_count: int,
    edges_per_new_node: int,
    seed: int | None = None,
) -> Graph:
    """Generate a Barabási–Albert preferential attachment graph.

    Args:
        node_count: Total number of nodes. Must be at least 2.
        edges_per_new_node: How many existing nodes each new node
            connects to. Must be at least 1 and less than node_count.
        seed: Optional random seed.

    Returns:
        A graph with ``node_count`` nodes and preferential edges.

    Raises:
        ValueError: If node_count is less than 2, or the attachment
            count is out of range.
    """
    if node_count < 2:
        raise ValueError("node_count must be at least 2")
    if edges_per_new_node < 1 or edges_per_new_node >= node_count:
        raise ValueError(
            "edges_per_new_node must be at least 1 and less than node_count"
        )
    rng = random.Random(seed)
    graph = Graph()
    initial = edges_per_new_node + 1
    for i in range(1, initial + 1):
        graph.add_node(Node(id=i))
    for u in range(1, initial + 1):
        for v in range(u + 1, initial + 1):
            graph.add_edge(Edge(source=u, target=v))
    for new_id in range(initial + 1, node_count + 1):
        graph.add_node(Node(id=new_id))
        existing = list(range(1, new_id))
        chosen: set[int] = set()
        while len(chosen) < edges_per_new_node:
            weights = [len(graph.neighbors(u)) + 1 for u in existing]
            picked = rng.choices(existing, weights=weights, k=1)[0]
            chosen.add(picked)
        for target in chosen:
            graph.add_edge(Edge(source=new_id, target=target))
    return graph


def generate_watts_strogatz(
    node_count: int,
    neighbors_per_node: int,
    rewiring_probability: float,
    seed: int | None = None,
) -> Graph:
    """Generate a Watts–Strogatz small-world graph.

    Args:
        node_count: Total number of nodes. Must be at least 4.
        neighbors_per_node: Ring degree. Must be even, at least 2,
            and less than node_count.
        rewiring_probability: Fraction of edges that are randomly
            rewired.
        seed: Optional random seed.

    Returns:
        A graph with ``node_count`` nodes and rewired ring lattice
        edges.

    Raises:
        ValueError: If any parameter is out of range.
    """
    if node_count < 4:
        raise ValueError("node_count must be at least 4")
    if neighbors_per_node < 2 or neighbors_per_node % 2 != 0:
        raise ValueError("neighbors_per_node must be even and at least 2")
    if neighbors_per_node >= node_count:
        raise ValueError("neighbors_per_node must be less than node_count")
    if not 0.0 <= rewiring_probability <= 1.0:
        raise ValueError("rewiring_probability must be in [0, 1]")

    rng = random.Random(seed)
    graph = Graph()
    for i in range(1, node_count + 1):
        graph.add_node(Node(id=i))

    half = neighbors_per_node // 2
    edges_seen: set[tuple[int, int]] = set()
    for i in range(1, node_count + 1):
        for offset in range(1, half + 1):
            j = ((i - 1 + offset) % node_count) + 1
            key = (min(i, j), max(i, j))
            if key in edges_seen:
                continue
            edges_seen.add(key)
            graph.add_edge(Edge(source=i, target=j))

    if rewiring_probability == 0.0:
        return graph

    existing_edges = list(graph.edges())
    rng.shuffle(existing_edges)
    for edge in existing_edges:
        if rng.random() >= rewiring_probability:
            continue
        old_key = (
            min(edge.source, edge.target),
            max(edge.source, edge.target),
        )
        if old_key not in edges_seen:
            continue
        for _ in range(50):
            new_target = rng.randint(1, node_count)
            if new_target == edge.source:
                continue
            new_key = (
                min(edge.source, new_target),
                max(edge.source, new_target),
            )
            if new_key in edges_seen:
                continue
            graph.remove_edge(edge.source, edge.target)
            edges_seen.discard(old_key)
            edges_seen.add(new_key)
            graph.add_edge(Edge(source=edge.source, target=new_target))
            break
    return graph


def generate(request: GeneratorRequest) -> Graph:
    """Dispatch to the generator described by the request.

    Args:
        request: The generation parameters.

    Returns:
        The generated graph.

    Raises:
        ValueError: If the request is invalid or the kind is unknown.
    """
    if request.kind is GeneratorKind.ERDOS_RENYI:
        return generate_erdos_renyi(
            request.node_count, request.probability, request.seed
        )
    if request.kind is GeneratorKind.BARABASI_ALBERT:
        return generate_barabasi_albert(
            request.node_count, request.edges_per_new_node, request.seed
        )
    if request.kind is GeneratorKind.WATTS_STROGATZ:
        return generate_watts_strogatz(
            request.node_count,
            request.neighbors_per_node,
            request.rewiring_probability,
            request.seed,
        )
    raise ValueError(f"Unknown generator kind: {request.kind}")
