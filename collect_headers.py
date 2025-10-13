#!/usr/bin/env python3
"""
헤더 파일 수집기

프로젝트에서 모든 .h 파일을 찾아 ./header 디렉토리에 복사합니다.
"""

import shutil
import argparse
from pathlib import Path
from typing import List
from collections import defaultdict


class HeaderCollector:
    """헤더 파일을 찾아 수집하는 클래스"""

    def __init__(self, project_path: Path, output_dir: Path = Path("./header"),
                 exclude_dirs: List[str] = None, preserve_structure: bool = False):
        """
        Args:
            project_path: 프로젝트 루트 경로
            output_dir: 헤더 파일을 저장할 디렉토리 (기본: ./header)
            exclude_dirs: 제외할 디렉토리 목록
            preserve_structure: True면 폴더 구조 유지, False면 평탄화
        """
        self.project_path = Path(project_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.preserve_structure = preserve_structure

        self.exclude_dirs = exclude_dirs or [
            'Pods',
            'Carthage',
            '.build',
            'build',
            'DerivedData',
            '.git',
            'node_modules',
        ]

        self.stats = {
            'total_found': 0,
            'copied': 0,
            'skipped': 0,
            'duplicates': 0
        }

        # 중복 파일명 처리용
        self.filename_counter = defaultdict(int)

    def should_skip_directory(self, dir_path: Path) -> bool:
        """디렉토리 스킵 여부"""
        dir_name = dir_path.name

        # 숨김 폴더
        if dir_name.startswith('.') and dir_name != '.':
            return True

        # 제외 목록
        if dir_name in self.exclude_dirs:
            return True

        return False

    def find_header_files(self) -> List[Path]:
        """프로젝트에서 모든 .h 파일 찾기"""
        header_files = []

        def scan_directory(directory: Path):
            try:
                for item in directory.iterdir():
                    if item.is_dir():
                        if not self.should_skip_directory(item):
                            scan_directory(item)
                    elif item.is_file() and item.suffix == '.h':
                        header_files.append(item)
            except PermissionError:
                pass

        scan_directory(self.project_path)
        return header_files

    def get_destination_path(self, header_file: Path) -> Path:
        """헤더 파일의 목적지 경로 결정"""
        if self.preserve_structure:
            # 상대 경로 유지
            try:
                rel_path = header_file.relative_to(self.project_path)
                dest_path = self.output_dir / rel_path
            except ValueError:
                # 프로젝트 외부 파일인 경우
                dest_path = self.output_dir / header_file.name
        else:
            # 평탄화 (모든 파일을 output_dir 바로 아래에)
            filename = header_file.name

            # 중복 파일명 처리
            if self.filename_counter[filename] > 0:
                # 중복이면 _1, _2, ... 추가
                stem = header_file.stem
                ext = header_file.suffix
                new_name = f"{stem}_{self.filename_counter[filename]}{ext}"
                dest_path = self.output_dir / new_name
                self.stats['duplicates'] += 1
            else:
                dest_path = self.output_dir / filename

            self.filename_counter[filename] += 1

        return dest_path

    def copy_header(self, header_file: Path, dest_path: Path) -> bool:
        """헤더 파일 복사"""
        try:
            # 디렉토리 생성
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # 파일 복사
            shutil.copy2(header_file, dest_path)
            return True
        except Exception as e:
            print(f"  ⚠️  복사 실패: {header_file.name} - {e}")
            return False

    def collect_all(self) -> int:
        """모든 헤더 파일 수집"""
        print(f"🔍 프로젝트: {self.project_path}")
        print(f"📂 저장 위치: {self.output_dir}")
        print(f"📁 구조 유지: {'예' if self.preserve_structure else '아니오 (평탄화)'}")
        print()

        # 출력 디렉토리 초기화
        if self.output_dir.exists():
            print(f"🗑️  기존 {self.output_dir} 삭제 중...")
            shutil.rmtree(self.output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 헤더 파일 찾기
        print("🔎 헤더 파일 검색 중...")
        header_files = self.find_header_files()
        self.stats['total_found'] = len(header_files)

        if not header_files:
            print("❌ 헤더 파일을 찾을 수 없습니다.")
            return 0

        print(f"✓ {len(header_files)}개의 헤더 파일 발견\n")

        # 복사 시작
        print("📝 헤더 파일 복사 중...")
        print("-" * 60)

        for i, header_file in enumerate(header_files, 1):
            try:
                rel_path = header_file.relative_to(self.project_path)
            except ValueError:
                rel_path = header_file

            dest_path = self.get_destination_path(header_file)

            if self.copy_header(header_file, dest_path):
                self.stats['copied'] += 1
                print(f"[{i:3d}/{len(header_files)}] ✓ {rel_path}")
            else:
                self.stats['skipped'] += 1

        return self.stats['copied']

    def print_summary(self):
        """결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 수집 결과 요약")
        print("=" * 60)
        print(f"발견:       {self.stats['total_found']:>6}개")
        print(f"복사 성공:   {self.stats['copied']:>6}개")
        print(f"복사 실패:   {self.stats['skipped']:>6}개")

        if self.stats['duplicates'] > 0:
            print(f"중복 처리:   {self.stats['duplicates']:>6}개 (자동으로 이름 변경됨)")

        print(f"\n저장 위치:   {self.output_dir}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="프로젝트에서 모든 헤더 파일(.h)을 찾아 ./header 디렉토리에 복사합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 사용 (./header에 평탄화하여 저장)
  python collect_headers.py /path/to/project

  # 특정 디렉토리에 저장
  python collect_headers.py /path/to/project -o ./output/headers

  # 폴더 구조 유지하면서 저장
  python collect_headers.py /path/to/project --preserve-structure

  # 특정 폴더 제외
  python collect_headers.py /path/to/project --exclude Tests External
        """
    )

    parser.add_argument(
        'project_path',
        type=Path,
        help='프로젝트 루트 경로'
    )

    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=Path('./header'),
        help='헤더 파일을 저장할 디렉토리 (기본: ./header)'
    )

    parser.add_argument(
        '--preserve-structure',
        action='store_true',
        help='원본 폴더 구조 유지 (기본: 평탄화)'
    )

    parser.add_argument(
        '--exclude',
        nargs='+',
        help='제외할 디렉토리 추가'
    )

    args = parser.parse_args()

    # 경로 확인
    if not args.project_path.exists():
        print(f"❌ 경로를 찾을 수 없습니다: {args.project_path}")
        return 1

    if not args.project_path.is_dir():
        print(f"❌ 디렉토리가 아닙니다: {args.project_path}")
        return 1

    # 제외 디렉토리
    exclude_dirs = None
    if args.exclude:
        default_exclude = [
            'Pods', 'Carthage', '.build', 'build',
            'DerivedData', '.git', 'node_modules'
        ]
        exclude_dirs = default_exclude + args.exclude

    # 수집 시작
    print("🚀 헤더 파일 수집기")
    print("=" * 60)
    print()

    collector = HeaderCollector(
        args.project_path,
        args.output,
        exclude_dirs,
        args.preserve_structure
    )

    copied_count = collector.collect_all()

    # 결과
    collector.print_summary()

    if copied_count > 0:
        print(f"\n✅ 완료! {copied_count}개의 헤더 파일이 복사되었습니다.")
    else:
        print("\n⚠️  복사된 파일이 없습니다.")

    return 0


if __name__ == "__main__":
    exit(main())