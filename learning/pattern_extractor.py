# learning/pattern_extractor.py

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import Counter, defaultdict
from config import Config


class PatternExtractor:
    """다운로드된 프로젝트에서 패턴 추출"""

    def __init__(self):
        self.patterns = {
            "property_names": Counter(),
            "method_names": Counter(),
            "class_names": Counter(),
            "protocol_names": Counter(),
            "delegate_methods": Counter(),
            "framework_patterns": defaultdict(lambda: defaultdict(Counter)),
            "architecture_patterns": Counter()
        }
        self.total_projects = 0

    def analyze_project(self, project_path: Path, dependencies: List[str] = None):
        """
        프로젝트 분석

        Args:
            project_path: 프로젝트 경로
            dependencies: 의존하는 프레임워크 목록
        """
        print(f"   📊 Analyzing: {project_path.name}")

        swift_files = list(project_path.rglob("*.swift"))

        if not swift_files:
            print(f"      ⚠️  No Swift files found")
            return

        print(f"      Found {len(swift_files)} Swift files")

        for swift_file in swift_files:
            try:
                content = swift_file.read_text(encoding="utf-8")
                self._extract_patterns_from_file(content, dependencies)
            except Exception as e:
                continue

        self.total_projects += 1

    def _extract_patterns_from_file(self, content: str, dependencies: List[str] = None):
        """파일에서 패턴 추출"""

        # 1. 프로퍼티 이름
        property_pattern = r'(?:var|let)\s+(\w+)\s*:'
        for match in re.finditer(property_pattern, content):
            name = match.group(1)
            if not name.startswith("_"):  # private 제외
                self.patterns["property_names"][name] += 1

        # 2. 메서드 이름
        method_pattern = r'func\s+(\w+)\s*\('
        for match in re.finditer(method_pattern, content):
            name = match.group(1)
            self.patterns["method_names"][name] += 1

        # 3. 클래스/구조체 이름
        class_pattern = r'(?:class|struct|enum)\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            name = match.group(1)
            self.patterns["class_names"][name] += 1

            # 아키텍처 패턴 감지
            if "ViewController" in name:
                self.patterns["architecture_patterns"]["ViewController"] += 1
            if "ViewModel" in name:
                self.patterns["architecture_patterns"]["ViewModel"] += 1
            if "Coordinator" in name:
                self.patterns["architecture_patterns"]["Coordinator"] += 1
            if name.endswith("Cell"):
                self.patterns["architecture_patterns"]["Cell"] += 1

        # 4. 프로토콜 이름
        protocol_pattern = r'protocol\s+(\w+)'
        for match in re.finditer(protocol_pattern, content):
            name = match.group(1)
            self.patterns["protocol_names"][name] += 1

        # 5. 델리게이트 메서드 (특정 패턴)
        delegate_patterns = [
            r'func\s+(tableView|collectionView|scrollView)\w*\(',
            r'func\s+(did|will|should)\w*\(',
            r'func\s+\w*(DidSelect|WillDisplay|DidEnd)\w*\('
        ]

        for pattern in delegate_patterns:
            for match in re.finditer(pattern, content):
                full_match = match.group(0)
                method_name = re.search(r'func\s+(\w+)', full_match).group(1)
                self.patterns["delegate_methods"][method_name] += 1

        # 6. 프레임워크 특화 패턴
        if dependencies:
            for framework in dependencies:
                if framework in content:
                    # RxSwift
                    if framework == "RxSwift":
                        rx_patterns = [
                            r'\.bind\(to:',
                            r'\.subscribe\(',
                            r'Observable\.',
                            r'disposeBag'
                        ]
                        for pattern in rx_patterns:
                            count = len(re.findall(pattern, content))
                            if count > 0:
                                self.patterns["framework_patterns"][framework]["rx_binding"] += count

                    # Alamofire
                    if framework == "Alamofire":
                        af_patterns = [
                            r'AF\.request\(',
                            r'\.response\(',
                            r'\.validate\('
                        ]
                        for pattern in af_patterns:
                            count = len(re.findall(pattern, content))
                            if count > 0:
                                self.patterns["framework_patterns"][framework]["networking"] += count

    def get_frequent_patterns(
            self,
            min_frequency: float = 0.6,
            min_occurrences: int = 3
    ) -> Dict:
        """
        자주 등장하는 패턴 추출

        Args:
            min_frequency: 최소 프로젝트 비율
            min_occurrences: 최소 등장 횟수

        Returns:
            자주 등장하는 패턴
        """
        frequent = {
            "property_names": [],
            "method_names": [],
            "class_suffixes": [],
            "delegate_methods": [],
            "framework_patterns": {}
        }

        threshold = int(self.total_projects * min_frequency)

        # 프로퍼티 이름
        for name, count in self.patterns["property_names"].items():
            if count >= max(threshold, min_occurrences):
                frequent["property_names"].append({
                    "name": name,
                    "count": count,
                    "frequency": count / self.total_projects
                })

        # 메서드 이름
        for name, count in self.patterns["method_names"].items():
            if count >= max(threshold, min_occurrences):
                frequent["method_names"].append({
                    "name": name,
                    "count": count,
                    "frequency": count / self.total_projects
                })

        # 클래스 접미사 (ViewController, ViewModel 등)
        suffix_counter = Counter()
        for name in self.patterns["class_names"].keys():
            for suffix in ["ViewController", "ViewModel", "Coordinator", "Cell", "View", "Service", "Manager"]:
                if name.endswith(suffix):
                    suffix_counter[suffix] += 1

        for suffix, count in suffix_counter.items():
            if count >= threshold:
                frequent["class_suffixes"].append({
                    "suffix": suffix,
                    "count": count,
                    "frequency": count / self.total_projects
                })

        # 델리게이트 메서드
        for name, count in self.patterns["delegate_methods"].items():
            if count >= max(threshold, min_occurrences):
                frequent["delegate_methods"].append({
                    "name": name,
                    "count": count,
                    "frequency": count / self.total_projects
                })

        # 프레임워크 패턴
        for framework, patterns in self.patterns["framework_patterns"].items():
            frequent["framework_patterns"][framework] = []
            for pattern_name, counter in patterns.items():
                total = sum(counter.values())
                if total >= threshold:
                    frequent["framework_patterns"][framework].append({
                        "pattern": pattern_name,
                        "count": total
                    })

        return frequent

    def save_patterns(self, patterns: Dict, filename: str = "patterns.json"):
        """패턴 저장"""
        output_path = Config.DATA_DIR / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=2, ensure_ascii=False)

        print(f"💾 Saved patterns to {output_path}")

    def generate_report(self, patterns: Dict) -> str:
        """분석 리포트 생성"""
        report = []
        report.append("=" * 70)
        report.append("📊 PATTERN EXTRACTION REPORT")
        report.append("=" * 70)
        report.append(f"\n📈 Total Projects Analyzed: {self.total_projects}")

        report.append(f"\n🔤 Frequent Property Names ({len(patterns['property_names'])} found):")
        for item in sorted(patterns["property_names"], key=lambda x: x["frequency"], reverse=True)[:20]:
            report.append(f"   • {item['name']:<20} {item['count']:>4} times ({item['frequency']:.1%})")

        report.append(f"\n⚙️  Frequent Method Names ({len(patterns['method_names'])} found):")
        for item in sorted(patterns["method_names"], key=lambda x: x["frequency"], reverse=True)[:20]:
            report.append(f"   • {item['name']:<20} {item['count']:>4} times ({item['frequency']:.1%})")

        report.append(f"\n🏗️  Class Name Suffixes ({len(patterns['class_suffixes'])} found):")
        for item in sorted(patterns["class_suffixes"], key=lambda x: x["frequency"], reverse=True):
            report.append(f"   • {item['suffix']:<20} {item['count']:>4} times ({item['frequency']:.1%})")

        report.append(f"\n📡 Delegate Methods ({len(patterns['delegate_methods'])} found):")
        for item in sorted(patterns["delegate_methods"], key=lambda x: x["frequency"], reverse=True)[:15]:
            report.append(f"   • {item['name']:<30} {item['count']:>4} times ({item['frequency']:.1%})")

        if patterns["framework_patterns"]:
            report.append(f"\n📦 Framework-Specific Patterns:")
            for framework, items in patterns["framework_patterns"].items():
                report.append(f"   {framework}:")
                for item in items:
                    report.append(f"      • {item['pattern']}: {item['count']} occurrences")

        report.append("\n" + "=" * 70)

        return "\n".join(report)


