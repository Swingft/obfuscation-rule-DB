#!/usr/bin/env python3
"""
리소스 파일 수집기

프로젝트에서 XIB, Storyboard, Plist, CoreData 등의 리소스 파일을 찾아
./resource 디렉토리에 타입별로 분류하여 복사합니다.
"""

import shutil
import json
import argparse
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict
import xml.etree.ElementTree as ET
import re


# 기존 파서 클래스들 (resource_identifier_extractor.py에서 가져옴)
class XIBStoryboardParser:
    """XIB/Storyboard 파일에서 식별자 추출"""

    @classmethod
    def parse(cls, file_path: Path) -> Dict[str, Set[str]]:
        result = defaultdict(set)

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            for elem in root.iter():
                custom_class = elem.get('customClass')
                if custom_class and cls._is_valid_identifier(custom_class):
                    result['classes'].add(custom_class)

                custom_module = elem.get('customModule')
                if custom_module and cls._is_valid_identifier(custom_module):
                    result['modules'].add(custom_module)

            for connection in root.iter('connection'):
                kind = connection.get('kind')
                property_name = connection.get('property')

                if kind == 'outlet' and property_name:
                    result['outlets'].add(property_name)
                elif kind == 'action':
                    selector = connection.get('selector')
                    if selector:
                        result['actions'].add(selector)

            for segue in root.iter('segue'):
                identifier = segue.get('identifier')
                if identifier:
                    result['segue_identifiers'].add(identifier)

            for elem in root.iter():
                reuse_id = elem.get('reuseIdentifier')
                if reuse_id:
                    result['reuse_identifiers'].add(reuse_id)

                storyboard_id = elem.get('storyboardIdentifier')
                if storyboard_id:
                    result['storyboard_identifiers'].add(storyboard_id)

                restoration_id = elem.get('restorationIdentifier')
                if restoration_id:
                    result['restoration_identifiers'].add(restoration_id)

            for attr in root.iter('userDefinedRuntimeAttribute'):
                keypath = attr.get('keyPath')
                if keypath:
                    parts = keypath.split('.')
                    for part in parts:
                        if cls._is_valid_identifier(part):
                            result['runtime_attributes'].add(part)

        except Exception as e:
            pass

        return dict(result)

    @staticmethod
    def _is_valid_identifier(name: str) -> bool:
        if not name or len(name) <= 1:
            return False
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))


class PlistParser:
    """Plist 파일에서 식별자 추출"""

    @classmethod
    def parse(cls, file_path: Path) -> Dict[str, Set[str]]:
        result = defaultdict(set)

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            main_dict = root.find('dict')
            if main_dict is None:
                return dict(result)

            cls._parse_dict(main_dict, result, [])

        except Exception as e:
            pass

        return dict(result)

    @classmethod
    def _parse_dict(cls, dict_elem, result: defaultdict, key_path: List[str]):
        children = list(dict_elem)
        i = 0

        while i < len(children):
            if children[i].tag == 'key':
                key = children[i].text
                if i + 1 < len(children):
                    value_elem = children[i + 1]

                    if key == 'CFBundleURLSchemes' and value_elem.tag == 'array':
                        for string_elem in value_elem.findall('string'):
                            if string_elem.text:
                                result['url_schemes'].add(string_elem.text)

                    elif key == 'CFBundleTypeName' and value_elem.tag == 'string':
                        if value_elem.text:
                            result['document_types'].add(value_elem.text)

                    elif key == 'UTTypeIdentifier' and value_elem.tag == 'string':
                        if value_elem.text:
                            result['uti_identifiers'].add(value_elem.text)

                    elif key == 'NSUserActivityTypes' and value_elem.tag == 'array':
                        for string_elem in value_elem.findall('string'):
                            if string_elem.text:
                                result['user_activity_types'].add(string_elem.text)

                    elif value_elem.tag == 'dict':
                        cls._parse_dict(value_elem, result, key_path + [key])
                    elif value_elem.tag == 'array':
                        cls._parse_array(value_elem, result, key_path + [key])

                    i += 2
                else:
                    i += 1
            else:
                i += 1

    @classmethod
    def _parse_array(cls, array_elem, result: defaultdict, key_path: List[str]):
        for child in array_elem:
            if child.tag == 'dict':
                cls._parse_dict(child, result, key_path)


