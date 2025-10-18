# learning/rule_generator.py

import json
import yaml
from pathlib import Path
from typing import Dict, List
from config import Config


class RuleGenerator:
    """추출된 패턴으로부터 YAML 규칙 자동 생성"""

    def __init__(self):
        self.generated_rules = []

    def generate_from_patterns(self, patterns: Dict) -> List[Dict]:
        """
        패턴으로부터 규칙 생성

        Args:
            patterns: 추출된 패턴

        Returns:
            생성된 규칙 리스트
        """
        rules = []

        # 1. 자주 사용되는 프로퍼티 이름
        if patterns["property_names"]:
            property_names = [p["name"] for p in patterns["property_names"]]

            rules.append({
                "id": "LEARNED_COMMON_PROPERTY_NAMES",
                "description": f"학습된 범용 프로퍼티 이름 ({len(property_names)}개)",
                "pattern": [
                    {"find": {"target": "P"}},
                    {"where": [
                        "P.kind == 'property'",
                        f"P.name in {property_names}"
                    ]}
                ]
            })

        # 2. 자주 사용되는 메서드 이름
        if patterns["method_names"]:
            method_names = [m["name"] for m in patterns["method_names"]]

            rules.append({
                "id": "LEARNED_COMMON_METHOD_NAMES",
                "description": f"학습된 범용 메서드 이름 ({len(method_names)}개)",
                "pattern": [
                    {"find": {"target": "M"}},
                    {"where": [
                        "M.kind == 'method'",
                        f"M.name in {method_names}"
                    ]}
                ]
            })

        # 3. 클래스 이름 접미사 (ViewController, ViewModel 등)
        if patterns["class_suffixes"]:
            for suffix_info in patterns["class_suffixes"]:
                suffix = suffix_info["suffix"]

                rules.append({
                    "id": f"LEARNED_CLASS_SUFFIX_{suffix.upper()}",
                    "description": f"학습된 클래스 접미사: {suffix}",
                    "pattern": [
                        {"find": {"target": "S"}},
                        {"where": [
                            "S.kind in ['class', 'struct']",
                            f"S.name matches '{suffix}$'"
                        ]}
                    ]
                })

        # 4. 델리게이트 메서드
        if patterns["delegate_methods"]:
            delegate_methods = [d["name"] for d in patterns["delegate_methods"]]

            rules.append({
                "id": "LEARNED_DELEGATE_METHODS",
                "description": f"학습된 델리게이트 메서드 ({len(delegate_methods)}개)",
                "pattern": [
                    {"find": {"target": "M"}},
                    {"where": [
                        "M.kind == 'method'",
                        f"M.name in {delegate_methods}"
                    ]}
                ]
            })

        # 5. 프레임워크 특화 패턴
        for framework, framework_patterns in patterns["framework_patterns"].items():
            if framework_patterns:
                # 예: RxSwift의 경우
                if framework == "RxSwift":
                    rules.append({
                        "id": "LEARNED_RXSWIFT_PROPERTIES",
                        "description": "학습된 RxSwift 관련 프로퍼티",
                        "pattern": [
                            {"find": {"target": "P"}},
                            {"where": [
                                "P.kind == 'property'",
                                "P.name in ['disposeBag', 'observable', 'subject', 'relay']"
                            ]}
                        ]
                    })

        self.generated_rules = rules
        return rules

    def merge_with_existing_rules(
            self,
            generated_rules: List[Dict],
            existing_rules_path: Path
    ) -> List[Dict]:
        """
        기존 규칙과 병합

        Args:
            generated_rules: 생성된 규칙
            existing_rules_path: 기존 규칙 파일 경로

        Returns:
            병합된 규칙
        """
        print(f"🔗 Merging with existing rules from {existing_rules_path}")

        if not existing_rules_path.exists():
            print(f"   ⚠️  No existing rules found, using generated rules only")
            return generated_rules

        with open(existing_rules_path, "r", encoding="utf-8") as f:
            existing_data = yaml.safe_load(f)
            existing_rules = existing_data.get("rules", [])

        print(f"   📋 Existing rules: {len(existing_rules)}")
        print(f"   🆕 Generated rules: {len(generated_rules)}")

        # ID 중복 체크
        existing_ids = {rule["id"] for rule in existing_rules}
        new_rules = []
        duplicates = 0

        for rule in generated_rules:
            if rule["id"] not in existing_ids:
                new_rules.append(rule)
            else:
                duplicates += 1

        print(f"   ✨ New unique rules: {len(new_rules)}")
        print(f"   🔄 Duplicates skipped: {duplicates}")

        # 병합
        merged = existing_rules + new_rules
        print(f"   ✅ Total rules after merge: {len(merged)}")

        return merged

    def save_rules(self, rules: List[Dict], filename: str = "generated_rules.yaml"):
        """규칙을 YAML 파일로 저장"""
        output_path = Config.DATA_DIR / filename

        # YAML 형식으로 저장
        output = {"rules": rules}

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(output, f, allow_unicode=True, sort_keys=False, width=120)

        print(f"💾 Saved {len(rules)} rules to {output_path}")

        return output_path

    def generate_statistics(self, rules: List[Dict]) -> Dict:
        """규칙 통계 생성"""
        stats = {
            "total_rules": len(rules),
            "by_category": {},
            "by_target": {}
        }

        for rule in rules:
            # 카테고리별 (ID 접두사 기준)
            category = rule["id"].split("_")[0]
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

            # 타겟별 (find.target 기준)
            try:
                target = rule["pattern"][0]["find"]["target"]
                stats["by_target"][target] = stats["by_target"].get(target, 0) + 1
            except:
                pass

        return stats


def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("🤖 Automatic Rule Generator")
    print("=" * 70)

    # 패턴 로드
    patterns_file = Config.DATA_DIR / "patterns.json"
    if not patterns_file.exists():
        print("❌ No patterns.json found. Run pattern_extractor.py first.")
        return

    print(f"\n📂 Loading patterns from {patterns_file}")
    with open(patterns_file, "r", encoding="utf-8") as f:
        patterns = json.load(f)

    # 규칙 생성
    print("\n🔨 Generating rules...")
    generator = RuleGenerator()
    generated_rules = generator.generate_from_patterns(patterns)

    print(f"✅ Generated {len(generated_rules)} rules")

    # 통계
    stats = generator.generate_statistics(generated_rules)
    print(f"\n📊 Rule Statistics:")
    print(f"   Total: {stats['total_rules']}")
    print(f"   By Category:")
    for category, count in sorted(stats["by_category"].items(), key=lambda x: x[1], reverse=True):
        print(f"      {category}: {count}")

    # 저장
    output_path = generator.save_rules(generated_rules)

    # 기존 규칙과 병합 여부
    print(f"\n🔗 Merge with existing rules? (y/n): ", end="")
    choice = input().strip().lower()

    if choice == "y":
        existing_rules_path = Path("../rules/swift_exclusion_rules.yaml")

        if existing_rules_path.exists():
            merged_rules = generator.merge_with_existing_rules(
                generated_rules,
                existing_rules_path
            )

            # 병합된 규칙 저장
            merged_path = generator.save_rules(merged_rules, "merged_rules.yaml")
            print(f"\n✅ Merged rules saved to {merged_path}")
            print(f"   You can replace the original file with this merged version.")
        else:
            print(f"❌ Existing rules not found at {existing_rules_path}")

    print("\n" + "=" * 70)
    print("🎉 Rule generation completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()