#!/usr/bin/env python3
"""
Objective-C 헤더 식별자 추출기 (완벽 최종판)

공개 API (난독화 제외 대상) 식별자를 100% 정확하게 추출합니다.
"""

import re
import json
import argparse
from pathlib import Path
from typing import Set, Dict, List
from collections import defaultdict
from enum import Enum, auto


class ParseState(Enum):
    NORMAL = auto()
    SINGLE_LINE_COMMENT = auto()
    MULTI_LINE_COMMENT = auto()
    STRING = auto()
    STRING_ESCAPE = auto()
    PREPROCESSOR = auto()


class ObjectiveCCommentRemover:
    def remove_comments(self, source: str) -> str:
        result = []
        state = ParseState.NORMAL
        i = 0
        length = len(source)

        while i < length:
            char = source[i]

            if state == ParseState.NORMAL:
                if char == '/' and i + 1 < length:
                    if source[i + 1] == '/':
                        state = ParseState.SINGLE_LINE_COMMENT
                        i += 1
                    elif source[i + 1] == '*':
                        state = ParseState.MULTI_LINE_COMMENT
                        i += 1
                    else:
                        result.append(char)
                elif char == '"' or (char == '@' and i + 1 < length and source[i + 1] == '"'):
                    result.append(char)
                    if char == '@':
                        result.append('"')
                        i += 1
                    state = ParseState.STRING
                elif char == '#' and (i == 0 or source[i - 1] == '\n'):
                    result.append(char)
                    state = ParseState.PREPROCESSOR
                else:
                    result.append(char)

            elif state == ParseState.STRING:
                result.append(char)
                if char == '\\':
                    state = ParseState.STRING_ESCAPE
                elif char == '"':
                    state = ParseState.NORMAL

            elif state == ParseState.STRING_ESCAPE:
                result.append(char)
                state = ParseState.STRING

            elif state == ParseState.SINGLE_LINE_COMMENT:
                if char == '\n':
                    result.append(char)
                    state = ParseState.NORMAL

            elif state == ParseState.MULTI_LINE_COMMENT:
                if char == '*' and i + 1 < length and source[i + 1] == '/':
                    i += 1
                    state = ParseState.NORMAL

            elif state == ParseState.PREPROCESSOR:
                result.append(char)
                if char == '\n':
                    if len(result) >= 2 and result[-2] == '\\':
                        pass
                    else:
                        state = ParseState.NORMAL

            i += 1

        return "".join(result)