class CoreDataParser:
    """CoreData 모델 파일에서 식별자 추출"""

    @classmethod
    def parse(cls, model_path: Path) -> Dict[str, Set[str]]:
        result = defaultdict(set)

        if model_path.is_dir():
            for xcdatamodel in model_path.glob('*.xcdatamodel'):
                contents_file = xcdatamodel / 'contents'
                if contents_file.exists():
                    cls._parse_contents(contents_file, result)
        else:
            cls._parse_contents(model_path, result)

        return dict(result)

    @classmethod
    def _parse_contents(cls, contents_file: Path, result: defaultdict):
        try:
            tree = ET.parse(contents_file)
            root = tree.getroot()

            for entity in root.findall('.//entity'):
                name = entity.get('name')
                if name:
                    result['entities'].add(name)

                for attr in entity.findall('attribute'):
                    attr_name = attr.get('name')
                    if attr_name:
                        result['attributes'].add(attr_name)

                for rel in entity.findall('relationship'):
                    rel_name = rel.get('name')
                    if rel_name:
                        result['relationships'].add(rel_name)

            for fetch in root.findall('.//fetchRequest'):
                name = fetch.get('name')
                if name:
                    result['fetch_requests'].add(name)

        except Exception as e:
            pass


class StringsFileParser:
    """Localizable.strings 파일에서 키 추출"""

    @classmethod
    def parse(cls, file_path: Path) -> Set[str]:
        keys = set()

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            pattern = re.compile(r'^"([^"]+)"\s*=\s*"[^"]*"\s*;', re.MULTILINE)

            for match in pattern.finditer(content):
                key = match.group(1)
                if key:
                    keys.add(key)

        except Exception as e:
            pass

        return keys


class EntitlementsParser:
    """Entitlements 파일에서 식별자 추출"""

    @classmethod
    def parse(cls, file_path: Path) -> Dict[str, Set[str]]:
        result = defaultdict(set)

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            main_dict = root.find('dict')
            if main_dict is None:
                return dict(result)

            children = list(main_dict)
            i = 0

            while i < len(children):
                if children[i].tag == 'key':
                    key = children[i].text
                    if i + 1 < len(children):
                        value_elem = children[i + 1]

                        if key == 'com.apple.security.application-groups' and value_elem.tag == 'array':
                            for string_elem in value_elem.findall('string'):
                                if string_elem.text:
                                    result['app_groups'].add(string_elem.text)

                        elif key == 'keychain-access-groups' and value_elem.tag == 'array':
                            for string_elem in value_elem.findall('string'):
                                if string_elem.text:
                                    result['keychain_groups'].add(string_elem.text)

                        i += 2
                    else:
                        i += 1
                else:
                    i += 1

        except Exception as e:
            pass

        return dict(result)