def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("🔍 Pattern Extraction from Downloaded Projects")
    print("=" * 70)

    # 프로젝트 목록 로드
    projects_file = Config.DATA_DIR / "projects.json"
    if not projects_file.exists():
        print("❌ No projects.json found. Run github_crawler.py first.")
        return

    with open(projects_file, "r", encoding="utf-8") as f:
        projects = json.load(f)

    # 다운로드된 프로젝트만 필터링
    downloaded_projects = [p for p in projects if "local_path" in p]

    if not downloaded_projects:
        print("❌ No downloaded projects found.")
        print("   Run github_crawler.py with download option.")
        return

    print(f"\n📁 Found {len(downloaded_projects)} downloaded projects")

    # 패턴 추출
    extractor = PatternExtractor()

    print("\n🔍 Extracting patterns...")
    for i, project in enumerate(downloaded_projects, 1):
        print(f"\n[{i}/{len(downloaded_projects)}]")
        project_path = Path(project["local_path"])
        dependencies = project.get("dependencies", [])

        if project_path.exists():
            extractor.analyze_project(project_path, dependencies)
        else:
            print(f"   ⚠️  Path not found: {project_path}")

    # 자주 등장하는 패턴 추출
    print(f"\n📊 Analyzing frequency...")
    frequent_patterns = extractor.get_frequent_patterns(
        min_frequency=Config.MIN_FREQUENCY,
        min_occurrences=Config.MIN_OCCURRENCES
    )

    # 저장
    extractor.save_patterns(frequent_patterns)

    # 리포트 출력
    report = extractor.generate_report(frequent_patterns)
    print("\n" + report)

    # 리포트 파일 저장
    report_path = Config.DATA_DIR / "extraction_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n💾 Report saved to {report_path}")

    print("\n" + "=" * 70)
    print("🎉 Pattern extraction completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()