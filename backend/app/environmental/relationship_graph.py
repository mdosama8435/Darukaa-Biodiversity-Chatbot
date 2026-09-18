"""Environmental Relationship Graph indexing and multi-metric query engine."""

from typing import Dict, List, Optional, Set
from app.environmental.schemas import MetricRelationshipDefinition
from app.environmental.relationships import ENVIRONMENTAL_RELATIONSHIPS


class EnvironmentalRelationshipGraph:
    """Graph structure indexing environmental relationships across multi-variable dimensions."""

    def __init__(self, registry: Optional[Dict[str, MetricRelationshipDefinition]] = None) -> None:
        self.registry = registry or ENVIRONMENTAL_RELATIONSHIPS
        self._variable_index: Dict[str, Set[str]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Indexes relationships by their constituent environmental variables."""
        self._variable_index.clear()
        for rel_id, rel in self.registry.items():
            for var in rel.variables:
                var_key = var.lower().strip()
                if var_key not in self._variable_index:
                    self._variable_index[var_key] = set()
                self._variable_index[var_key].add(rel_id)

    def get_relationship(self, relationship_id: str) -> Optional[MetricRelationshipDefinition]:
        """Fetches a relationship by unique ID."""
        return self.registry.get(relationship_id)

    def find_relationships_for_variables(
        self,
        variables: List[str],
        require_all_variables: bool = False,
        min_matching_variables: int = 1,
    ) -> List[MetricRelationshipDefinition]:
        """Finds relationships matching a set of present environmental variables.
        
        Args:
            variables: List of observed variable keys (e.g. ['soil_organic_carbon', 'rainfall'])
            require_all_variables: If True, only returns relationships where ALL relationship variables are present.
            min_matching_variables: Minimum number of variables from the relationship that must be present.
        """
        clean_vars = set(v.lower().strip() for v in variables if v)
        matched_rels: List[MetricRelationshipDefinition] = []

        for rel in self.registry.values():
            rel_vars = set(v.lower().strip() for v in rel.variables)
            intersection = clean_vars.intersection(rel_vars)

            if require_all_variables:
                if rel_vars.issubset(clean_vars):
                    matched_rels.append(rel)
            else:
                if len(intersection) >= min_matching_variables:
                    matched_rels.append(rel)

        return matched_rels

    def find_multi_metric_relationships(
        self,
        variables: List[str],
        min_variables: int = 3,
    ) -> List[MetricRelationshipDefinition]:
        """Finds compound relationships involving at least `min_variables` simultaneously."""
        clean_vars = set(v.lower().strip() for v in variables if v)
        multi_metric_rels: List[MetricRelationshipDefinition] = []

        for rel in self.registry.values():
            rel_vars = set(v.lower().strip() for v in rel.variables)
            if len(rel_vars) >= min_variables:
                # Count how many of the relationship's variables are present in the observation
                intersection = clean_vars.intersection(rel_vars)
                if len(intersection) >= 2:  # At least 2 observed out of >=3
                    multi_metric_rels.append(rel)

        return multi_metric_rels

    def all_relationships(self) -> List[MetricRelationshipDefinition]:
        """Returns all registered relationships."""
        return list(self.registry.values())


_GRAPH_INSTANCE: Optional[EnvironmentalRelationshipGraph] = None


def get_relationship_graph() -> EnvironmentalRelationshipGraph:
    """Singleton getter for the EnvironmentalRelationshipGraph."""
    global _GRAPH_INSTANCE
    if _GRAPH_INSTANCE is None:
        _GRAPH_INSTANCE = EnvironmentalRelationshipGraph()
    return _GRAPH_INSTANCE
