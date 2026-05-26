"""Code dependency graph analysis for GitHub repositories."""

from dependency_graph.builder import build_dependency_graph
from dependency_graph.impact import build_change_impact

__all__ = ["build_dependency_graph", "build_change_impact"]
