#!/bin/bash

# 단일 프로젝트의 전체 분석 파이프라인을 실행하는 스크립트
# 사용법: ./run_analysis.sh <프로젝트_디렉토리_이름> <정답_파일_이름>
# 예시:   ./run_analysis.sh test_project8 uikit1.txt

# --- 인자 유효성 검사 ---
if [ "$#" -ne 2 ]; then
    echo "❌ 오류: 인자 개수가 올바르지 않습니다."
    echo "사용법: $0 <프로젝트_디렉토리_이름> <정답_파일_이름>"
    exit 1
fi

# --- 설정 ---
PROJECT_NAME=$1
RULE_BASE_NAME=$2

PROJECT_PATH="project/${PROJECT_NAME}"
RULE_BASE_PATH="rule_base/${RULE_BASE_NAME}"
OUTPUT_DIR="output/${PROJECT_NAME}_results" # 각 프로젝트별로 독립된 결과 폴더 생성

# --- 메인 실행 로직 ---
echo "========================================================================"
echo "🚀 전체 분석 파이프라인 시작: ${PROJECT_NAME}"
echo "========================================================================"
echo

# 1. 이전 결과물을 정리하고 이번 실행을 위한 새 디렉토리 생성
echo "🧹 [0/4 단계] 이전 결과 정리 중..."
rm -rf ${OUTPUT_DIR}
mkdir -p ${OUTPUT_DIR}
echo "   -> 결과는 ${OUTPUT_DIR} 폴더에 저장됩니다."
echo

# 2. 외부 식별자 추출 (Python)
echo "🐍 [1/4 단계] 외부 식별자 추출 중..."
(cd python-engine && ./run_external_extractors.sh ../${PROJECT_PATH} ../${OUTPUT_DIR}/external_exclusions.txt)
echo

# 3. Swift Extractor 빌드 및 실행
echo "🐦 [2/4 단계] Swift Extractor 빌드 및 심볼 그래프 생성 중..."
(cd swift-extractor && swift build -c release && ./.build/release/SymbolExtractor ../${PROJECT_PATH} --output ../${OUTPUT_DIR}/symbol_graph.json --external-exclusion-list ../${OUTPUT_DIR}/external_exclusions.txt)
echo

# 4. 파이썬 규칙 엔진 실행
echo "⚙️  [3/4 단계] 파이썬 규칙 엔진으로 분석 실행 중..."
(cd python-engine && python3 main.py ../${OUTPUT_DIR}/symbol_graph.json --output ../${OUTPUT_DIR}/final_exclusion_list.json --txt-output ../${OUTPUT_DIR}/final_exclusion_list.txt)
echo

# 5. 결과 비교
echo "📊 [4/4 단계] 정답지와 결과 비교 중..."
python3 compare_results.py ${RULE_BASE_PATH} ${OUTPUT_DIR}/final_exclusion_list.txt
echo

echo "========================================================================"
echo "🎉 분석 완료: ${PROJECT_NAME}"
echo "========================================================================"
echo
