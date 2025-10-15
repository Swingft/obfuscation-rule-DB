from typing import Set, Dict, Any, List
from ..graph.graph_loader import SymbolGraph


class PatternMatcher:
    """규칙의 패턴을 심볼 그래프에 매칭시킵니다."""

    def __init__(self, graph: SymbolGraph):
        self.graph = graph

    def match(self, pattern: List[Dict[str, Any]]) -> Set[str]:
        """주어진 패턴과 일치하는 모든 노드 ID를 찾습니다."""

        # 1. find 절 찾기
        find_clause = None
        where_clauses = []

        for item in pattern:
            if 'find' in item:
                find_clause = item['find']
            elif 'where' in item:
                where_clauses = item['where']

        if not find_clause:
            return set()

        target_variable = find_clause.get('target')
        if not target_variable:
            return set()

        # 2. 초기 후보 설정 (모든 노드)
        candidate_ids = set(self.graph.find_all_nodes())

        # 3. where 조건들을 순차적으로 적용
        for condition in where_clauses:
            candidate_ids = self._apply_single_condition(candidate_ids, condition)
            if not candidate_ids:
                break

        return candidate_ids

    def _apply_single_condition(self, current_ids: Set[str], condition: Any) -> Set[str]:
        """단일 조건을 적용"""

        # not_exists 처리
        if isinstance(condition, dict) and "not_exists" in condition:
            sub_conditions = condition["not_exists"]
            invalid_ids = self._match_not_exists(current_ids, sub_conditions)
            return current_ids - invalid_ids

        # 문자열 조건
        if isinstance(condition, str):
            # 엣지 조건인지 속성 조건인지 구분
            if '-->' in condition or '<--' in condition:
                return self._filter_by_edge(current_ids, condition)
            else:
                return self._filter_by_property(current_ids, condition)

        return current_ids

    def _filter_by_property(self, current_ids: Set[str], condition: str) -> Set[str]:
        """속성 조건으로 필터링: 'S_METHOD.kind == method'"""
        matching_ids = set()

        # 조건 파싱
        parts = condition.split()
        if len(parts) < 3:
            return matching_ids

        prop_path = parts[0]  # S_METHOD.kind
        operator = parts[1]  # ==, !=, in, contains, contains_any
        value_str = ' '.join(parts[2:])  # 'method' 또는 ['a', 'b']

        if '.' not in prop_path:
            return matching_ids

        _, prop_name = prop_path.split('.', 1)
        value = self._parse_value(value_str)

        # 각 노드 검사
        for node_id in current_ids:
            node_data = self.graph.get_node(node_id)
            if not node_data:
                continue

            prop_value = node_data.get(prop_name)
            if self._check_value(prop_value, operator, value):
                matching_ids.add(node_id)

        return matching_ids

    def _filter_by_edge(self, current_ids: Set[str], condition: str) -> Set[str]:
        """엣지 조건으로 필터링: 'S_METHOD --OVERRIDES--> PARENT_METHOD'"""
        matching_ids = set()

        # 방향 결정
        if '-->' in condition:
            direction = 'out'
            parts = condition.split('-->')
        else:  # '<--'
            direction = 'in'
            parts = condition.split('<--')

        if len(parts) != 2:
            return matching_ids

        left = parts[0].strip()
        right = parts[1].strip()

        # 엣지 타입 추출: 'VAR --TYPE' -> TYPE
        edge_type = None
        if left.count('--') > 0:
            left_parts = left.rsplit('--', 1)
            if len(left_parts) == 2:
                edge_type = left_parts[1].strip()

        if right.count('--') > 0:
            right_parts = right.split('--', 1)
            if len(right_parts) == 2 and not edge_type:
                edge_type = right_parts[0].strip()

        # 각 노드에서 해당 엣지가 있는지 확인
        for node_id in current_ids:
            neighbors = self.graph.get_neighbors(node_id, edge_type=edge_type, direction=direction)
            if neighbors:
                matching_ids.add(node_id)

        return matching_ids

    def _match_not_exists(self, candidate_ids: Set[str], sub_conditions: List) -> Set[str]:
        """not_exists 절: 조건을 만족하는 노드들을 찾아서 제외용으로 반환"""
        invalid_ids = set()

        for node_id in candidate_ids:
            temp_ids = {node_id}
            all_match = True

            for sub_cond in sub_conditions:
                temp_ids = self._apply_single_condition(temp_ids, sub_cond)
                if not temp_ids:
                    all_match = False
                    break

            if all_match and temp_ids:
                invalid_ids.add(node_id)

        return invalid_ids

    def _parse_value(self, value_str: str) -> Any:
        """문자열 값을 파싱"""
        value_str = value_str.strip()

        if (value_str.startswith('"') and value_str.endswith('"')) or \
                (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]

        if value_str.startswith('[') and value_str.endswith(']'):
            inner = value_str[1:-1]
            if not inner.strip(): return []
            return [self._parse_value(item) for item in inner.split(',')]

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
        """값 비교 (🔥 'contains' 연산자 추가)"""
        if prop_value is None:
            return operator == '!='

        if operator == '==':
            return prop_value == required_value
        if operator == '!=':
            return prop_value != required_value
        if operator == 'in':
            return isinstance(required_value, list) and prop_value in required_value

        # [수정] 문자열 포함 연산자 추가
        if operator == 'contains':
            return isinstance(prop_value, str) and isinstance(required_value, str) and required_value in prop_value

        if operator == 'contains_any':
            if isinstance(prop_value, list) and isinstance(required_value, list):
                return any(item in prop_value for item in required_value)
        return False