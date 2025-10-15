from typing import Set, Dict, Any, List
from ..graph.graph_loader import SymbolGraph


class PatternMatcher:
    """규칙의 패턴을 심볼 그래프에 매칭시킵니다. (🔥 상속 계층 전체 탐색 기능 추가)"""

    def __init__(self, graph: SymbolGraph):
        self.graph = graph
        self.path_map = {
            'parent': {'direction': 'in', 'type': 'CONTAINS'},
            'child': {'direction': 'out', 'type': 'CONTAINS'},
            'superclass': {'direction': 'out', 'type': ['INHERITS_FROM', 'CONFORMS_TO']},
        }

    def match(self, pattern: List[Dict[str, Any]]) -> Set[str]:
        find_clause = next((item['find'] for item in pattern if 'find' in item), None)
        where_clauses = next((item['where'] for item in pattern if 'where' in item), [])
        if not find_clause or not find_clause.get('target'): return set()

        candidate_ids = set(self.graph.find_all_nodes())
        for condition in where_clauses:
            candidate_ids = self._apply_single_condition(candidate_ids, condition)
            if not candidate_ids: break
        return candidate_ids

    def _apply_single_condition(self, current_ids: Set[str], condition: Any) -> Set[str]:
        if isinstance(condition, dict) and "not_exists" in condition:
            invalid_ids = self._match_not_exists(current_ids, condition["not_exists"])
            return current_ids - invalid_ids
        if isinstance(condition, str):
            if '-->' in condition or '<--' in condition:
                return self._filter_by_edge(current_ids, condition)
            else:
                return self._filter_by_property(current_ids, condition)
        return current_ids

    def _filter_by_property(self, current_ids: Set[str], condition: str) -> Set[str]:
        matching_ids = set()
        parts = condition.split()
        if len(parts) < 3: return matching_ids

        prop_path_str, operator, value_str = parts[0], parts[1], ' '.join(parts[2:])
        value = self._parse_value(value_str)

        path_components = prop_path_str.split('.')
        if len(path_components) < 2: return matching_ids

        _ = path_components.pop(0)
        target_prop = path_components.pop()
        traversal_path = path_components

        for node_id in current_ids:
            nodes_to_check_ids = {node_id}

            for path_key in traversal_path:
                if path_key not in self.path_map:
                    nodes_to_check_ids = set()
                    break

                next_nodes_ids = set()
                path_info = self.path_map[path_key]
                edge_types = path_info['type'] if isinstance(path_info['type'], list) else [path_info['type']]

                if path_key == 'superclass':
                    q = list(nodes_to_check_ids)
                    visited_ids = set(q)
                    while q:
                        current_id = q.pop(0)
                        for etype in edge_types:
                            neighbors = self.graph.get_neighbors(current_id, edge_type=etype,
                                                                 direction=path_info['direction'])
                            for nid in neighbors:
                                if nid not in visited_ids:
                                    visited_ids.add(nid)
                                    q.append(nid)
                    next_nodes_ids = visited_ids
                else:  # parent, child
                    for current_id in nodes_to_check_ids:
                        for etype in edge_types:
                            neighbors = self.graph.get_neighbors(current_id, edge_type=etype,
                                                                 direction=path_info['direction'])
                            next_nodes_ids.update(neighbors)

                nodes_to_check_ids = next_nodes_ids

            for final_id in nodes_to_check_ids:
                final_node = self.graph.get_node(final_id)
                if not final_node: continue

                prop_value = final_node.get(target_prop)
                if self._check_value(prop_value, operator, value):
                    matching_ids.add(node_id)
                    break
        return matching_ids

    def _filter_by_edge(self, current_ids: Set[str], condition: str) -> Set[str]:
        matching_ids = set()
        direction, edge_type = 'out', None
        if '-->' in condition:
            parts = condition.split('-->')
        elif '<--' in condition:
            direction, parts = 'in', condition.split('<--')
        else:
            return matching_ids
        left, right = parts[0].strip(), parts[1].strip()
        if '--' in left: edge_type = left.rsplit('--', 1)[1].strip()
        if '--' in right and not edge_type: edge_type = right.split('--', 1)[0].strip()
        for node_id in current_ids:
            if self.graph.get_neighbors(node_id, edge_type=edge_type, direction=direction):
                matching_ids.add(node_id)
        return matching_ids

    def _match_not_exists(self, candidate_ids: Set[str], sub_conditions: List) -> Set[str]:
        invalid_ids = set()
        for node_id in candidate_ids:
            temp_ids = {node_id}
            all_match = True
            for sub_cond in sub_conditions:
                temp_ids = self._apply_single_condition(temp_ids, sub_cond)
                if not temp_ids:
                    all_match = False
                    break
            if all_match and temp_ids: invalid_ids.add(node_id)
        return invalid_ids

    def _parse_value(self, value_str: str) -> Any:
        value_str = value_str.strip()
        if (value_str.startswith('"') and value_str.endswith('"')) or \
                (value_str.startswith("'") and value_str.endswith("'")): return value_str[1:-1]
        if value_str.startswith('[') and value_str.endswith(']'):
            inner = value_str[1:-1].strip()
            return [self._parse_value(item) for item in inner.split(',')] if inner else []
        if value_str.lower() == 'true': return True
        if value_str.lower() == 'false': return False
        try:
            return int(value_str)
        except ValueError:
            try:
                return float(value_str)
            except ValueError:
                return value_str

    def _check_value(self, prop_value: Any, operator: str, required_value: Any) -> bool:
        if prop_value is None: return operator == '!='
        if operator == '==': return prop_value == required_value
        if operator == '!=': return prop_value != required_value
        if operator == 'in': return isinstance(required_value, list) and prop_value in required_value
        if operator == 'contains': return isinstance(prop_value, str) and isinstance(required_value,
                                                                                     str) and required_value in prop_value
        if operator == 'contains_any':
            if isinstance(prop_value, list) and isinstance(required_value, list):
                return any(item in prop_value for item in required_value)
        if operator == 'starts_with':
            return isinstance(prop_value, str) and prop_value.startswith(required_value)
        return False