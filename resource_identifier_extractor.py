#!/usr/bin/env python3
"""
iOS/macOS 리소스 파일에서 식별자 추출기
XIB, Storyboard, Plist, CoreData, Strings, Entitlements에서 난독화 제외 대상 추출
"""

import re
import json
import argparse
from pathlib import Path
from typing import Set, Dict, List
from collections import defaultdict
import xml.etree.ElementTree as ET


class XIBStoryboardParser:
    """XIB/Storyboard 파일에서 식별자 추출"""

    @classmethod
    def parse(cls, file_path: Path) -> Dict[str, Set[str]]:
        result = defaultdict(set)

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Custom Class 이름
            for elem in root.iter():
                custom_class = elem.get('customClass')
                if custom_class and cls._is_valid_identifier(custom_class):
                    result['classes'].add(custom_class)

                custom_module = elem.get('customModule')
                if custom_module and cls._is_valid_identifier(custom_module):
                    result['modules'].add(custom_module)

            # IBOutlet/IBAction connections
            for connection in root.iter('connection'):
                kind = connection.get('kind')
                property_name = connection.get('property')

                if kind == 'outlet' and property_name:
                    result['outlets'].add(property_name)
                elif kind == 'action':
                    selector = connection.get('selector')
                    if selector:
                        result['actions'].add(selector)

            # Segue identifiers
            for segue in root.iter('segue'):
                identifier = segue.get('identifier')
                if identifier:
                    result['segue_identifiers'].add(identifier)

            # Reuse identifiers (UITableViewCell, UICollectionViewCell)
            for elem in root.iter():
                reuse_id = elem.get('reuseIdentifier')
                if reuse_id:
                    result['reuse_identifiers'].add(reuse_id)

            # Storyboard identifiers
            for elem in root.iter():
                storyboard_id = elem.get('storyboardIdentifier')
                if storyboard_id:
                    result['storyboard_identifiers'].add(storyboard_id)

            # Restoration identifiers
            for elem in root.iter():
                restoration_id = elem.get('restorationIdentifier')
                if restoration_id:
                    result['restoration_identifiers'].add(restoration_id)

            # User Defined Runtime Attributes (keyPath)
            for attr in root.iter('userDefinedRuntimeAttribute'):
                keypath = attr.get('keyPath')
                if keypath:
                    parts = keypath.split('.')
                    for part in parts:
                        if cls._is_valid_identifier(part):
                            result['runtime_attributes'].add(part)

        except Exception as e:
            print(f"⚠️  {file_path.name} 파싱 실패: {e}")

        return dict(result)

    @staticmethod
    def _is_valid_identifier(name: str) -> bool:
        if not name or len(name) <= 1:
            return False

        # 시스템 클래스 제외
        SYSTEM_CLASSES = {
            'UIResponder', 'UIViewController', 'UIView', 'UITableView',
            'UICollectionView', 'UIButton', 'UILabel', 'UIImageView',
            'UITableViewCell', 'UICollectionViewCell', 'UIScrollView',
            'UIStackView', 'UINavigationController', 'UITabBarController',
            'NSObject', 'NSManagedObject'
        }

        if name in SYSTEM_CLASSES:
            return False

        # Swift/ObjC 식별자 규칙
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
            print(f"⚠️  {file_path.name} 파싱 실패: {e}")

        return dict(result)

    @classmethod
    def _parse_dict(cls, dict_elem, result: defaultdict, key_path: List[str]):
        """재귀적으로 dict 파싱"""
        children = list(dict_elem)
        i = 0

        while i < len(children):
            if children[i].tag == 'key':
                key = children[i].text
                if i + 1 < len(children):
                    value_elem = children[i + 1]

                    # URL Schemes
                    if key == 'CFBundleURLSchemes' and value_elem.tag == 'array':
                        for string_elem in value_elem.findall('string'):
                            if string_elem.text:
                                result['url_schemes'].add(string_elem.text)

                    # Document Types
                    elif key == 'CFBundleTypeName' and value_elem.tag == 'string':
                        if value_elem.text:
                            result['document_types'].add(value_elem.text)

                    # UTI
                    elif key == 'UTTypeIdentifier' and value_elem.tag == 'string':
                        if value_elem.text:
                            result['uti_identifiers'].add(value_elem.text)

                    # NSUserActivityTypes
                    elif key == 'NSUserActivityTypes' and value_elem.tag == 'array':
                        for string_elem in value_elem.findall('string'):
                            if string_elem.text:
                                result['user_activity_types'].add(string_elem.text)

                    # 재귀: dict/array
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
        """배열 파싱"""
        for child in array_elem:
            if child.tag == 'dict':
                cls._parse_dict(child, result, key_path)


