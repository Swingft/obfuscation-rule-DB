# learning/merge_rules.py

import yaml
from pathlib import Path
from typing import Dict, List
from config import Config


class RuleMerger:
    """규칙 파일 병합 및 중복 제거"""

    @staticmethod
    def load_rules(filepath: Path) -> List[Dict]:
        """YAML 규칙 로드"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("rules", [])

    @staticmethod
    def merge_rules(
            base_rules: List[Dict],
            new_rules: List[Dict],
            prefer_new: bool = False
    ) -> List[Dict]:
        """
        규칙 병합

        Args:
            base_rules: 기존 규칙
            new_rules: 새로운 규칙
            prefer_new: True면 중복 시 새 규칙 우선

        Returns:
            병합된 규칙
        """
        # ID로 인덱싱
        merged = {}

        # 기존 규칙 추가
        for rule in base_rules:
            rule_id = rule.get("id")
            if rule_id:
                merged[rule_id] = rule

        # 새 규칙 병합
        added = 0
        replaced = 0

        for rule in new_rules:
            rule_id = rule.get("id")
            if not rule_id:
                continue

            if rule_id in merged:
                if prefer_new:
                    merged[rule_id] = rule
                    replaced += 1
            else:
                merged[rule_id] = rule
                added += 1

        print(f"   📊 Merge Statistics:")
        print(f"      Base rules: {len(base_rules)}")
        print(f"      New rules: {len(new_rules)}")
        print(f"      Added: {added}")
        print(f"      Replaced: {replaced}")
        print(f"      Total: {len(merged)}")

        return list(merged.values())

    @staticmethod
    def remove_duplicates(rules: List[Dict]) -> List[Dict]:
        """중복 규칙 제거"""
        seen_ids = set()
        unique_rules = []
        duplicates = 0

        for rule in rules:
            rule_id = rule.get("id")
            if rule_id and rule_id not in seen_ids:
                seen_ids.add(rule_id)
                unique_rules.append(rule)
            else:
                duplicates += 1

        if duplicates > 0:
            print(f"   🔄 Removed {duplicates} duplicate rules")

        return unique_rules

    @staticmethod
    def sort_rules(rules: List[Dict]) -> List[Dict]:
        """규칙을 ID로 정렬"""
        return sorted(rules, key=lambda r: r.get("id", ""))

    @staticmethod
    def save_rules(rules: List[Dict], filepath: Path):
        """규칙을 YAML로 저장"""
        output = {"rules": rules}

        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(output, f, allow_unicode=True, sort_keys=False, width=120)

        print(f"💾 Saved {len(rules)} rules to {filepath}")


def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("🔗 Rule Merger")
    print("=" * 70)

    # 기존 규칙 경로
    base_path = Path("../rules/swift_exclusion_rules.yaml")

    if not base_path.exists():
        print(f"❌ Base rules not found: {base_path}")
        return

    # 새 규칙 경로 선택
    print("\nSelect new rules to merge:")
    print("  1. Generated rules (generated_rules.yaml)")
    print("  2. Custom path")

    choice = input("\nChoice (1-2): ").strip()

    if choice == "1":
        new_path = Config.DATA_DIR / "generated_rules.yaml"
    elif choice == "2":
        custom = input("Enter path: ").strip()
        new_path = Path(custom)
    else:
        print("❌ Invalid choice")
        return

    if not new_path.exists():
        print(f"❌ New rules not found: {new_path}")
        return

    # 규칙 로드
    print(f"\n📂 Loading rules...")
    print(f"   Base: {base_path}")
    print(f"   New:  {new_path}")

    merger = RuleMerger()
    base_rules = merger.load_rules(base_path)
    new_rules = merger.load_rules(new_path)

    print(f"\n✅ Loaded {len(base_rules)} base rules")
    print(f"✅ Loaded {len(new_rules)} new rules")

    # 병합 옵션
    print("\n🔀 Merge strategy:")
    print("  1. Add new rules only (keep existing on conflict)")
    print("  2. Replace on conflict (prefer new rules)")

    strategy = input("\nChoice (1-2): ").strip()
    prefer_new = (strategy == "2")

    # 병합
    print(f"\n🔨 Merging rules...")
    merged_rules = merger.merge_rules(base_rules, new_rules, prefer_new)

    # 중복 제거
    merged_rules = merger.remove_duplicates(merged_rules)

    # 정렬
    merged_rules = merger.sort_rules(merged_rules)

    # 저장
    output_path = Config.DATA_DIR / "merged_rules.yaml"
    merger.save_rules(merged_rules, output_path)

    print(f"\n✅ Merged rules saved to {output_path}")
    print(f"\n💡 To use these rules, copy them to:")
    print(f"   {base_path}")

    print("\n" + "=" * 70)
    print("🎉 Merge completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()