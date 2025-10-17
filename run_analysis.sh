#!/bin/bash

# 단일 프로젝트의 전체 분석 파이프라인을 실행하는 스크립트 (최종 수정판)
# 사용법: ./run_analysis.sh <프로젝트_디렉토리_이름> <정답_파일_이름>

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
OUTPUT_DIR="output/$(echo ${PROJECT_NAME} | sed 's/\//_/g')_results"

# --- 프로젝트 존재 여부 확인 ---
if [ ! -d "${PROJECT_PATH}" ]; then
    echo "❌ 오류: 프로젝트 디렉토리를 찾을 수 없습니다: ${PROJECT_PATH}"
    exit 1
fi

# --- 메인 실행 로직 ---
echo "========================================================================"
echo "🚀 전체 분석 파이프라인 시작: ${PROJECT_NAME}"
echo "========================================================================"
echo

# 0. 이전 결과물 정리
echo "🧹 [0/5 단계] 이전 결과 정리 중..."
rm -rf ${OUTPUT_DIR}
mkdir -p ${OUTPUT_DIR}
echo "   -> 결과는 ${OUTPUT_DIR} 폴더에 저장됩니다."
echo

# 1. Xcode 프로젝트 빌드 (DerivedData 생성)
echo "🔨 [1/5 단계] Xcode 프로젝트 빌드 중 (DerivedData 및 SPM 패키지 생성)..."

XCWORKSPACE=$(find "${PROJECT_PATH}" -name "*.xcworkspace" -type d | grep -v "Pods" | grep -v "DerivedData" | head -n 1)
XCODEPROJ=$(find "${PROJECT_PATH}" -name "*.xcodeproj" -type d | grep -v "Pods" | grep -v "DerivedData" | head -n 1)

REAL_PROJECT_NAME=""
SCHEME=""
BUILD_TARGET=""
BUILD_TYPE=""
BUILD_SUCCESS=false

# ✅ 핵심 수정: 실제 프로젝트 이름을 .xcodeproj/.xcworkspace에서 추출
if [ -n "$XCWORKSPACE" ]; then
    BUILD_TARGET="$XCWORKSPACE"
    BUILD_TYPE="workspace"

    # .xcworkspace의 부모 디렉토리 이름이 실제 프로젝트 이름
    PARENT_DIR=$(dirname "$XCWORKSPACE")
    if [[ $(basename "$PARENT_DIR") == *.xcodeproj ]]; then
        # project.xcworkspace가 .xcodeproj 안에 있는 경우
        REAL_PROJECT_NAME=$(basename "$PARENT_DIR" .xcodeproj)
    else
        # 독립적인 .xcworkspace인 경우
        REAL_PROJECT_NAME=$(basename "$XCWORKSPACE" .xcworkspace)
    fi

    SCHEME=$(xcodebuild -workspace "$XCWORKSPACE" -list 2>/dev/null | grep -A 100 "Schemes:" | grep -v "Schemes:" | head -n 1 | xargs)
    echo "   -> Workspace 발견: $(basename $XCWORKSPACE)"
    echo "   -> 실제 프로젝트 이름: $REAL_PROJECT_NAME"

elif [ -n "$XCODEPROJ" ]; then
    BUILD_TARGET="$XCODEPROJ"
    BUILD_TYPE="project"

    # .xcodeproj 이름이 실제 프로젝트 이름
    REAL_PROJECT_NAME=$(basename "$XCODEPROJ" .xcodeproj)

    SCHEME=$(xcodebuild -project "$XCODEPROJ" -list 2>/dev/null | grep -A 100 "Schemes:" | grep -v "Schemes:" | head -n 1 | xargs)
    echo "   -> 프로젝트 발견: $(basename $XCODEPROJ)"
    echo "   -> 실제 프로젝트 이름: $REAL_PROJECT_NAME"
fi