class CoreDataParser:
    """CoreData 모델 파일에서 식별자 추출"""

    @classmethod
    def parse(cls, model_path: Path) -> Dict[str, Set[str]]:
        result = defaultdict(set)

        # .xcdatamodeld는 디렉토리, 내부 .xcdatamodel 파일들 파싱
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

            # Entity 이름
            for entity in root.findall('.//entity'):
                name = entity.get('name')
                if name:
                    result['entities'].add(name)

                # Attributes
                for attr in entity.findall('attribute'):
                    attr_name = attr.get('name')
                    if attr_name:
                        result['attributes'].add(attr_name)

                # Relationships
                for rel in entity.findall('relationship'):
                    rel_name = rel.get('name')
                    if rel_name:
                        result['relationships'].add(rel_name)

            # Fetch Request Templates
            for fetch in root.findall('.//fetchRequest'):
                name = fetch.get('name')
                if name:
                    result['fetch_requests'].add(name)

        except Exception as e:
            print(f"⚠️  {contents_file.name} 파싱 실패: {e}")


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

        except Exception as e:
            print(f"⚠️  {file_path.name} 파싱 실패: {e}")

        return keys

    @staticmethod
    def _is_valid_key(key: str) -> bool:
        """유효한 localization key인지 검사"""
        # 너무 짧은 키 제외 (1글자)
        if len(key) <= 1:
            return False

        # 특수문자만 있는 키 제외
        if not any(c.isalnum() for c in key):
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

                        # App Groups
                        if key == 'com.apple.security.application-groups' and value_elem.tag == 'array':
                            for string_elem in value_elem.findall('string'):
                                if string_elem.text:
                                    result['app_groups'].add(string_elem.text)

                        # Keychain Groups
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
            print(f"⚠️  {file_path.name} 파싱 실패: {e}")

        return dict(result)


