"""Graph statistics computed over the undirected view of a graph."""

from collections import deque
from dataclasses import dataclass

from domain.entities.graph import Graph

DEFAULT_MAX_NODES_FOR_PATHS = 50


@dataclass(frozen=True)
class GraphStatistics:
    """Summary statistics for a graph.

    All connectivity-based metrics treat the graph as undirected:
    directed edges contribute in both directions. Self-loops are
    excluded from density, average degree, connectivity, and path
    metrics because they do not change any of those measurements.
    They are still included in the reported edge count, which matches
    the value shown in the status bar.

    Args:
        node_count: Number of nodes.
        edge_count: Number of edges, including self-loops.
        density: Non-loop edges divided by the maximum possible
            undirected edges. Values above 1 indicate a multigraph.
        average_degree: Twice the non-loop edge count divided by the
            node count.
        component_count: Number of weakly connected components.
        diameter: Longest shortest-path distance, or None when the
            graph is disconnected or larger than the configured
            threshold.
        average_path_length: Mean shortest-path distance over all
            reachable ordered pairs, or None under the same
            conditions.
    """

    node_count: int
    edge_count: int
    density: float
    average_degree: float
    component_count: int
    diameter: int | None
    average_path_length: float | None


def compute_statistics(
    graph: Graph,
    *,
    max_nodes_for_paths: int = DEFAULT_MAX_NODES_FOR_PATHS,
) -> GraphStatistics:
    """Compute summary statistics for the given graph.

    The path metrics (diameter and average path length) are only
    computed when the graph is connected and has at most
    ``max_nodes_for_paths`` nodes. Beyond that the all-pairs BFS is
    too expensive for interactive use, so the two values are None.

    Args:
        graph: The graph to analyse.
        max_nodes_for_paths: Upper bound on the node count for which
            diameter and average path length are computed.

    Returns:
        A GraphStatistics instance with every available metric.
    """
    nodes = [node.id for node in graph.nodes()]
    node_count = len(nodes)
    adjacency: dict[int, list[int]] = {nid: [] for nid in nodes}
    non_loop_edge_count = 0
    for edge in graph.edges():
        if edge.source == edge.target:
            continue
        non_loop_edge_count += 1
        adjacency[edge.source].append(edge.target)
        adjacency[edge.target].append(edge.source)

    if node_count == 0:
        return GraphStatistics(
            node_count=0,
            edge_count=graph.edge_count,
            density=0.0,
            average_degree=0.0,
            component_count=0,
            diameter=None,
            average_path_length=None,
        )

    max_possible_edges = node_count * (node_count - 1) / 2
    density = (
        non_loop_edge_count / max_possible_edges if max_possible_edges > 0 else 0.0
    )
    average_degree = 2 * non_loop_edge_count / node_count

    component_count = 0
    visited: set[int] = set()
    for start in nodes:
        if start in visited:
            continue
        component_count += 1
        queue: deque[int] = deque([start])
        visited.add(start)
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

    diameter: int | None = None
    average_path_length: float | None = None
    if node_count == 1:
        diameter = 0
        average_path_length = 0.0
    elif component_count == 1 and node_count <= max_nodes_for_paths:
        total_distance = 0
        total_pairs = 0
        max_distance = 0
        for start in nodes:
            distances: dict[int, int] = {start: 0}
            bfs: deque[int] = deque([start])
            while bfs:
                current = bfs.popleft()
                for neighbor in adjacency[current]:
                    if neighbor not in distances:
                        distances[neighbor] = distances[current] + 1
                        bfs.append(neighbor)
            for target, dist in distances.items():
                if target == start:
                    continue
                total_distance += dist
                total_pairs += 1
                max_distance = max(max_distance, dist)
        if total_pairs > 0:
            diameter = max_distance
            average_path_length = total_distance / total_pairs

    return GraphStatistics(
        node_count=node_count,
        edge_count=graph.edge_count,
        density=density,
        average_degree=average_degree,
        component_count=component_count,
        diameter=diameter,
        average_path_length=average_path_length,
    )