# ✅ DerivedData 미리 확인
if [ -n "$REAL_PROJECT_NAME" ]; then
    DERIVED_DATA_PATTERN="${REAL_PROJECT_NAME}-*"
    EXISTING_DERIVED=$(find ~/Library/Developer/Xcode/DerivedData -maxdepth 1 -name "$DERIVED_DATA_PATTERN" -type d 2>/dev/null | head -n 1)

    if [ -n "$EXISTING_DERIVED" ]; then
        echo "   ✅ 기존 DerivedData 발견: $(basename $EXISTING_DERIVED)"
        BUILD_SUCCESS=true

        # SPM 헤더 미리 확인
        SPM_CHECKOUTS="${EXISTING_DERIVED}/SourcePackages/checkouts"
        if [ -d "$SPM_CHECKOUTS" ]; then
            SPM_COUNT=$(find "$SPM_CHECKOUTS" -name "*.h" 2>/dev/null | wc -l | xargs)
            echo "   ✅ SPM 헤더 발견: ${SPM_COUNT}개"
        else
            echo "   ⚠️ SPM checkouts 폴더가 없습니다 (의존성이 없거나 빌드 필요)"
        fi
    else
        echo "   ⚠️ 기존 DerivedData를 찾을 수 없습니다. 빌드가 필요합니다."
    fi
fi

# ✅ 빌드 실행 (기존 DerivedData가 없거나 SPM이 없는 경우)
if [ "$BUILD_SUCCESS" = false ] && [ -n "$BUILD_TARGET" ] && [ -n "$SCHEME" ]; then
    echo "   -> 스킴 사용: $SCHEME"
    echo "   -> 빌드 시작 (SPM 패키지 자동 다운로드)..."

    # SDK 감지
    echo "   -> 빌드 대상 감지 중..."
    if xcodebuild -showsdks 2>/dev/null | grep -q "iphonesimulator"; then
        DESTINATION="generic/platform=iOS Simulator"
        echo "      ✅ iOS 시뮬레이터 감지됨 → iOS 빌드 수행"
    elif xcodebuild -showsdks 2>/dev/null | grep -q "macosx"; then
        DESTINATION="generic/platform=macOS"
        echo "      ⚠️ iOS 시뮬레이터 미설치 → macOS 빌드로 대체"
    else
        DESTINATION=""
        echo "      ⚠️ SDK 감지 실패 → -destination 플래그 생략"
    fi

    # 빌드 실행
    echo "   -> 빌드 명령 실행 중..."

    BUILD_LOG="${OUTPUT_DIR}/build.log"

    if [ -n "$DESTINATION" ]; then
        xcodebuild -${BUILD_TYPE} "${BUILD_TARGET}" -scheme "${SCHEME}" \
            -destination "$DESTINATION" \
            -configuration Debug clean build \
            CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO \
            2>&1 | tee "$BUILD_LOG"
        BUILD_RESULT=${PIPESTATUS[0]}
    else
        xcodebuild -${BUILD_TYPE} "${BUILD_TARGET}" -scheme "${SCHEME}" \
            -configuration Debug clean build \
            CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO \
            2>&1 | tee "$BUILD_LOG"
        BUILD_RESULT=${PIPESTATUS[0]}
    fi

    # 빌드 결과 판단
    if [ $BUILD_RESULT -eq 0 ]; then
        if grep -q "BUILD SUCCEEDED" "$BUILD_LOG"; then
            echo "   ✅ 빌드 성공 (DerivedData 생성됨)"
            BUILD_SUCCESS=true
        else
            echo "   ⚠️ 빌드 exit code는 0이지만 BUILD SUCCEEDED를 찾을 수 없습니다."
            BUILD_SUCCESS=false
        fi
    else
        echo "   ❌ 빌드 실패 (exit code: $BUILD_RESULT)"

        if grep -q "is not installed" "$BUILD_LOG"; then
            echo "   💡 힌트: iOS SDK가 설치되지 않았습니다."
        fi

        BUILD_SUCCESS=false
    fi

    # DerivedData 폴더 확인
    if [ "$BUILD_SUCCESS" = true ] && [ -n "$REAL_PROJECT_NAME" ]; then
        DERIVED_DATA_DIR=$(find ~/Library/Developer/Xcode/DerivedData -maxdepth 1 -name "${REAL_PROJECT_NAME}-*" -type d 2>/dev/null | head -n 1)
        if [ -n "$DERIVED_DATA_DIR" ]; then
            echo "   ✅ DerivedData 폴더 확인: $DERIVED_DATA_DIR"

            SPM_CHECKOUTS="${DERIVED_DATA_DIR}/SourcePackages/checkouts"
            if [ -d "$SPM_CHECKOUTS" ]; then
                SPM_COUNT=$(find "$SPM_CHECKOUTS" -name "*.h" 2>/dev/null | wc -l | xargs)
                echo "   ✅ SPM 헤더 발견: ${SPM_COUNT}개"
            else
                echo "   ⚠️ SPM checkouts 폴더가 없습니다"
            fi
        else
            echo "   ⚠️ DerivedData 폴더를 찾을 수 없습니다."
            BUILD_SUCCESS=false
        fi
    fi
