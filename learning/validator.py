# learning/validator.py

import json
import yaml
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from config import Config

# python-engine 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "python-engine"))

try:
    from rule_engine.graph.graph_loader import SymbolGraph
    from rule_engine.rules.rule_loader import RuleLoader
    from rule_engine.rules.pattern_matcher import PatternMatcher
except ImportError as e:
    print(f"❌ Failed to import rule_engine modules: {e}")
    print(f"   Make sure python-engine directory exists in the project root")
    sys.exit(1)


class RuleValidator:
    """생성된 규칙 검증"""

    def __init__(self):
        self.validation_results = []

    def validate_against_benchmark(
            self,
            rules_path: Path,
            benchmark_dir: Path
    ) -> Dict:
        """벤치마크 프로젝트로 규칙 검증"""
        print(f"🧪 Validating rules against benchmark projects...")
        print(f"   Rules: {rules_path}")
        print(f"   Benchmark: {benchmark_dir}")

        benchmark_projects = {
            "life": {
                "symbol_graph": Path("../output/test_project4_Life-Progress-iOS_results/symbol_graph.json"),
                "ground_truth": benchmark_dir / "life.txt"
            },
            "social": {
                "symbol_graph": Path("../output/test_project7_social-distancing-ios_results/symbol_graph.json"),
                "ground_truth": benchmark_dir / "social.txt"
            },
            "uikit1": {
                "symbol_graph": Path("../output/test_project8_UIKit+SPM_1_results/symbol_graph.json"),
                "ground_truth": benchmark_dir / "uikit1.txt"
            },
            "uikit2": {
                "symbol_graph": Path("../output/test_project9_UIKit+SPM_2_results/symbol_graph.json"),
                "ground_truth": benchmark_dir / "uikit2.txt"
            }
        }

        results = {}

        for project_name, paths in benchmark_projects.items():
            if not paths["symbol_graph"].exists() or not paths["ground_truth"].exists():
                print(f"   ⚠️  {project_name}: Files not found, skipping")
                continue

            print(f"\n   📊 Testing: {project_name}")

            result = self._validate_single_project(
                rules_path,
                paths["symbol_graph"],
                paths["ground_truth"]
            )

            if result:
                results[project_name] = result
                print(f"      Accuracy: {result['accuracy']:.2%}")
                print(f"      Precision: {result['precision']:.2%}")
                print(f"      Recall: {result['recall']:.2%}")
                print(f"      F1 Score: {result['f1_score']:.2%}")

        # 전체 통계
        if results:
            avg_accuracy = sum(r["accuracy"] for r in results.values()) / len(results)
            avg_precision = sum(r["precision"] for r in results.values()) / len(results)
            avg_recall = sum(r["recall"] for r in results.values()) / len(results)
            avg_f1 = sum(r["f1_score"] for r in results.values()) / len(results)

            summary = {
                "projects": results,
                "average": {
                    "accuracy": avg_accuracy,
                    "precision": avg_precision,
                    "recall": avg_recall,
                    "f1_score": avg_f1
                }
            }

            print(f"\n   📈 Average Results:")
            print(f"      Accuracy:  {avg_accuracy:.2%}")
            print(f"      Precision: {avg_precision:.2%}")
            print(f"      Recall:    {avg_recall:.2%}")
            print(f"      F1 Score:  {avg_f1:.2%}")

            return summary

        return {}

    def _validate_single_project(
            self,
            rules_path: Path,
            symbol_graph_path: Path,
            ground_truth_path: Path
    ) -> Dict:
        """단일 프로젝트 검증"""

        try:
            # ✅ 심볼 그래프 로드
            symbol_graph = SymbolGraph(str(symbol_graph_path))

            # ✅ 규칙 로드 (RuleLoader의 올바른 사용법)
            rule_loader = RuleLoader(str(rules_path))
            rules = rule_loader.rules  # ← load_rules() 대신 .rules 속성 사용

            # ✅ 패턴 매칭
            # [수정 1] 생성자에는 symbol_graph만 전달합니다.
            matcher = PatternMatcher(symbol_graph)
            # [수정 2] find_matches 메서드에 rules를 인자로 전달합니다.
            excluded_node_ids = matcher.find_matches(rules)

            # ✅ 노드 ID를 심볼 이름으로 변환
            predicted = set()
            for node_id in excluded_node_ids:
                node_data = symbol_graph.get_node(node_id)
                if node_data:
                    predicted.add(node_data.get('name', node_id))

            # 정답 로드
            with open(ground_truth_path, "r", encoding="utf-8") as f:
                ground_truth = {line.strip() for line in f if line.strip()}

            # 전체 심볼 수
            total_symbols = len(symbol_graph.find_all_nodes())

            # 메트릭 계산
            true_positive = len(predicted & ground_truth)
            false_positive = len(predicted - ground_truth)
            false_negative = len(ground_truth - predicted)
            true_negative = total_symbols - true_positive - false_positive - false_negative

            accuracy = (true_positive + true_negative) / total_symbols if total_symbols > 0 else 0
            precision = true_positive / len(predicted) if len(predicted) > 0 else 0
            recall = true_positive / len(ground_truth) if len(ground_truth) > 0 else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            return {
                "total_symbols": total_symbols,
                "ground_truth_count": len(ground_truth),
                "predicted_count": len(predicted),
                "true_positive": true_positive,
                "false_positive": false_positive,
                "false_negative": false_negative,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "missing_identifiers": list(ground_truth - predicted)[:10]
            }

        except Exception as e:
            print(f"      ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def check_quality_threshold(self, results: Dict) -> Tuple[bool, str]:
        """품질 기준 체크"""
        avg = results.get("average", {})

        checks = []

        # 정확도 체크
        if avg.get("accuracy", 0) < Config.MIN_ACCURACY:
            checks.append(f"❌ Accuracy {avg['accuracy']:.2%} < {Config.MIN_ACCURACY:.2%}")
        else:
            checks.append(f"✅ Accuracy {avg['accuracy']:.2%} >= {Config.MIN_ACCURACY:.2%}")

        # 재현율 체크
        if avg.get("recall", 0) < 0.90:
            checks.append(f"⚠️  Recall {avg['recall']:.2%} < 90%")
        else:
            checks.append(f"✅ Recall {avg['recall']:.2%} >= 90%")

        # F1 Score 체크
        if avg.get("f1_score", 0) < 0.85:
            checks.append(f"⚠️  F1 Score {avg['f1_score']:.2%} < 85%")
        else:
            checks.append(f"✅ F1 Score {avg['f1_score']:.2%} >= 85%")

        passed = avg.get("accuracy", 0) >= Config.MIN_ACCURACY
        message = "\n".join(checks)

        return passed, message

    def save_validation_report(self, results: Dict, filename: str = "validation_report.json"):
        """검증 결과 저장"""
        output_path = Config.DATA_DIR / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Validation report saved to {output_path}")


def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("🧪 Rule Validator")
    print("=" * 70)

    # 검증할 규칙 파일 선택
    print("\nSelect rules to validate:")
    print("  1. Generated rules (generated_rules.yaml)")
    print("  2. Merged rules (merged_rules.yaml)")
    print("  3. Custom path")

    choice = input("\nChoice (1-3): ").strip()

    if choice == "1":
        rules_path = Config.DATA_DIR / "generated_rules.yaml"
    elif choice == "2":
        rules_path = Config.DATA_DIR / "merged_rules.yaml"
    elif choice == "3":
        custom_path = input("Enter path: ").strip()
        rules_path = Path(custom_path)
    else:
        print("❌ Invalid choice")
        return

    if not rules_path.exists():
        print(f"❌ Rules file not found: {rules_path}")
        return

    # 벤치마크 디렉토리
    benchmark_dir = Path("../rule_base")
    if not benchmark_dir.exists():
        print(f"❌ Benchmark directory not found: {benchmark_dir}")
        return

    # 검증 실행
    validator = RuleValidator()
    results = validator.validate_against_benchmark(rules_path, benchmark_dir)

    if not results:
        print("\n❌ No validation results")
        return

    # 품질 기준 체크
    print("\n" + "=" * 70)
    print("📋 Quality Check")
    print("=" * 70)

    passed, message = validator.check_quality_threshold(results)
    print("\n" + message)

    if passed:
        print("\n✅ Rules PASSED quality threshold!")
    else:
        print("\n⚠️  Rules need improvement")
        print("   Consider adjusting the rules or collecting more training data")

    # 결과 저장
    validator.save_validation_report(results)

    print("\n" + "=" * 70)
    print("🎉 Validation completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()