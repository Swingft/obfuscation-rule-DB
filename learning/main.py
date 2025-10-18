# learning/main.py

import sys
from pathlib import Path
from config import Config
import github_crawler
import pattern_extractor
import rule_generator
import validator
import merge_rules


def print_menu():
    """메뉴 출력"""
    print("\n" + "=" * 70)
    print("🤖 Automatic Rule Learning System")
    print("=" * 70)
    print("\n📋 Menu:")
    print("  1. Crawl GitHub projects")
    print("  2. Extract patterns from projects")
    print("  3. Generate rules from patterns")
    print("  4. Validate generated rules")
    print("  5. Merge rules with existing")
    print("  6. Run full pipeline (1 → 2 → 3 → 4)")
    print("  0. Exit")
    print("=" * 70)


def run_full_pipeline():
    """전체 파이프라인 실행"""
    print("\n" + "=" * 70)
    print("🚀 Running Full Learning Pipeline")
    print("=" * 70)

    # 1. Crawl
    print("\n[1/4] 📥 Crawling GitHub projects...")
    crawler = github_crawler.GitHubCrawler()
    projects = crawler.search_repositories(
        language=Config.LANGUAGE,
        min_stars=Config.MIN_STARS,
        max_results=Config.MAX_PROJECTS
    )

    # 의존성 확인
    print("\n📦 Checking dependencies...")
    for project in projects:
        deps = crawler.get_repository_dependencies(
            project["owner"],
            project["name"]
        )
        project["dependencies"] = deps

    crawler.save_projects(projects)

    # 다운로드
    print("\n📥 Downloading projects...")
    for i, project in enumerate(projects, 1):
        print(f"\n[{i}/{len(projects)}]")
        path = crawler.download_repository(project)
        if path:
            project["local_path"] = str(path)

    crawler.save_projects(projects)

    # 2. Extract patterns
    print("\n[2/4] 🔍 Extracting patterns...")
    extractor = pattern_extractor.PatternExtractor()

    downloaded_projects = [p for p in projects if "local_path" in p]

    for i, project in enumerate(downloaded_projects, 1):
        print(f"\n[{i}/{len(downloaded_projects)}]")
        project_path = Path(project["local_path"])
        dependencies = project.get("dependencies", [])

        if project_path.exists():
            extractor.analyze_project(project_path, dependencies)

    frequent_patterns = extractor.get_frequent_patterns(
        min_frequency=Config.MIN_FREQUENCY,
        min_occurrences=Config.MIN_OCCURRENCES
    )

    extractor.save_patterns(frequent_patterns)

    report = extractor.generate_report(frequent_patterns)
    print("\n" + report)

    # 3. Generate rules
    print("\n[3/4] 🤖 Generating rules...")
    generator = rule_generator.RuleGenerator()
    generated_rules = generator.generate_from_patterns(frequent_patterns)

    generator.save_rules(generated_rules)

    stats = generator.generate_statistics(generated_rules)
    print(f"\n📊 Generated {stats['total_rules']} rules")

    # 4. Validate
    print("\n[4/4] 🧪 Validating rules...")
    val = validator.RuleValidator()

    rules_path = Config.DATA_DIR / "generated_rules.yaml"
    benchmark_dir = Path("../rule_base")

    if rules_path.exists() and benchmark_dir.exists():
        results = val.validate_against_benchmark(rules_path, benchmark_dir)

        if results:
            passed, message = val.check_quality_threshold(results)
            print("\n" + "=" * 70)
            print("📋 Quality Check")
            print("=" * 70)
            print("\n" + message)

            if passed:
                print("\n✅ Rules PASSED quality threshold!")
            else:
                print("\n❌ Rules FAILED quality threshold")

            val.save_validation_report(results)

    print("\n" + "=" * 70)
    print("🎉 Full pipeline completed!")
    print("=" * 70)


def main():
    """메인 함수"""
    Config.ensure_dirs()

    while True:
        print_menu()

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            github_crawler.main()
        elif choice == "2":
            pattern_extractor.main()
        elif choice == "3":
            rule_generator.main()
        elif choice == "4":
            validator.main()
        elif choice == "5":
            merge_rules.main()
        elif choice == "6":
            run_full_pipeline()
        elif choice == "0":
            print("\n👋 Goodbye!")
            break
        else:
            print("\n❌ Invalid option. Please try again.")

        input("\n⏎ Press Enter to continue...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)