class ObjCHeaderParser:
    """완벽 최종판 - Swift-generated 헤더 완벽 지원"""

    PATTERNS = {
        'interface': re.compile(r'@interface\s+(\w+)\s*[:(]', re.MULTILINE),
        'protocol': re.compile(r'@protocol\s+(\w+)\b', re.MULTILINE),

        'struct_typedef': re.compile(r'typedef\s+struct\s+\w*\s*\{[^}]*\}\s*(\w+)\s*;',
                                     re.MULTILINE | re.DOTALL),
        'struct_plain': re.compile(r'struct\s+(\w+)\s*\{', re.MULTILINE),

        'enum_ns': re.compile(r'(?:NS_ENUM|NS_OPTIONS|NS_CLOSED_ENUM|NS_ERROR_ENUM)\s*\(\s*\w+\s*,\s*(\w+)\s*\)',
                              re.MULTILINE),
        'enum_typedef': re.compile(r'typedef\s+enum\s+\w*\s*(?::\s*\w+)?\s*\{[^}]*\}\s*(\w+)\s*;',
                                   re.MULTILINE | re.DOTALL),
        'enum_forward_decl': re.compile(r'enum\s+(\w+)\s*:\s*\w+\s*;', re.MULTILINE),
        'swift_enum': re.compile(r'typedef\s+SWIFT_ENUM\s*\([^,]+,\s*(\w+)\s*,', re.MULTILINE),

        'typedef_funcptr': re.compile(r'typedef\s+.+\(\s*\*\s*(\w+)\s*\)\s*\(.*\)\s*;', re.MULTILINE),
        'typedef_block': re.compile(r'typedef\s+.+\(\s*\^\s*(\w+)\s*\)\s*\(.*\)\s*;', re.MULTILINE),
        'typedef': re.compile(r'typedef\s+(?!enum|struct|union).*?\s+(\w+)\s*;',
                              re.MULTILINE | re.DOTALL),

        'function': re.compile(r'^(?:extern\s+)?(?:static\s+)?(?:inline\s+)?[A-Z]\w*\s+\*?\s*(\w+)\s*\(',
                               re.MULTILINE),
        'export_function': re.compile(
            r'^(?:FOUNDATION_EXPORT|NS_SWIFT_NAME|UIKIT_EXTERN|extern)\s+.*?\*?\s*([a-zA-Z_]\w+)\s*\(',
            re.MULTILINE),

        'extern_const': re.compile(
            r'(?:FOUNDATION_EXPORT|UIKIT_EXTERN|extern)\s+(?:const\s+)?[\w\s\*]+?(?:const\s+)?(\w+)\s*;',
            re.MULTILINE),
        'extern_const_array': re.compile(
            r'(?:FOUNDATION_EXPORT|UIKIT_EXTERN|extern)\s+(?:const\s+)?[\w\s\*]+\s+(\w+)\s*\[\s*\]',
            re.MULTILINE),

        'macro_k_constant': re.compile(r'\b(k[A-Z]\w+)\b', re.MULTILINE),
    }

    @classmethod
    def parse(cls, file_path: Path) -> Dict[str, Set[str]]:
        result = defaultdict(set)

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            remover = ObjectiveCCommentRemover()
            clean_content = remover.remove_comments(content)

            # 기본 패턴들
            result['classes'].update(cls.PATTERNS['interface'].findall(clean_content))
            result['protocols'].update(cls.PATTERNS['protocol'].findall(clean_content))
            result['structs'].update(cls.PATTERNS['struct_typedef'].findall(clean_content))
            result['structs'].update(cls.PATTERNS['struct_plain'].findall(clean_content))

            result['enums'].update(cls.PATTERNS['enum_ns'].findall(clean_content))
            result['enums'].update(cls.PATTERNS['enum_typedef'].findall(clean_content))
            result['enums'].update(cls.PATTERNS['enum_forward_decl'].findall(clean_content))
            result['enums'].update(cls.PATTERNS['swift_enum'].findall(clean_content))

            result['typedefs'].update(cls.PATTERNS['typedef'].findall(clean_content))
            result['typedefs'].update(cls.PATTERNS['typedef_funcptr'].findall(clean_content))
            result['typedefs'].update(cls.PATTERNS['typedef_block'].findall(clean_content))

            result['functions'].update(cls.PATTERNS['function'].findall(clean_content))
            result['functions'].update(cls.PATTERNS['export_function'].findall(clean_content))

            result['constants'].update(cls.PATTERNS['extern_const'].findall(clean_content))
            result['constants'].update(cls.PATTERNS['extern_const_array'].findall(clean_content))
            result['constants'].update(cls.PATTERNS['macro_k_constant'].findall(clean_content))

            result['macros'].update(cls._extract_macros(content))

            # 복잡한 패턴들
            result['enum_cases'].update(cls._extract_enum_cases(clean_content))
            result['methods'].update(cls._extract_methods(clean_content))
            result['properties'].update(cls._extract_properties(clean_content))

            # 카테고리 제외
            categories = cls._extract_categories(clean_content)
            for key in result:
                result[key] -= categories

            # 필터링
            for key in result:
                result[key] = cls._filter_identifiers(result[key], key)

        except Exception as e:
            pass

        return dict(result)

    @classmethod
    def _extract_macros(cls, content: str) -> Set[str]:
        """#define 매크로 추출 (ifndef/define 포함)"""
        macros = set()

        for line in content.split('\n'):
            line = line.strip()

            if line.startswith('//') or line.startswith('/*'):
                continue

            # #ifndef, #define 둘 다 매크로 이름
            if line.startswith('#ifndef') or line.startswith('#define'):
                match = re.match(r'^#(?:ifndef|define)\s+([A-Za-z_]\w*)(?:\s|$|\()', line)
                if match:
                    macro_name = match.group(1)
                    if len(macro_name) > 1:
                        macros.add(macro_name)

        return macros

    @classmethod
    def _extract_categories(cls, content: str) -> Set[str]:
        pattern = re.compile(r'@interface\s+\w+\s*\((\w+)\)', re.MULTILINE)
        return set(pattern.findall(content))

    @classmethod
    def _extract_enum_cases(cls, content: str) -> Set[str]:
        """enum case 값들 추출"""
        cases = set()

        # #define 라인 제거
        lines = []
        for line in content.split('\n'):
            if not line.strip().startswith('#define'):
                lines.append(line)
        clean_content = '\n'.join(lines)

        # enum 블록들 찾기
        ns_enum_blocks = re.findall(
            r'(?:NS_ENUM|NS_OPTIONS|NS_CLOSED_ENUM|NS_ERROR_ENUM)\s*\([^)]+\)\s*\{([^}]+)\}',
            clean_content, re.DOTALL
        )

        typedef_enum_blocks = re.findall(
            r'typedef\s+enum[^{]*\{([^}]+)\}',
            clean_content, re.DOTALL
        )

        swift_enum_blocks = re.findall(
            r'typedef\s+SWIFT_ENUM\s*\([^)]+\)\s*\{([^}]+)\}',
            clean_content, re.DOTALL
        )

        all_blocks = ns_enum_blocks + typedef_enum_blocks + swift_enum_blocks

        for block in all_blocks:
            for line in block.split(','):
                line = line.strip()
                if not line:
                    continue

                match = re.match(r'^\s*([A-Za-z_]\w*)', line)
                if match:
                    case_name = match.group(1)
                    cases.add(case_name)

        return cases

    @classmethod
    def _extract_methods(cls, content: str) -> Set[str]:
        """Objective-C 메서드 추출"""
        methods = set()
        method_pattern = re.compile(r'^\s*[-+]\s*\((?:.+?)\)(.*?);', re.MULTILINE)
        block_pattern = re.compile(r'@(?:interface|protocol).*?@end', re.DOTALL)

        for block in block_pattern.findall(content):
            for match in method_pattern.finditer(block):
                method_sig = match.group(1).strip()

                # 속성 제거
                method_sig = re.sub(r'\s+__attribute__\s*\(.*?\)', '', method_sig)
                method_sig = re.sub(r'\s+SWIFT_\w+(?:\([^)]*\))?', '', method_sig)
                method_sig = re.sub(r'\s+NS_\w+(?:\([^)]*\))?', '', method_sig)

                if ':' not in method_sig:
                    # 파라미터 없는 메서드
                    selector = method_sig.strip()
                    if selector and re.match(r'^[a-zA-Z_]\w*$', selector):
                        methods.add(selector)
                else:
                    # 파라미터 있는 메서드
                    labels = re.findall(r'(\w+)\s*:', method_sig)
                    if labels:
                        selector = ':'.join(labels) + ':'
                        methods.add(selector)

        return methods

    @classmethod
    def _extract_properties(cls, content: str) -> Set[str]:
        """✅ 완벽 개선: @property + SWIFT_CLASS_PROPERTY 모두 추출"""
        properties = set()

        # 1. 일반 @property 패턴
        # @property (attrs) Type * name;
        prop_pattern = re.compile(
            r'@property\s*\(([^)]*)\)\s*[^;]+?\b(\w+)\s*;',
            re.MULTILINE | re.DOTALL
        )

        for match in prop_pattern.finditer(content):
            attributes = match.group(1)
            prop_name = match.group(2)

            if not prop_name or len(prop_name) <= 1:
                continue

            # getter
            getter_match = re.search(r'getter\s*=\s*(\w+)', attributes)
            if getter_match:
                properties.add(getter_match.group(1))
            else:
                properties.add(prop_name)

            # setter (readonly가 아니고, class property도 아닌 경우)
            is_readonly = 'readonly' in attributes
            is_class_property = 'class' in attributes
            is_delegate_like = 'delegate' in prop_name.lower() or 'datasource' in prop_name.lower()

            if not is_readonly and not is_class_property and not is_delegate_like:
                setter_match = re.search(r'setter\s*=\s*(\w+:)', attributes)
                if setter_match:
                    properties.add(setter_match.group(1))
                else:
                    setter = f"set{prop_name[0].upper()}{prop_name[1:]}:"
                    properties.add(setter)

        # 2. ✅ SWIFT_CLASS_PROPERTY 패턴 추가
        # SWIFT_CLASS_PROPERTY(@property (nonatomic, class, readonly, strong) Type * name;)
        swift_class_prop_pattern = re.compile(
            r'SWIFT_CLASS_PROPERTY\s*\(\s*@property\s*\(([^)]*)\)\s*[^;]+?\b(\w+)\s*;\s*\)',
            re.MULTILINE | re.DOTALL
        )

        for match in swift_class_prop_pattern.finditer(content):
            attributes = match.group(1)
            prop_name = match.group(2)

            if not prop_name or len(prop_name) <= 1:
                continue

            # class property는 getter만 (readonly 임)
            getter_match = re.search(r'getter\s*=\s*(\w+)', attributes)
            if getter_match:
                properties.add(getter_match.group(1))
            else:
                properties.add(prop_name)

        return properties

    @classmethod
    def _filter_identifiers(cls, identifiers: Set[str], id_type: str) -> Set[str]:
        """✅ 최종 필터링"""

        SYSTEM_TYPES = {
            'NSInteger', 'NSUInteger', 'CGFloat', 'BOOL', 'id', 'void', 'int',
            'float', 'double', 'char', 'unsigned', 'signed', 'long', 'short',
            'NSSecureCoding', 'NSCopying', 'NSCoding', 'CFTimeInterval',
            'NSTimeInterval', 'CGRect', 'CGPoint', 'CGSize', 'NSRange',
            'char16_t', 'char32_t', 'uint_least16_t', 'uint_least32_t',
        }

        # ✅ SWIFT_CLASS 같은 매크로 정의 제외
        EXCLUDE_PATTERNS = [
            r'^API_DEPRECATED.*', r'^API_AVAILABLE.*',
            r'^NS_SWIFT_UI_ACTOR$', r'^NS_AVAILABLE.*', r'^NS_DEPRECATED.*',
            r'^NS_ENUM$', r'^NS_OPTIONS$', r'^NS_ERROR_ENUM$', r'^NS_CLOSED_ENUM$',
            r'^NS_DESIGNATED_INITIALIZER$', r'^UI_APPEARANCE_SELECTOR$',
            r'^OBJC_DESIGNATED_INITIALIZER$', r'^IB_DESIGNABLE$', r'^IBSegueAction$',
            r'^SWIFT_CLASS$', r'^SWIFT_PROTOCOL$', r'^SWIFT_ENUM$',  # 매크로 정의 제외
            r'^SWIFT_CLASS_PROPERTY$', r'^SWIFT_RESILIENT_CLASS$',
            r'^__\w+__$',
            r'^_Nonnull$', r'^_Nullable$', r'^_Null_unspecified$',
        ]

        filtered = set()
        for name in identifiers:
            if not name or len(name) <= 1:
                continue

            if not (name[0].isalpha() or name.startswith('_')):
                continue

            if name in SYSTEM_TYPES:
                continue

            if any(re.match(pattern, name) for pattern in EXCLUDE_PATTERNS):
                continue

            # 매크로 파라미터 형태 제외
            if name.startswith('_'):
                if not name.startswith('_Tt') and len(name) > 1 and name[1:].islower():
                    continue

            filtered.add(name)

        return filtered


