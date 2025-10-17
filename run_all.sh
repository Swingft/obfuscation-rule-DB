#!/bin/bash

# 지정된 모든 프로젝트에 대해 전체 분석을 실행하는 마스터 스크립트

# 분석 스크립트에 실행 권한 부여
chmod +x run_analysis.sh

# --- 분석할 프로젝트 쌍 목록 ---
# 형식: "프로젝트_폴더_이름 정답_파일.txt"
PROJECTS=(
#    "test_project4/Life-Progress-iOS life.txt"
#    "test_project5/NextLevel nextlevel.txt"
#    "test_project6/sample-food-truck sample.txt"
    "test_project7/social-distancing-ios social.txt"
#    "test_project8/UIKit+SPM_1 uikit1.txt"
#    "test_project9/UIKit+SPM_2 uikit2.txt"
)

# --- 루프를 돌며 각 프로젝트 분석 실행 ---
for pair in "${PROJECTS[@]}"; do
    # 쌍을 프로젝트 이름과 정답 파일 이름으로 분리
    read -r project rule_file <<< "$pair"

    # 현재 쌍에 대해 분석 스크립트 실행
    ./run_analysis.sh "$project" "$rule_file"
done

echo "✅ 모든 프로젝트 분석이 완료되었습니다."
