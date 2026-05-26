"""Repository intelligence: collect GitHub data and produce structured insights."""

from intelligence.analyzer import analyze_snapshot
from intelligence.collector import collect_repository_snapshot

__all__ = ["collect_repository_snapshot", "analyze_snapshot"]
