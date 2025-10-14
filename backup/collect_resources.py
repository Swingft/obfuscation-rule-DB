#!/usr/bin/env python3
"""
리소스 파일 수집기 v2

프로젝트에서 XIB, Storyboard, Plist, CoreData, Strings, Entitlements, Assets 파일을 찾아
./resource 디렉토리에 타입별로 분류하여 복사합니다.
"""

import shutil
import json
import argparse
import plistlib
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict
import xml.etree.ElementTree as ET
import re


class XIBStoryboardParser:
    """XIB/Storyboard 파일에서 식별자 추출"""

    SYSTEM_CLASSES = {
        'UIResponder', 'UIViewController', 'UIView', 'UITableView',
        'UICollectionView', 'UIButton', 'UILabel', 'UIImageView',
        'UITableViewCell', 'UICollectionViewCell', 'UIScrollView',
        'UIStackView', 'UINavigationController', 'UITabBarController',
        'NSObject', 'NSManagedObject', 'UITextField', 'UITextView',
        'UISwitch', 'UISlider', 'UISegmentedControl', 'UIDatePicker',
    }

    @classmethod
    def parse(cls, file_path: Path) -> Dict[str, Set[str]]:
        result = defaultdict(set)

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            for elem in root.iter():
                custom_class = elem.get('customClass')
                if custom_class and cls._is_valid_identifier(custom_class):
                    if custom_class not in cls.SYSTEM_CLASSES:
                        result['classes'].add(custom_class)

                custom_module = elem.get('customModule')
                if custom_module and cls._is_valid_identifier(custom_module):
                    result['modules'].add(custom_module)

            for connection in root.iter('connection'):
                kind = connection.get('kind')
                property_name = connection.get('property')

                if kind == 'outlet' and property_name:
                    if cls._is_valid_identifier(property_name):
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

        except Exception:
            pass

        return dict(result)

    @staticmethod
    def _is_valid_identifier(name: str) -> bool:
        if not name or len(name) <= 1:
            return False

        if not (name[0].isalpha() or name[0] == '_'):
            return False

        for char in name:
            if not (char.isalnum() or char == '_'):
                return False

        return True


class PlistParser:
    """Plist 파일에서 식별자 추출 (바이너리/XML 자동 처리)"""

    @classmethod
    def parse(cls, file_path: Path) -> Dict[str, Set[str]]:
        result = defaultdict(set)

        # 1단계: plistlib으로 바이너리/XML 자동 감지
        try:
            with open(file_path, 'rb') as f:
                plist_data = plistlib.load(f)

            if isinstance(plist_data, dict):
                cls._parse_dict_native(plist_data, result, [])
                return dict(result)
        except Exception:
            pass

        # 2단계: XML 파싱 시도
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            main_dict = root.find('dict')
            if main_dict is not None:
                cls._parse_dict_xml(main_dict, result, [])
        except Exception:
            pass

        return dict(result)

    @classmethod
    def _parse_dict_native(cls, data: dict, result: defaultdict, key_path: List[str]):
        """Python dict로 파싱"""
        for key, value in data.items():
            if key == 'CFBundleURLSchemes' and isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        result['url_schemes'].add(item)

            elif key == 'CFBundleTypeName' and isinstance(value, str):
                result['document_types'].add(value)

            elif key == 'UTTypeIdentifier' and isinstance(value, str):
                result['uti_identifiers'].add(value)

            elif key == 'NSUserActivityTypes' and isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        result['user_activity_types'].add(item)

            elif key == 'BGTaskSchedulerPermittedIdentifiers' and isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        result['background_task_ids'].add(item)

            elif isinstance(value, dict):
                cls._parse_dict_native(value, result, key_path + [key])
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        cls._parse_dict_native(item, result, key_path + [key])

    @classmethod
    def _parse_dict_xml(cls, dict_elem, result: defaultdict, key_path: List[str]):
        """XML로 파싱"""
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

                    elif key == 'BGTaskSchedulerPermittedIdentifiers' and value_elem.tag == 'array':
                        for string_elem in value_elem.findall('string'):
                            if string_elem.text:
                                result['background_task_ids'].add(string_elem.text)

                    elif value_elem.tag == 'dict':
                        cls._parse_dict_xml(value_elem, result, key_path + [key])
                    elif value_elem.tag == 'array':
                        for child in value_elem:
                            if child.tag == 'dict':
                                cls._parse_dict_xml(child, result, key_path)

                    i += 2
                else:
                    i += 1
            else:
                i += 1


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

        except Exception:
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
                if key and cls._is_valid_key(key):
                    keys.add(key)

        except Exception:
            pass

        return keys

    @staticmethod
    def _is_valid_key(key: str) -> bool:
        """유효한 localization key인지 검사"""
        if not key or len(key) < 2:
            return False

        # 숫자나 특수문자로 시작하는 키 제외
        if key[0].isdigit() or not (key[0].isalnum() or key[0] in ('_', '-')):
            return False

        # 5단어 이상 문장 제외
        if ' ' in key and len(key.split()) > 5:
            return False

        return True


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

                        elif key == 'com.apple.developer.icloud-container-identifiers' and value_elem.tag == 'array':
                            for string_elem in value_elem.findall('string'):
                                if string_elem.text:
                                    result['icloud_containers'].add(string_elem.text)

                        i += 2
                    else:
                        i += 1
                else:
                    i += 1

        except Exception:
            pass

        return dict(result)


