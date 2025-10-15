import os
from pathlib import Path


def find_common_identifiers(directory: Path):
    """
    지정된 디렉토리 내의 모든 .txt 파일에서 공통으로 나타나는
    식별자(한 줄에 하나씩)의 집합을 찾습니다.

    Args:
        directory: .txt 파일들이 포함된 디렉토리의 Path 객체

    Returns:
        모든 파일에 공통으로 존재하는 식별자들의 set.
    """
    # 디렉토리 존재 여부 확인
    if not directory.is_dir():
        print(f"❌ 오류: '{directory}' 디렉토리를 찾을 수 없습니다.")
        print("   스크립트를 프로젝트 루트 디렉토리에서 실행하고 있는지 확인하세요.")
        return None

    # 디렉토리 내의 모든 .txt 파일 경로를 가져옵니다.
    txt_files = list(directory.glob('*.txt'))

    if not txt_files:
        print(f"❌ 오류: '{directory}' 디렉토리에서 .txt 파일을 찾을 수 없습니다.")
        return None

    print(f"🔍 총 {len(txt_files)}개의 룰베이스 파일을 분석합니다:")
    for f in txt_files:
        print(f"  - {f.name}")
    print("-" * 50)

    try:
        # 첫 번째 파일의 내용을 기준으로 초기 세트를 만듭니다.
        # 각 줄의 앞뒤 공백을 제거하고 비어있지 않은 줄만 세트에 추가합니다.
        common_identifiers = {line.strip() for line in txt_files[0].read_text(encoding='utf-8').splitlines() if
                              line.strip()}

        # 나머지 파일들을 순회하며 교집합을 구합니다.
        for file_path in txt_files[1:]:
            file_identifiers = {line.strip() for line in file_path.read_text(encoding='utf-8').splitlines() if
                                line.strip()}

            # intersection_update는 현재 세트를 두 세트의 교집합으로 업데이트합니다.
            common_identifiers.intersection_update(file_identifiers)

            # 만약 중간에 공통 식별자가 하나도 없게 되면 더 이상 진행할 필요가 없습니다.
            if not common_identifiers:
                break

        return common_identifiers

    except Exception as e:
        print(f"🚨 파일을 읽는 중 오류가 발생했습니다: {e}")
        return None


def main():
    """스크립트의 메인 실행 함수"""
    # 스크립트가 위치한 곳을 기준으로 'rule_base' 디렉토리 경로를 설정합니다.
    # 이렇게 하면 어디서 실행하든 경로가 정확해집니다.
    script_dir = Path(__file__).parent
    rule_base_directory = script_dir / 'rule_base'

    # 공통 식별자를 찾습니다.
    common_ids = find_common_identifiers(rule_base_directory)

    # 결과 출력
    if common_ids is not None:
        if common_ids:
            # 결과를 알파벳 순으로 정렬합니다.
            sorted_common_ids = sorted(list(common_ids))
            print(
                f"\n✅ 총 {len(sorted_common_ids)}개의 공통 식별자를 찾았습니다 (모든 {len(list(rule_base_directory.glob('*.txt')))}개 파일에 존재):")
            print("=" * 50)
            for identifier in sorted_common_ids:
                print(f"  • {identifier}")
        else:
            print("\n❌ 모든 파일에 공통으로 포함된 식별자를 찾지 못했습니다.")


if __name__ == "__main__":
    main()