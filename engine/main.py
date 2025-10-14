import argparse
import sys

from rule_engine.graph.graph_loader import SymbolGraph
from rule_engine.rules.rule_loader import RuleLoader
from rule_engine.core.analysis_engine import AnalysisEngine
from rule_engine.reporting.report_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description="Obfuscation Rule-DB Analysis Engine")
    parser.add_argument("symbol_graph_json", help="Path to the symbol_graph.json file.")
    parser.add_argument("--rules", default="../rules/swift_exclusion_rules.yaml", help="Path to the rules YAML file.")
    parser.add_argument("--output", default="../output/exclusion_list.json", help="Path for the output exclusion list JSON file.")
    args = parser.parse_args()

    print(f"📂 Loading symbol graph from: {args.symbol_graph_json}")
    try:
        graph = SymbolGraph(args.symbol_graph_json)
    except FileNotFoundError:
        print(f"❌ Error: Symbol graph file not found at '{args.symbol_graph_json}'", file=sys.stderr)
        sys.exit(1)
    print(f"  - Loaded {len(graph.graph.nodes)} symbols and {len(graph.graph.edges)} relationships.")

    print(f"📚 Loading rules from: {args.rules}")
    rules = RuleLoader(args.rules)
    print(f"  - Loaded {len(rules.rules)} rules.")

    engine = AnalysisEngine(graph, rules)
    engine.run()

    results = engine.get_results()
    reporter = ReportGenerator()
    reporter.generate_json(results, args.output)
    reporter.print_summary(results, graph)

    print("\n🎉 Analysis finished successfully!")


if __name__ == '__main__':
    main()