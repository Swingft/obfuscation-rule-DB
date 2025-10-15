import argparse
import sys
from pathlib import Path

# rule_engine을 패키지로 인식하도록 경로 추가
sys.path.append(str(Path(__file__).parent.resolve()))

from rule_engine.graph.graph_loader import SymbolGraph
from rule_engine.rules.rule_loader import RuleLoader
from rule_engine.core.analysis_engine import AnalysisEngine
from rule_engine.reporting.report_generator import ReportGenerator


def main():
    # 프로젝트 구조에 맞게 경로 기본값 현실화
    parser = argparse.ArgumentParser(description="Swift Obfuscation Rule-DB Analysis Engine")
    parser.add_argument("symbol_graph_json", help="Path to the symbol_graph.json file.")
    parser.add_argument("--rules", default="../rules/swift_exclusion_rules.yaml", help="Path to the rules YAML file.")
    parser.add_argument("--output", default="../output/final_exclusion_list.json",
                        help="Path for the output exclusion list JSON file.")
    # [추가] TXT 파일 출력을 위한 새로운 인자
    parser.add_argument("--txt-output", default="../output/final_exclusion_list.txt",
                        help="Path for the output exclusion name list TXT file.")
    args = parser.parse_args()

    print(f"📂 Loading symbol graph from: {args.symbol_graph_json}")
    try:
        graph = SymbolGraph(args.symbol_graph_json)
    except FileNotFoundError:
        print(f"❌ Error: Symbol graph file not found at '{args.symbol_graph_json}'", file=sys.stderr)
        sys.exit(1)
    print(f"  - Loaded {len(graph.graph.nodes)} symbols and {len(graph.graph.edges)} relationships.")

    print(f"\n📚 Loading rules from: {args.rules}")
    rules = RuleLoader(args.rules)
    if not rules.rules:
        print("❌ Error: No rules were loaded. Exiting.", file=sys.stderr)
        sys.exit(1)
    print(f"  - Loaded {len(rules.rules)} rules.")

    engine = AnalysisEngine(graph, rules)
    engine.run()

    results = engine.get_results()
    reporter = ReportGenerator()

    print("\n" + "=" * 50)
    print("💾 SAVING RESULTS")
    print("=" * 50)
    reporter.generate_json(results, args.output)
    # [추가] 새로운 TXT 생성 함수 호출
    reporter.generate_txt(results, args.txt_output)

    reporter.print_summary(results, graph)

    print("\n🎉 Analysis finished successfully!")


if __name__ == '__main__':
    main()