class AssetsParser:
    """Assets.xcassets에서 이미지/색상 이름 추출"""

    @classmethod
    def parse(cls, assets_path: Path) -> Dict[str, Set[str]]:
        result = defaultdict(set)

        if not assets_path.is_dir():
            return dict(result)

        try:
            for item in assets_path.rglob('*'):
                if item.is_dir():
                    if item.suffix == '.imageset':
                        result['images'].add(item.stem)
                    elif item.suffix == '.colorset':
                        result['colors'].add(item.stem)
                    elif item.suffix == '.dataset':
                        result['data_assets'].add(item.stem)
                    elif item.suffix == '.symbolset':
                        result['symbols'].add(item.stem)

        except Exception:
            pass

        return dict(result)


class ResourceCollector:
    """리소스 파일 수집기"""

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
        'assets': {
            'extensions': ['.xcassets'],
            'subdirectory': 'assets',
            'parser': AssetsParser,
            'is_directory': True
        },
    }

    def __init__(self, project_path: Path, output_dir: Path = Path('./resource'),
                 resource_types: Optional[List[str]] = None,
                 exclude_dirs: Optional[List[str]] = None,
                 preserve_structure: bool = False,
                 extract_identifiers: bool = False):
        self.project_path = Path(project_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.preserve_structure = preserve_structure
        self.extract_identifiers = extract_identifiers

        if resource_types is None:
            self.active_types = set(self.RESOURCE_TYPES.keys())
        else:
            self.active_types = set(resource_types)
            invalid = self.active_types - set(self.RESOURCE_TYPES.keys())
            if invalid:
                print(f"⚠️  알 수 없는 타입: {', '.join(invalid)}")
                print(f"   지원 타입: {', '.join(self.RESOURCE_TYPES.keys())}")

        self.exclude_dirs = exclude_dirs or [
            '.build', 'build', 'DerivedData', '.git', 'node_modules', 'Pods', 'Carthage'
        ]

        self.stats = defaultdict(lambda: {'found': 0, 'copied': 0, 'failed': 0})
        self.filename_counter = defaultdict(lambda: defaultdict(int))
        self.identifiers = defaultdict(lambda: defaultdict(set))

    def should_skip_directory(self, dir_path: Path) -> bool:
        dir_name = dir_path.name

        if dir_name.startswith('.') and dir_name not in ('.xcassets',):
            return True

        if dir_name in self.exclude_dirs:
            return True

        return False

    def get_resource_type(self, file_path: Path) -> Optional[str]:
        for type_name, type_info in self.RESOURCE_TYPES.items():
            if type_name not in self.active_types:
                continue

            for ext in type_info['extensions']:
                if file_path.suffix == ext:
                    return type_name

        return None

    def get_destination_path(self, resource_file: Path, resource_type: str) -> Path:
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
        type_info = self.RESOURCE_TYPES[resource_type]
        parser = type_info.get('parser')

        if parser is None:
            return

        try:
            if resource_type == 'strings':
                keys = parser.parse(resource_file)
                if keys:
                    self.identifiers[resource_type]['localization_keys'].update(keys)
            else:
                parsed = parser.parse(resource_file)
                for category, identifiers in parsed.items():
                    self.identifiers[resource_type][category].update(identifiers)
        except Exception:
            pass

    def find_and_collect_resources(self) -> Dict[str, int]:
        def scan_directory(directory: Path):
            try:
                for item in directory.iterdir():
                    if item.is_dir():
                        if not self.should_skip_directory(item):
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
                            # xcschememanagement 파일 제외
                            if 'xcschememanagement' in item.name.lower():
                                continue

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
        print(f"🔍 프로젝트: {self.project_path}")
        print(f"📂 저장 위치: {self.output_dir}")
        print(f"📁 구조 유지: {'예' if self.preserve_structure else '아니오 (평탄화)'}")
        print(f"🔎 식별자 추출: {'예' if self.extract_identifiers else '아니오'}")
        print(f"📦 수집 타입: {', '.join(sorted(self.active_types))}")
        print()

        if self.output_dir.exists():
            print(f"🗑️  기존 {self.output_dir} 삭제 중...")
            shutil.rmtree(self.output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)

        print("📝 리소스 파일 수집 중...")
        print("-" * 60)

        copied_counts = self.find_and_collect_resources()

        return copied_counts

    def print_summary(self):
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
  plist, xib, storyboard, coredata, strings, entitlements, assets

사용 예시:
  # 모든 리소스 수집
  python collect_resources.py /path/to/project

  # 특정 타입만 수집
  python collect_resources.py /path/to/project --types plist assets

  # 수집 + 식별자 추출 + JSON 저장
  python collect_resources.py /path/to/project --extract-identifiers --json identifiers.json
        """
    )

    parser.add_argument('project_path', type=Path, help='프로젝트 루트 경로')
    parser.add_argument('-o', '--output', type=Path, default=Path('./resource'),
                        help='리소스 파일을 저장할 디렉토리 (기본: ./resource)')
    parser.add_argument('--types', nargs='+', choices=list(ResourceCollector.RESOURCE_TYPES.keys()),
                        help='수집할 리소스 타입 지정 (미지정 시 전체)')
    parser.add_argument('--preserve-structure', action='store_true',
                        help='원본 폴더 구조 유지 (기본: 평탄화)')
    parser.add_argument('--extract-identifiers', action='store_true',
                        help='식별자 추출 수행')
    parser.add_argument('--json', type=Path,
                        help='식별자를 JSON 파일로 저장 (--extract-identifiers와 함께 사용)')
    parser.add_argument('--exclude', nargs='+',
                        help='제외할 디렉토리 추가')

    args = parser.parse_args()

    if not args.project_path.exists():
        print(f"❌ 경로를 찾을 수 없습니다: {args.project_path}")
        return 1

    if not args.project_path.is_dir():
        print(f"❌ 디렉토리가 아닙니다: {args.project_path}")
        return 1

    exclude_dirs = None
    if args.exclude:
        default_exclude = ['.build', 'build', 'DerivedData', '.git', 'node_modules', 'Pods', 'Carthage']
        exclude_dirs = default_exclude + args.exclude

    print("🚀 리소스 파일 수집기 v2 (Assets 지원 + 바이너리 Plist)")
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
    collector.print_summary()

    total_copied = sum(copied_counts.values())

    if total_copied > 0:
        print(f"\n✅ 완료! {total_copied}개의 리소스 파일이 복사되었습니다.")
    else:
        print("\n⚠️  복사된 파일이 없습니다.")

    if args.json and args.extract_identifiers:
        collector.save_identifiers_json(args.json)
    elif args.json and not args.extract_identifiers:
        print("\n⚠️  --json 옵션은 --extract-identifiers와 함께 사용해야 합니다.")

    return 0


if __name__ == "__main__":
    exit(main())