class ResourceScanner:
    """프로젝트 전체 리소스 스캔"""

    def __init__(self, project_path: Path, exclude_dirs: List[str] = None):
        self.project_path = Path(project_path)
        self.exclude_dirs = exclude_dirs or [
            '.build', 'build', 'DerivedData', '.git', 'node_modules',
        ]
        self.results = defaultdict(lambda: defaultdict(set))
        self.stats = defaultdict(int)

    def should_skip_directory(self, dir_path: Path) -> bool:
        dir_name = dir_path.name
        if dir_name.startswith('.') and dir_name != '.':
            return True
        if dir_name in self.exclude_dirs:
            return True
        return False

    def scan_all(self):
        print(f"🔍 프로젝트: {self.project_path}")
        print(f"📂 리소스 파일 검색 중...\n")

        self._scan_directory(self.project_path)

        print("\n" + "=" * 60)
        print("📊 추출 결과 요약")
        print("=" * 60)

        for file_type, categories in self.results.items():
            total = sum(len(ids) for ids in categories.values())
            print(f"\n[{file_type}]")
            for category, identifiers in sorted(categories.items()):
                if identifiers:
                    print(f"  {category:25s}: {len(identifiers):>6}개")

        print("\n" + "=" * 60)

    def _scan_directory(self, directory: Path):
        try:
            for item in directory.iterdir():
                if item.is_dir():
                    if not self.should_skip_directory(item):
                        # CoreData 모델
                        if item.suffix == '.xcdatamodeld':
                            print(f"✓ CoreData: {item.name}")
                            parsed = CoreDataParser.parse(item)
                            self._merge_results('CoreData', parsed)
                            self.stats['coredata'] += 1
                        else:
                            self._scan_directory(item)

                elif item.is_file():
                    # XIB
                    if item.suffix == '.xib':
                        print(f"✓ XIB: {item.name}")
                        parsed = XIBStoryboardParser.parse(item)
                        self._merge_results('XIB/Storyboard', parsed)
                        self.stats['xib'] += 1

                    # Storyboard
                    elif item.suffix == '.storyboard':
                        print(f"✓ Storyboard: {item.name}")
                        parsed = XIBStoryboardParser.parse(item)
                        self._merge_results('XIB/Storyboard', parsed)
                        self.stats['storyboard'] += 1

                    # Plist
                    elif item.suffix == '.plist':
                        print(f"✓ Plist: {item.name}")
                        parsed = PlistParser.parse(item)
                        self._merge_results('Plist', parsed)
                        self.stats['plist'] += 1

                    # Strings
                    elif item.suffix == '.strings':
                        print(f"✓ Strings: {item.name}")
                        keys = StringsFileParser.parse(item)
                        if keys:
                            self.results['Strings']['localization_keys'].update(keys)
                        self.stats['strings'] += 1

                    # Entitlements
                    elif item.suffix == '.entitlements':
                        print(f"✓ Entitlements: {item.name}")
                        parsed = EntitlementsParser.parse(item)
                        self._merge_results('Entitlements', parsed)
                        self.stats['entitlements'] += 1

        except PermissionError:
            pass

    def _merge_results(self, file_type: str, parsed: Dict[str, Set[str]]):
        for category, identifiers in parsed.items():
            self.results[file_type][category].update(identifiers)

    def get_all_identifiers(self) -> Set[str]:
        """모든 식별자 통합"""
        all_ids = set()
        for file_type, categories in self.results.items():
            for identifiers in categories.values():
                all_ids.update(identifiers)
        return all_ids

    def save_to_json(self, output_path: Path):
        """JSON 저장"""
        output_data = {
            "project_path": str(self.project_path),
            "description": "난독화에서 제외해야 할 리소스 파일 식별자 목록",
            "statistics": dict(self.stats),
            "identifiers_by_file_type": {}
        }

        for file_type, categories in self.results.items():
            output_data["identifiers_by_file_type"][file_type] = {
                category: sorted(list(identifiers))
                for category, identifiers in categories.items()
            }

        all_ids = self.get_all_identifiers()
        output_data["all_identifiers"] = sorted(list(all_ids))
        output_data["total_identifiers"] = len(all_ids)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 JSON 저장: {output_path}")

    def save_to_txt(self, output_path: Path):
        """TXT 저장"""
        all_ids = self.get_all_identifiers()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for identifier in sorted(all_ids):
                f.write(identifier + '\n')
        print(f"💾 TXT 저장: {output_path} ({len(all_ids)}개)")


def main():
    parser = argparse.ArgumentParser(
        description="iOS/macOS 리소스 파일에서 난독화 제외 대상 식별자 추출",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('project_path', type=Path, help='프로젝트 루트 경로')
    parser.add_argument('-o', '--output', type=Path, help='JSON 파일 경로')
    parser.add_argument('--txt', type=Path, help='TXT 파일 경로')
    parser.add_argument('--exclude', nargs='+', help='제외할 디렉토리')

    args = parser.parse_args()

    if not args.project_path.exists():
        print(f"❌ 경로를 찾을 수 없습니다: {args.project_path}")
        return 1

    if not args.project_path.is_dir():
        print(f"❌ 디렉토리가 아닙니다: {args.project_path}")
        return 1

    exclude_dirs = None
    if args.exclude:
        default_exclude = ['.build', 'build', 'DerivedData', '.git', 'node_modules']
        exclude_dirs = default_exclude + args.exclude

    print("🚀 iOS/macOS 리소스 식별자 추출기")
    print("   (XIB, Storyboard, Plist, CoreData, Strings, Entitlements)")
    print("=" * 60)
    print()

    scanner = ResourceScanner(args.project_path, exclude_dirs)
    scanner.scan_all()

    if args.output:
        scanner.save_to_json(args.output)

    if args.txt:
        scanner.save_to_txt(args.txt)

    print("\n✅ 완료!")
    print("💡 이 식별자들은 리소스 파일에서 참조되므로 난독화에서 제외해야 합니다.")
    return 0


if __name__ == "__main__":
    exit(main())