fi

# 빌드 실패 시 경고
if [ "$BUILD_SUCCESS" = false ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  경고: 빌드가 실패하여 SPM 헤더를 찾지 못할 수 있습니다."
    echo ""
    echo "💡 해결 방법:"
    echo "   1. Xcode를 열고 프로젝트를 수동으로 빌드해보세요"
    echo "   2. 필요한 iOS SDK를 Xcode에서 다운로드하세요"
    echo "   3. 이미 빌드한 적이 있다면 DerivedData가 남아있을 수 있습니다"
    echo ""
    echo "📝 분석은 계속 진행됩니다."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
echo

# 2. 외부 식별자 추출 (Python)
echo "🐍 [2/5 단계] 외부 식별자 추출 중 (헤더 + 리소스 + SPM)..."
if [ -n "$REAL_PROJECT_NAME" ]; then
    (cd python-engine && ./run_external_extractors.sh ../"${PROJECT_PATH}" ../"${OUTPUT_DIR}/external_exclusions.txt" "${REAL_PROJECT_NAME}")
else
    (cd python-engine && ./run_external_extractors.sh ../"${PROJECT_PATH}" ../"${OUTPUT_DIR}/external_exclusions.txt")
fi
echo

# 3. Swift Extractor 빌드
echo "🐦 [3/5 단계] Swift Extractor 빌드 중..."
if [ ! -f "swift-extractor/.build/release/SymbolExtractor" ]; then
    (cd swift-extractor && swift build -c release)
else
    echo "   -> 이미 빌드되어 있음 (스킵)"
fi
echo

# 4. 심볼 그래프 생성
echo "📊 [4/5 단계] 심볼 그래프 생성 중..."
(cd swift-extractor && .build/release/SymbolExtractor ../"${PROJECT_PATH}" --output ../"${OUTPUT_DIR}/symbol_graph.json" --external-exclusion-list ../"${OUTPUT_DIR}/external_exclusions.txt")
echo

# 5. 파이썬 규칙 엔진 실행
echo "⚙️  [5/5 단계] 파이썬 규칙 엔진으로 분석 실행 중..."
(cd python-engine && python3 main.py ../"${OUTPUT_DIR}/symbol_graph.json" --output ../"${OUTPUT_DIR}/final_exclusion_list.json" --txt-output ../"${OUTPUT_DIR}/final_exclusion_list.txt")
echo

# 6. 결과 비교
echo "📊 [비교] 정답지와 결과 비교 중..."
if [ -f "${RULE_BASE_PATH}" ]; then
    python3 compare_results.py "${RULE_BASE_PATH}" "${OUTPUT_DIR}/final_exclusion_list.txt"
else
    echo "   ⚠️ 정답 파일을 찾을 수 없습니다: ${RULE_BASE_PATH}"
fi
echo

echo "========================================================================"
echo "🎉 분석 완료: ${PROJECT_NAME}"
echo "========================================================================"
echo "📁 결과 위치: ${OUTPUT_DIR}/"
echo "   - external_exclusions.txt      : 외부 식별자 목록"
echo "   - symbol_graph.json            : 심볼 그래프"
echo "   - final_exclusion_list.json    : 최종 제외 목록 (상세)"
echo "   - final_exclusion_list.txt     : 최종 제외 목록 (이름만)"
if [ -f "${OUTPUT_DIR}/build.log" ]; then
    echo "   - build.log                    : 빌드 로그"
fi
echo "========================================================================"