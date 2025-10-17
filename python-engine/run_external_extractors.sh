#!/bin/bash
#
# 리소스와 헤더 파일에서 제외할 식별자 목록을 추출하는 스크립트
#
# 사용법:
# ./run_external_extractors.sh <project_path> <output_file> [real_project_name]

# --- 설정 ---
PROJECT_PATH=$1
OUTPUT_FILE=$2
REAL_PROJECT_NAME=$3  # 선택적: 실제 프로젝트 이름 (DerivedData 검색용)
SCRIPT_DIR=$(dirname "$0")

# --- 유효성 검사 ---
if [ -z "$PROJECT_PATH" ] || [ -z "$OUTPUT_FILE" ]; then
  echo "❌ Error: Project path and output file must be provided."
  echo "Usage: $0 <project_path> <output_file> [real_project_name]"
  exit 1
fi

echo "🚀 Starting External Identifier Extraction..."
echo "============================================================"

# --- 출력 디렉토리 생성 ---
mkdir -p "$(dirname "$OUTPUT_FILE")"

# --- 임시 파일 생성 ---
HEADER_TMP=$(mktemp)
RESOURCE_TMP=$(mktemp)

# --- 각 추출기 실행 ---
echo "1/2: 📝 Analyzing Objective-C headers..."

# 실제 프로젝트 이름이 제공되었으면 --real-project-name 인자로 전달
if [ -n "$REAL_PROJECT_NAME" ]; then
    python3 "${SCRIPT_DIR}/external_extractors/header_extractor.py" "$PROJECT_PATH" --txt "$HEADER_TMP" --real-project-name "$REAL_PROJECT_NAME"
else
    python3 "${SCRIPT_DIR}/external_extractors/header_extractor.py" "$PROJECT_PATH" --txt "$HEADER_TMP"
fi
echo "Done."

echo "\n2/2: 📂 Analyzing resource files (XIB, Storyboard, etc.)..."
python3 "${SCRIPT_DIR}/external_extractors/resource_identifier_extractor.py" "$PROJECT_PATH" --txt "$RESOURCE_TMP"
echo "Done."

# --- 결과 병합 및 정리 ---
echo "\n✨ Merging and cleaning up results..."
cat "$HEADER_TMP" "$RESOURCE_TMP" | sort | uniq > "$OUTPUT_FILE"

# --- 임시 파일 삭제 ---
rm "$HEADER_TMP" "$RESOURCE_TMP"

echo "============================================================"
echo "✅ External exclusion list created successfully!"
echo "   - Output: ${OUTPUT_FILE}"
echo "   - Total Unique Identifiers: $(wc -l < ${OUTPUT_FILE} | xargs)"