class ResourceCollector:
    """리소스 파일 수집기"""

    # 지원하는 리소스 타입 (난독화 제외 식별자 추출 대상)
    RESOURCE_TYPES = {
        'plist': {
            'extensions': ['.plist'],
            'subdirectory': 'plist',
            'parser': PlistParser
        },
        'xib': {
            'extensions': ['.xib'],
            'subdirectory': 'xib',
            'parser': XIBStoryboardParser
        },
        'storyboard': {
            'extensions': ['.storyboard'],
            'subdirectory': 'storyboard',
            'parser': XIBStoryboardParser
        },
        'coredata': {
            'extensions': ['.xcdatamodeld', '.xcdatamodel'],
            'subdirectory': 'coredata',
            'parser': CoreDataParser,
            'is_directory': True
        },
        'strings': {
            'extensions': ['.strings'],
            'subdirectory': 'strings',
            'parser': StringsFileParser
        },
        'entitlements': {
            'extensions': ['.entitlements'],
            'subdirectory': 'entitlements',
            'parser': EntitlementsParser
        },
    }

    def __init__(self, project_path: Path, output_dir: Path = Path('./resource'),
                 resource_types: Optional[List[str]] = None,
                 exclude_dirs: Optional[List[str]] = None,
                 preserve_structure: bool = False,
                 extract_identifiers: bool = False):
        """
        Args:
            project_path: 프로젝트 루트 경로
            output_dir: 리소스 파일을 저장할 디렉토리 (기본: ./resource)
            resource_types: 수집할 리소스 타입 목록 (None이면 전체)
            exclude_dirs: 제외할 디렉토리 목록
            preserve_structure: True면 폴더 구조 유지, False면 평탄화
            extract_identifiers: True면 식별자 추출
        """
        self.project_path = Path(project_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.preserve_structure = preserve_structure
        self.extract_identifiers = extract_identifiers

        # 수집할 타입 (None이면 전체)
        if resource_types is None:
            self.active_types = set(self.RESOURCE_TYPES.keys())
        else:
            self.active_types = set(resource_types)
            # 유효하지 않은 타입 체크
            invalid = self.active_types - set(self.RESOURCE_TYPES.keys())
            if invalid:
                print(f"⚠️  알 수 없는 타입: {', '.join(invalid)}")
                print(f"   지원 타입: {', '.join(self.RESOURCE_TYPES.keys())}")

        self.exclude_dirs = exclude_dirs or [
            '.build', 'build', 'DerivedData', '.git', 'node_modules',
        ]

        self.stats = defaultdict(lambda: {'found': 0, 'copied': 0, 'failed': 0})
        self.filename_counter = defaultdict(lambda: defaultdict(int))

        # 식별자 추출 결과
        self.identifiers = defaultdict(lambda: defaultdict(set))

    def should_skip_directory(self, dir_path: Path) -> bool:
        """디렉토리 스킵 여부"""
        dir_name = dir_path.name

        if dir_name.startswith('.') and dir_name != '.':
            return True

        if dir_name in self.exclude_dirs:
            return True

        return False

    def get_resource_type(self, file_path: Path) -> Optional[str]:
        """파일의 리소스 타입 반환"""
        for type_name, type_info in self.RESOURCE_TYPES.items():
            if type_name not in self.active_types:
                continue

            for ext in type_info['extensions']:
                if file_path.suffix == ext or (type_info.get('is_directory') and file_path.suffix == ext):
                    return type_name

        return None

    def get_destination_path(self, resource_file: Path, resource_type: str) -> Path:
        """리소스 파일의 목적지 경로 결정"""
        type_info = self.RESOURCE_TYPES[resource_type]
        type_subdir = self.output_dir / type_info['subdirectory']

        if self.preserve_structure:
            try:
                rel_path = resource_file.relative_to(self.project_path)
                dest_path = type_subdir / rel_path
            except ValueError:
                dest_path = type_subdir / resource_file.name
        else:
            filename = resource_file.name

            # 중복 파일명 처리
            if self.filename_counter[resource_type][filename] > 0:
                stem = resource_file.stem
                ext = resource_file.suffix
                new_name = f"{stem}_{self.filename_counter[resource_type][filename]}{ext}"
                dest_path = type_subdir / new_name
            else:
                dest_path = type_subdir / filename

            self.filename_counter[resource_type][filename] += 1

        return dest_path

    def copy_resource(self, resource_file: Path, dest_path: Path, is_directory: bool = False) -> bool:
        """리소스 파일 복사"""
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if is_directory:
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(resource_file, dest_path)
            else:
                shutil.copy2(resource_file, dest_path)

            return True
        except Exception as e:
            print(f"  ⚠️  복사 실패: {resource_file.name} - {e}")
            return False

    def extract_identifiers_from_file(self, resource_file: Path, resource_type: str):
        """파일에서 식별자 추출"""
        type_info = self.RESOURCE_TYPES[resource_type]
        parser = type_info.get('parser')

        if parser is None:
            return

        try:
            if resource_type == 'strings':
                # strings는 Set[str] 반환
                keys = parser.parse(resource_file)
                if keys:
                    self.identifiers[resource_type]['localization_keys'].update(keys)
            else:
                # 나머지는 Dict[str, Set[str]] 반환
                parsed = parser.parse(resource_file)
                for category, identifiers in parsed.items():
                    self.identifiers[resource_type][category].update(identifiers)
        except Exception as e:
            pass

    def find_and_collect_resources(self) -> Dict[str, int]:
        """리소스 파일 찾아서 수집"""

        def scan_directory(directory: Path):
            try:
                for item in directory.iterdir():
                    if item.is_dir():
                        if not self.should_skip_directory(item):
                            # CoreData, Assets 같은 디렉토리형 리소스 체크
                            resource_type = self.get_resource_type(item)
                            if resource_type:
                                type_info = self.RESOURCE_TYPES[resource_type]
                                if type_info.get('is_directory'):
                                    self.stats[resource_type]['found'] += 1

                                    dest_path = self.get_destination_path(item, resource_type)

                                    if self.copy_resource(item, dest_path, is_directory=True):
                                        self.stats[resource_type]['copied'] += 1
                                        print(f"✓ {resource_type}: {item.name}")

                                        if self.extract_identifiers:
                                            self.extract_identifiers_from_file(item, resource_type)
                                    else:
                                        self.stats[resource_type]['failed'] += 1

                                    continue

                            scan_directory(item)

                    elif item.is_file():
                        resource_type = self.get_resource_type(item)
                        if resource_type:
                            self.stats[resource_type]['found'] += 1

                            dest_path = self.get_destination_path(item, resource_type)

                            if self.copy_resource(item, dest_path):
                                self.stats[resource_type]['copied'] += 1
                                print(f"✓ {resource_type}: {item.name}")

                                if self.extract_identifiers:
                                    self.extract_identifiers_from_file(item, resource_type)
                            else:
                                self.stats[resource_type]['failed'] += 1

            except PermissionError:
                pass

        scan_directory(self.project_path)

        return {rtype: stats['copied'] for rtype, stats in self.stats.items()}

    def collect_all(self):
        """모든 리소스 수집"""
        print(f"🔍 프로젝트: {self.project_path}")
        print(f"📂 저장 위치: {self.output_dir}")
        print(f"📁 구조 유지: {'예' if self.preserve_structure else '아니오 (평탄화)'}")
        print(f"🔎 식별자 추출: {'예' if self.extract_identifiers else '아니오'}")
        print(f"📦 수집 타입: {', '.join(sorted(self.active_types))}")
        print()

        # 출력 디렉토리 초기화
        if self.output_dir.exists():
            print(f"🗑️  기존 {self.output_dir} 삭제 중...")
            shutil.rmtree(self.output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 리소스 수집
        print("📝 리소스 파일 수집 중...")
        print("-" * 60)

        copied_counts = self.find_and_collect_resources()

        return copied_counts

    def print_summary(self):
        """결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 수집 결과 요약")
        print("=" * 60)

        total_found = 0
        total_copied = 0
        total_failed = 0

        for resource_type in sorted(self.active_types):
            stats = self.stats[resource_type]
            if stats['found'] > 0:
                print(f"\n[{resource_type}]")
                print(f"  발견:       {stats['found']:>6}개")
                print(f"  복사 성공:   {stats['copied']:>6}개")
                if stats['failed'] > 0:
                    print(f"  복사 실패:   {stats['failed']:>6}개")

                total_found += stats['found']
                total_copied += stats['copied']
                total_failed += stats['failed']

        print(f"\n{'[전체]'}")
        print(f"  발견:       {total_found:>6}개")
        print(f"  복사 성공:   {total_copied:>6}개")
        if total_failed > 0:
            print(f"  복사 실패:   {total_failed:>6}개")

        print(f"\n저장 위치:   {self.output_dir}")
        print("=" * 60)

        # 식별자 추출 결과
        if self.extract_identifiers and self.identifiers:
            print("\n" + "=" * 60)
            print("🔍 식별자 추출 결과")
            print("=" * 60)

            for resource_type in sorted(self.identifiers.keys()):
                categories = self.identifiers[resource_type]
                if categories:
                    print(f"\n[{resource_type}]")
                    for category, ids in sorted(categories.items()):
                        if ids:
                            print(f"  {category:25s}: {len(ids):>6}개")

            print("=" * 60)

    def save_identifiers_json(self, output_path: Path):
        """식별자를 JSON으로 저장"""
        if not self.identifiers:
            print("⚠️  추출된 식별자가 없습니다.")
            return

        output_data = {
            "project_path": str(self.project_path),
            "description": "리소스 파일에서 추출한 식별자 목록",
            "identifiers_by_type": {}
        }

        for resource_type, categories in self.identifiers.items():
            output_data["identifiers_by_type"][resource_type] = {
                category: sorted(list(identifiers))
                for category, identifiers in categories.items()
            }

        # 전체 식별자
        all_ids = set()
        for categories in self.identifiers.values():
            for identifiers in categories.values():
                all_ids.update(identifiers)

        output_data["all_identifiers"] = sorted(list(all_ids))
        output_data["total_identifiers"] = len(all_ids)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 식별자 JSON 저장: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="프로젝트에서 리소스 파일을 찾아 ./resource 디렉토리에 타입별로 분류하여 복사합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
리소스 타입:
  plist, xib, storyboard, coredata, strings, assets, entitlements

사용 예시:
  # 모든 리소스 수집
  python collect_resources.py /path/to/project

  # plist만 수집
  python collect_resources.py /path/to/project --types plist

  # plist와 xib만 수집
  python collect_resources.py /path/to/project --types plist xib

  # 수집 + 식별자 추출
  python collect_resources.py /path/to/project --extract-identifiers

  # 특정 타입만 수집 + 식별자 추출 + JSON 저장
  python collect_resources.py /path/to/project --types plist xib --extract-identifiers --json identifiers.json

  # 특정 디렉토리에 저장
  python collect_resources.py /path/to/project -o ./output/resources

  # 폴더 구조 유지
  python collect_resources.py /path/to/project --preserve-structure
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
        default=Path('./resource'),
        help='리소스 파일을 저장할 디렉토리 (기본: ./resource)'
    )

    parser.add_argument(
        '--types',
        nargs='+',
        choices=list(ResourceCollector.RESOURCE_TYPES.keys()),
        help='수집할 리소스 타입 지정 (미지정 시 전체)'
    )

    parser.add_argument(
        '--preserve-structure',
        action='store_true',
        help='원본 폴더 구조 유지 (기본: 평탄화)'
    )

    parser.add_argument(
        '--extract-identifiers',
        action='store_true',
        help='식별자 추출 수행'
    )

    parser.add_argument(
        '--json',
        type=Path,
        help='식별자를 JSON 파일로 저장 (--extract-identifiers와 함께 사용)'
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
        default_exclude = ['.build', 'build', 'DerivedData', '.git', 'node_modules']
        exclude_dirs = default_exclude + args.exclude

    # 수집 시작
    print("🚀 리소스 파일 수집기")
    print("=" * 60)
    print()

    collector = ResourceCollector(
        args.project_path,
        args.output,
        args.types,
        exclude_dirs,
        args.preserve_structure,
        args.extract_identifiers
    )

    copied_counts = collector.collect_all()

    # 결과
    collector.print_summary()

    total_copied = sum(copied_counts.values())

    if total_copied > 0:
        print(f"\n✅ 완료! {total_copied}개의 리소스 파일이 복사되었습니다.")
    else:
        print("\n⚠️  복사된 파일이 없습니다.")

    # JSON 저장
    if args.json and args.extract_identifiers:
        collector.save_identifiers_json(args.json)
    elif args.json and not args.extract_identifiers:
        print("\n⚠️  --json 옵션은 --extract-identifiers와 함께 사용해야 합니다.")

    return 0


if __name__ == "__main__":
    exit(main())