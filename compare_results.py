import argparse
from pathlib import Path
import sys


def read_identifiers_from_file(file_path: Path) -> set:
    """Reads a text file and returns a set of non-empty, stripped lines."""
    if not file_path.exists():
        print(f"❌ Error: File not found at '{file_path}'")
        sys.exit(1)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read lines, strip whitespace, and filter out any empty lines
            return {line.strip() for line in f if line.strip()}
    except Exception as e:
        print(f"❌ Error reading file '{file_path}': {e}")
        sys.exit(1)


def compare_files(rule_file_path: Path, my_file_path: Path):
    """Compares two files containing lists of identifiers and prints the difference."""

    print("=" * 60)
    print("🚀 Starting Comparison...")
    print(f"  -  RULE BASE : '{rule_file_path}'")
    print(f"  - MY RESULT   : '{my_file_path}'")
    print("=" * 60)

    # Read identifiers from both files into sets for efficient comparison
    rule_identifiers = read_identifiers_from_file(rule_file_path)
    my_identifiers = read_identifiers_from_file(my_file_path)

    # --- Perform Set Operations ---
    common_identifiers = sorted(list(rule_identifiers.intersection(my_identifiers)))
    missing_identifiers = sorted(list(rule_identifiers.difference(my_identifiers)))
    new_identifiers = sorted(list(my_identifiers.difference(rule_identifiers)))

    # --- Print Summary ---
    print("\n📊 COMPARISON SUMMARY\n" + "-" * 25)
    print(f"Rule Base Identifiers: {len(rule_identifiers)}")
    print(f"My Result Identifiers:   {len(my_identifiers)}")
    print("-" * 25)
    print(f"✅ Common Identifiers:    {len(common_identifiers)}")
    print(f"❌ Missing Identifiers:   {len(missing_identifiers)}")
    print(f"✨ New Identifiers Found: {len(new_identifiers)}")
    print("=" * 60)

    # --- Print Detailed Lists ---
    if missing_identifiers:
        print(f"\n❌ MISSING IDENTIFIERS ({len(missing_identifiers)} items not found by your engine)\n" + "-" * 50)
        for item in missing_identifiers:
            print(f"  - {item}")
    else:
        print("\n🎉 Excellent! No missing identifiers.")

    if new_identifiers:
        print(f"\n✨ NEW IDENTIFIERS ({len(new_identifiers)} items found ONLY by your engine)\n" + "-" * 50)
        for item in new_identifiers:
            print(f"  + {item}")

    if common_identifiers:
        print(f"\n✅ COMMON IDENTIFIERS ({len(common_identifiers)} items found by both)\n" + "-" * 50)
        for item in common_identifiers:
            print(f"  = {item}")

    print("\n🎉 Comparison finished successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare your analysis result with a rule-base answer key.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "rule_file",
        type=Path,
        help="Path to the rule-base .txt file (e.g., rule_output/uikit2_internal_name.txt)"
    )
    parser.add_argument(
        "my_file",
        type=Path,
        help="Path to your final exclusion .txt file (e.g., output/final_exclusion_list.txt)"
    )

    args = parser.parse_args()

    compare_files(args.rule_file, args.my_file)