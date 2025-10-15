# 'from rule_engine...' 대신 상대 경로를 사용합니다.
from ..graph.graph_loader import SymbolGraph
from ..rules.rule_loader import RuleLoader
from ..rules.pattern_matcher import PatternMatcher

class AnalysisEngine:
    # 내용은 이전과 동일합니다.
    def __init__(self, graph: SymbolGraph, rules: RuleLoader):
        self.graph = graph
        self.rules = rules.rules
        self.matcher = PatternMatcher(self.graph)
        self.excluded_symbols = {}

    def run(self):
        # ... (이하 로직 동일) ...
        print("🚀 Starting exclusion analysis...")
        for i, rule in enumerate(self.rules):
            print(f"  - Running rule [{i+1}/{len(self.rules)}] \"{rule['id']}\"...")
            pattern = rule.get('pattern')
            if not pattern: continue
            matched_ids = self.matcher.match(pattern)
            print(f"    Found {len(matched_ids)} matching symbols.")
            for symbol_id in matched_ids:
                reason = {"rule_id": rule['id'], "description": rule['description']}
                if symbol_id not in self.excluded_symbols:
                    self.excluded_symbols[symbol_id] = []
                self.excluded_symbols[symbol_id].append(reason)
        print(f"✅ Analysis complete. Found {len(self.excluded_symbols)} symbols to exclude.")

    def get_results(self):
        # ... (이하 로직 동일) ...
        results = []
        for symbol_id, reasons in self.excluded_symbols.items():
            symbol_data = self.graph.get_node(symbol_id)
            if symbol_data:
                results.append({
                    "name": symbol_data.get("name"), "kind": symbol_data.get("kind"),
                    "location": symbol_data.get("location"), "reasons": reasons
                })
        return results