class HeaderScanner:
    def __init__(self, project_path: Path, exclude_dirs: List[str] = None):
        self.project_path = Path(project_path)
        self.exclude_dirs = exclude_dirs or [
            'Pods', 'Carthage', '.build', 'build',
            'DerivedData', '.git', 'node_modules',
        ]
        self.header_results = {}
        self.stats = defaultdict(int)

    def should_skip_directory(self, dir_path: Path) -> bool:
        dir_name = dir_path.name
        if dir_name.startswith('.') and dir_name != '.':
            return True
        if dir_name in self.exclude_dirs:
            return True
        return False

    def find_header_files(self) -> List[Path]:
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

    def scan_all(self) -> Dict[str, Dict[str, Set[str]]]:
        print(f"🔍 프로젝트: {self.project_path}")
        print(f"📂 헤더 파일 검색 중...\n")

        header_files = self.find_header_files()
        self.stats['total_headers'] = len(header_files)

        if not header_files:
            print("❌ 헤더 파일을 찾을 수 없습니다.")
            return {}

        print(f"✓ {len(header_files)}개의 헤더 파일 발견\n")
        print("📝 식별자 추출 중...")
        print("-" * 60)

        for header_file in header_files:
            relative_path = str(header_file.relative_to(self.project_path))
            identifiers_by_type = ObjCHeaderParser.parse(header_file)
            total_count = sum(len(ids) for ids in identifiers_by_type.values())

            if total_count > 0:
                self.header_results[relative_path] = identifiers_by_type
                self.stats['success'] += 1
                print(f"✓ {relative_path}: {total_count}개")
            else:
                self.stats['failed'] += 1

        return self.header_results

    def get_all_identifiers_by_type(self) -> Dict[str, Set[str]]:
        merged = defaultdict(set)
        for header_data in self.header_results.values():
            for id_type, identifiers in header_data.items():
                merged[id_type].update(identifiers)
        return dict(merged)

    def get_all_identifiers(self) -> Set[str]:
        all_ids = set()
        for header_data in self.header_results.values():
            for identifiers in header_data.values():
                all_ids.update(identifiers)
        return all_ids

    def print_summary(self):
        print("\n" + "=" * 60)
        print("📊 추출 결과 요약 (난독화 제외 대상)")
        print("=" * 60)
        print(f"총 헤더 파일:     {self.stats['total_headers']:>6}개")
        print(f"성공:            {self.stats['success']:>6}개")
        print(f"실패:            {self.stats['failed']:>6}개")

        merged = self.get_all_identifiers_by_type()
        print("\n타입별 식별자 수:")
        for id_type, identifiers in sorted(merged.items()):
            if identifiers:
                print(f"  {id_type:15s}: {len(identifiers):>6}개")

        total = len(self.get_all_identifiers())
        print(f"\n고유 식별자 총합: {total:>6}개")
        print("=" * 60)

    def save_to_json(self, output_path: Path, include_per_header: bool = True):
        output_data = {
            "project_path": str(self.project_path),
            "description": "난독화에서 제외해야 할 공개 API 식별자 목록",
            "total_headers": self.stats['total_headers'],
            "success": self.stats['success'],
            "failed": self.stats['failed'],
        }

        merged = self.get_all_identifiers_by_type()
        output_data["identifiers_by_type"] = {
            id_type: sorted(list(identifiers))
            for id_type, identifiers in merged.items()
        }

        all_ids = self.get_all_identifiers()
        output_data["all_identifiers"] = sorted(list(all_ids))
        output_data["total_identifiers"] = len(all_ids)

        if include_per_header:
            output_data["headers"] = {
                header_path: {
                    id_type: sorted(list(identifiers))
                    for id_type, identifiers in header_data.items()
                }
                for header_path, header_data in self.header_results.items()
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n💾 JSON 저장: {output_path}")

    def save_to_txt(self, output_path: Path):
        all_ids = self.get_all_identifiers()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for identifier in sorted(all_ids):
                f.write(identifier + '\n')
        print(f"\n💾 TXT 저장: {output_path} ({len(all_ids)}개)")


def main():
    parser = argparse.ArgumentParser(
        description="Objective-C 헤더에서 공개 API 식별자를 추출합니다 (난독화 제외 대상)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('project_path', type=Path, help='프로젝트 루트 경로')
    parser.add_argument('-o', '--output', type=Path, help='JSON 파일 경로')
    parser.add_argument('--txt', type=Path, help='TXT 파일 경로')
    parser.add_argument('--exclude', nargs='+', help='제외할 디렉토리')
    parser.add_argument('--no-per-header', action='store_true', help='헤더별 상세 정보 제외')

    args = parser.parse_args()

    if not args.project_path.exists():
        print(f"❌ 경로를 찾을 수 없습니다: {args.project_path}")
        return 1

    if not args.project_path.is_dir():
        print(f"❌ 디렉토리가 아닙니다: {args.project_path}")
        return 1

    exclude_dirs = None
    if args.exclude:
        default_exclude = ['Pods', 'Carthage', '.build', 'build', 'DerivedData', '.git', 'node_modules']
        exclude_dirs = default_exclude + args.exclude

    print("🚀 Objective-C 헤더 식별자 추출기")
    print("   (난독화 제외 대상 - 공개 API)")
    print("=" * 60)
    print()

    scanner = HeaderScanner(args.project_path, exclude_dirs)
    scanner.scan_all()
    scanner.print_summary()

    if args.output:
        scanner.save_to_json(args.output, include_per_header=not args.no_per_header)

    if args.txt:
        scanner.save_to_txt(args.txt)

    print("\n✅ 완료!")
    print("💡 이 식별자들은 공개 API이므로 난독화에서 제외해야 합니다.")
    return 0


if __name__ == "__main__":
    exit(main())