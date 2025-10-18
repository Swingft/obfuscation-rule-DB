#!/usr/bin/env python3
"""
Swift Obfuscation Analyzer
CLI 도구 - 난독화 제외 대상 분석

사용법:
    python analyze.py <project_path> [options]
"""

import argparse
import subprocess
import sys
from pathlib import Path
import json

# 모듈 임포트
from lib.extractors.header_extractor import HeaderScanner
from lib.extractors.resource_identifier_extractor import ResourceScanner
from lib.analyzer.graph_loader import SymbolGraph
from lib.analyzer.analysis_engine import AnalysisEngine
from lib.analyzer.rule_loader import RuleLoader
from lib.utils.report_generator import ReportGenerator


class ObfuscationAnalyzer:
    """난독화 분석 오케스트레이터"""

    def __init__(self, project_path: Path, output_dir: Path = None, debug: bool = False):
        self.project_path = Path(project_path)
        self.output_dir = output_dir or Path("./analysis_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.debug = debug

        # 내부 경로
        self.bin_dir = Path(__file__).parent / "bin"
        self.rules_path = Path(__file__).parent / "rules" / "swift_exclusion_rules.yaml"

        # 프로젝트 이름 자동 추출
        self.project_name = self._find_project_name()

    def run_full_analysis(self, real_project_name: str = None):
        """전체 분석 파이프라인 실행"""
        print("=" * 70)
        print("🚀 Swift Obfuscation Analysis Pipeline")
        print("=" * 70)

        # 프로젝트 이름 사용 (사용자 지정 우선, 없으면 자동 추출)
        project_name = real_project_name or self.project_name
        print(f"📦 Project Name: {project_name}\n")

        # Step 1: 외부 식별자 추출
        external_ids = self._extract_external_identifiers(project_name)
        print(f"✅ Step 1 Complete: {len(external_ids)} external identifiers found\n")

        # Step 2: 심볼 그래프 생성
        symbol_graph_path = self._generate_symbol_graph(external_ids)
        print(f"✅ Step 2 Complete: Symbol graph generated\n")

        # Step 3: 규칙 기반 분석
        results = self._run_rule_analysis(symbol_graph_path)
        print(f"✅ Step 3 Complete: {len(results)} symbols excluded\n")

        # Step 4: 리포트 생성
        self._generate_reports(results)

        # Step 5: 디버그 모드가 아니면 중간 파일 삭제
        if not self.debug:
            self._cleanup_intermediate_files()

        print("=" * 70)
        print(f"🎉 Analysis Complete!")
        print(f"📁 Results saved to: {self.output_dir.absolute()}")
        if not self.debug:
            print(f"ℹ️  Only exclusion_list.txt kept (use --debug to keep all files)")
        print("=" * 70)

        return results

    def _extract_external_identifiers(self, project_name: str = None) -> set:
        """Step 1: 헤더 + 리소스 식별자 추출"""
        print("📝 [Step 1/3] Extracting external identifiers...")

        all_identifiers = set()

        # 1-1. 헤더 스캔
        print("  → Scanning Objective-C headers...")
        header_scanner = HeaderScanner(
            self.project_path,
            scan_spm=True,
            real_project_name=project_name
        )
        header_scanner.scan_all()
        header_ids = header_scanner.get_all_identifiers()
        all_identifiers.update(header_ids)
        print(f"     Found {len(header_ids)} identifiers from headers")

        # 1-2. 리소스 스캔
        print("  → Scanning resource files...")
        resource_scanner = ResourceScanner(self.project_path)
        resource_scanner.scan_all()
        resource_ids = resource_scanner.get_all_identifiers()
        all_identifiers.update(resource_ids)
        print(f"     Found {len(resource_ids)} identifiers from resources")

        # 저장
        external_file = self.output_dir / "external_identifiers.txt"
        with open(external_file, 'w', encoding='utf-8') as f:
            for identifier in sorted(all_identifiers):
                f.write(identifier + '\n')

        return all_identifiers

    def _generate_symbol_graph(self, external_ids: set) -> Path:
        """Step 2: Swift SymbolExtractor 실행"""
        print("🔍 [Step 2/3] Generating symbol graph...")

        symbol_extractor = self.bin_dir / "SymbolExtractor"

        if not symbol_extractor.exists():
            raise FileNotFoundError(
                f"SymbolExtractor not found at {symbol_extractor}\n"
                "Please build it first:\n"
                "  cd swift-extractor && swift build -c release\n"
                "  cp .build/release/SymbolExtractor ../bin/"
            )

        # 외부 식별자 파일
        external_file = self.output_dir / "external_identifiers.txt"
        symbol_graph_path = self.output_dir / "symbol_graph.json"

        # SymbolExtractor 실행
        cmd = [
            str(symbol_extractor),
            str(self.project_path),
            "--output", str(symbol_graph_path),
            "--external-exclusion-list", str(external_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print("❌ SymbolExtractor failed:")
            print(result.stderr)
            sys.exit(1)

        print(f"  → Symbol graph saved to: {symbol_graph_path.name}")
        return symbol_graph_path

    def _run_rule_analysis(self, symbol_graph_path: Path) -> list:
        """Step 3: 규칙 엔진 실행"""
        print("⚙️  [Step 3/3] Running rule-based analysis...")

        # 그래프 로드
        graph = SymbolGraph(str(symbol_graph_path))
        print(f"  → Loaded {len(graph.graph.nodes)} symbols")

        # 규칙 로드
        rules = RuleLoader(str(self.rules_path))
        print(f"  → Loaded {len(rules.rules)} rules")

        # 분석 실행
        engine = AnalysisEngine(graph, rules)
        engine.run()

        return engine.get_results()

    def _generate_reports(self, results: list):
        """Step 4: 리포트 생성"""
        reporter = ReportGenerator()

        # JSON 리포트
        json_path = self.output_dir / "exclusion_report.json"
        reporter.generate_json(results, str(json_path))

        # TXT 리포트 (이름만)
        txt_path = self.output_dir / "exclusion_list.txt"
        reporter.generate_txt(results, str(txt_path))

        # 콘솔 요약
        graph = SymbolGraph(str(self.output_dir / "symbol_graph.json"))
        reporter.print_summary(results, graph)

    def _find_project_name(self) -> str:
        """프로젝트 경로에서 프로젝트 이름 추출 (.xcodeproj 또는 .xcworkspace 또는 Package.swift)"""
        # 1. 주어진 경로가 .xcodeproj 파일이면 바로 사용
        if self.project_path.suffix == '.xcodeproj':
            return self.project_path.stem

        # 2. 주어진 경로가 .xcworkspace 파일이면 사용
        if self.project_path.suffix == '.xcworkspace':
            return self.project_path.stem

        # 3. 디렉토리라면 재귀적으로 .xcodeproj 또는 .xcworkspace 찾기
        if self.project_path.is_dir():
            # .xcodeproj 재귀 검색 (rglob)
            xcodeproj_files = list(self.project_path.rglob("*.xcodeproj"))
            if xcodeproj_files:
                # 가장 얕은 깊이의 프로젝트 선택
                xcodeproj_files.sort(key=lambda p: len(p.relative_to(self.project_path).parts))
                return xcodeproj_files[0].stem

            # .xcworkspace 재귀 검색
            xcworkspace_files = list(self.project_path.rglob("*.xcworkspace"))
            if xcworkspace_files:
                xcworkspace_files.sort(key=lambda p: len(p.relative_to(self.project_path).parts))
                return xcworkspace_files[0].stem

            # Package.swift 검색 (현재 디렉토리만)
            package_swift = self.project_path / "Package.swift"
            if package_swift.exists():
                # Package.swift에서 name 추출 시도
                try:
                    with open(package_swift, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # name: "ProjectName" 패턴 찾기
                        import re
                        match = re.search(r'name:\s*"([^"]+)"', content)
                        if match:
                            return match.group(1)
                except:
                    pass
                # 추출 실패시 디렉토리 이름 사용
                return self.project_path.name

        # 찾지 못하면 디렉토리 이름 사용
        return self.project_path.name

    def _cleanup_intermediate_files(self):
        """디버그 모드가 아닐 때 중간 파일 삭제 (exclusion_list.txt만 유지)"""
        print("\n🧹 Cleaning up intermediate files...")

        files_to_remove = [
            "external_identifiers.txt",
            "symbol_graph.json",
            "exclusion_report.json"
        ]

        for filename in files_to_remove:
            file_path = self.output_dir / filename
            if file_path.exists():
                try:
                    file_path.unlink()
                    print(f"  ✓ Removed {filename}")
                except Exception as e:
                    print(f"  ⚠️  Could not remove {filename}: {e}")

        print("  ✓ Cleanup complete (exclusion_list.txt preserved)")


def main():
    parser = argparse.ArgumentParser(
        description="Swift 프로젝트 난독화 제외 대상 분석기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 분석 (프로젝트 이름 자동 추출)
  python analyze.py /path/to/MyProject.xcodeproj
  python analyze.py /path/to/MyProject.xcworkspace
  python analyze.py /path/to/spm-project  # Package.swift 포함 디렉토리

  # 출력 디렉토리 지정
  python analyze.py /path/to/MyProject.xcodeproj -o ./results

  # 프로젝트 이름 명시 (DerivedData 검색용)
  python analyze.py /path/to/project -p "MyRealProjectName"

  # 디버그 모드 (모든 중간 파일 보존)
  python analyze.py /path/to/project --debug
        """
    )

    parser.add_argument(
        "project_path",
        type=Path,
        help="Swift 프로젝트 경로 (.xcodeproj, .xcworkspace, Package.swift, 또는 프로젝트 루트)"
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./analysis_output"),
        help="분석 결과 출력 디렉토리 (기본: ./analysis_output)"
    )

    parser.add_argument(
        "-p", "--project-name",
        type=str,
        help="DerivedData 검색용 프로젝트 이름 (미지정시 자동 추출)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="디버그 모드: 모든 중간 파일 보존"
    )

    args = parser.parse_args()

    # 프로젝트 존재 확인
    if not args.project_path.exists():
        print(f"❌ 오류: 프로젝트를 찾을 수 없습니다: {args.project_path}")
        sys.exit(1)

    # 분석 실행
    analyzer = ObfuscationAnalyzer(
        project_path=args.project_path,
        output_dir=args.output,
        debug=args.debug
    )

    analyzer.run_full_analysis(real_project_name=args.project_name)


if __name__ == "__main__":
    main()