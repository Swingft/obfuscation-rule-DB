markdown# learning/README.md

# 🤖 자동 규칙 학습 시스템

GitHub 오픈소스 프로젝트에서 패턴을 자동으로 학습하여 난독화 제외 규칙을 생성하는 시스템입니다.

## 📋 목차

- [개요](#개요)
- [설치](#설치)
- [사용 방법](#사용-방법)
- [워크플로우](#워크플로우)
- [설정](#설정)
- [출력 파일](#출력-파일)

---

## 🎯 개요

### 문제점

수동으로 규칙을 작성하면:
- ❌ 시간이 많이 소요됨
- ❌ 놓치는 패턴이 있을 수 있음
- ❌ 새로운 프레임워크 대응이 느림

### 해결책

대규모 오픈소스 프로젝트 분석을 통해:
- ✅ 자동으로 패턴 발견
- ✅ 통계 기반 규칙 생성
- ✅ 검증을 통한 품질 보장

---

## 🚀 설치

### 1. 의존성 설치
```bash
cd learning
pip install -r requirements.txt
```

### 2. GitHub Token 설정 (선택)

API Rate Limit을 늘리려면:
```bash
export GITHUB_TOKEN="your_personal_access_token"
```

Token 생성: https://github.com/settings/tokens

---

## 📖 사용 방법

### 옵션 1: 통합 메뉴 (권장)
```bash
python main.py
```

대화형 메뉴에서 원하는 단계 선택

### 옵션 2: 개별 실행
```bash
#재시도마계속bash# 1. GitHub 프로젝트 수집
python github_crawler.py

# 2. 패턴 추출
python pattern_extractor.py

# 3. 규칙 생성
python rule_generator.py

# 4. 규칙 검증
python validator.py

# 5. 규칙 병합
python merge_rules.py
옵션 3: 전체 파이프라인 자동 실행
bashpython main.py
# 메뉴에서 6번 선택
```

---

## 🔄 워크플로우
```
┌─────────────────────────────────────────────────────────┐
│ 1. GitHub Crawler                                       │
│    ↓                                                     │
│    • GitHub API로 Star 100+ 프로젝트 검색               │
│    • 의존성 분석 (Package.swift, Podfile)               │
│    • Git Clone (선택)                                   │
│    ↓                                                     │
│    Output: projects.json                                │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Pattern Extractor                                    │
│    ↓                                                     │
│    • Swift 파일 파싱                                    │
│    • 프로퍼티/메서드/클래스 이름 추출                   │
│    • 빈도 분석 (60% 이상 등장)                          │
│    • 프레임워크 특화 패턴 감지                          │
│    ↓                                                     │
│    Output: patterns.json                                │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Rule Generator                                       │
│    ↓                                                     │
│    • 패턴 → YAML 규칙 변환                              │
│    • 카테고리별 그룹화                                  │
│    • ID 자동 생성                                       │
│    ↓                                                     │
│    Output: generated_rules.yaml                         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Validator                                            │
│    ↓                                                     │
│    • 벤치마크 프로젝트로 테스트                         │
│    • Accuracy, Precision, Recall 계산                   │
│    • 품질 기준 체크 (85% 이상)                          │
│    ↓                                                     │
│    Output: validation_report.json                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Rule Merger                                          │
│    ↓                                                     │
│    • 기존 규칙과 병합                                   │
│    • 중복 제거                                          │
│    • 정렬 및 정리                                       │
│    ↓                                                     │
│    Output: merged_rules.yaml                            │
└─────────────────────────────────────────────────────────┘

⚙️ 설정
config.py에서 다음 설정을 조정할 수 있습니다:
python# 수집 기준
MIN_STARS = 100           # 최소 스타 수
MAX_PROJECTS = 50         # 최대 프로젝트 수
LANGUAGE = "Swift"        # 프로그래밍 언어

# 패턴 추출 기준
MIN_FREQUENCY = 0.6       # 60% 이상의 프로젝트에서 등장
MIN_OCCURRENCES = 3       # 최소 3회 이상 등장

# 검증 기준
MIN_ACCURACY = 0.85       # 85% 이상 정확도
MAX_FALSE_POSITIVE = 0.05 # 5% 이하 오탐률
```

---

## 📂 출력 파일

### data/
```
learning/data/
├── projects.json              # 수집된 프로젝트 목록
├── patterns.json              # 추출된 패턴
├── generated_rules.yaml       # 생성된 규칙
├── merged_rules.yaml          # 병합된 규칙
├── validation_report.json     # 검증 결과
└── extraction_report.txt      # 패턴 분석 리포트
```

### cache/
```
learning/cache/
└── downloaded_projects/       # 다운로드된 프로젝트
    ├── user1_repo1/
    ├── user2_repo2/
    └── ...

📊 예제 출력
1. projects.json
json[
  {
    "name": "Alamofire",
    "full_name": "Alamofire/Alamofire",
    "owner": "Alamofire",
    "stars": 40500,
    "language": "Swift",
    "dependencies": ["SwiftLint"],
    "local_path": "/path/to/cache/Alamofire_Alamofire"
  }
]
2. patterns.json
json{
  "property_names": [
    {
      "name": "viewModel",
      "count": 45,
      "frequency": 0.9
    }
  ],
  "method_names": [
    {
      "name": "configure",
      "count": 38,
      "frequency": 0.76
    }
  ],
  "class_suffixes": [
    {
      "suffix": "ViewController",
      "count": 48,
      "frequency": 0.96
    }
  ]
}
3. generated_rules.yaml
yamlrules:
  - id: "LEARNED_COMMON_PROPERTY_NAMES"
    description: "학습된 범용 프로퍼티 이름 (45개)"
    pattern:
      - find: {target: P}
      - where:
          - "P.kind == 'property'"
          - "P.name in ['viewModel', 'disposeBag', 'coordinator', ...]"
4. validation_report.json
json{
  "projects": {
    "life": {
      "accuracy": 0.87,
      "precision": 0.92,
      "recall": 0.85,
      "f1_score": 0.88
    }
  },
  "average": {
    "accuracy": 0.86,
    "precision": 0.90,
    "recall": 0.84,
    "f1_score": 0.87
  }
}

🎓 학습 전략
빈도 기반 학습
50개 프로젝트에서 60% 이상 등장하는 패턴만 추출:
pythonif pattern_count / total_projects >= 0.6:
    add_to_rules(pattern)
프레임워크 특화 학습
프로젝트의 의존성을 분석하여 특화 패턴 추출:
pythonif "RxSwift" in dependencies:
    extract_rx_patterns()
```

### 아키텍처 패턴 감지

클래스 이름 접미사로 아키텍처 파악:

- `*ViewController` → MVC/MVVM
- `*ViewModel` → MVVM
- `*Coordinator` → Coordinator Pattern
- `*Interactor` → VIPER

---

## 🧪 검증 메트릭

### Accuracy (정확도)

전체 심볼 중 올바르게 분류한 비율
```
Accuracy = (TP + TN) / (TP + TN + FP + FN)
```

### Precision (정밀도)

제외 대상으로 예측한 것 중 실제로 제외해야 하는 비율
```
Precision = TP / (TP + FP)
```

### Recall (재현율)

실제 제외 대상 중 올바르게 찾아낸 비율
```
Recall = TP / (TP + FN)
```

### F1 Score

Precision과 Recall의 조화 평균
```
F1 = 2 * (Precision * Recall) / (Precision + Recall)

🔧 트러블슈팅
GitHub API Rate Limit
증상: X-RateLimit-Remaining: 0 에러
해결:

GitHub Personal Access Token 설정
대기 시간 자동 처리 (코드에 구현됨)

다운로드 실패
증상: git clone 타임아웃
해결:

네트워크 연결 확인
--depth 1 옵션으로 shallow clone (이미 적용됨)
타임아웃 시간 조정 (config.py)

패턴 추출 실패
증상: 패턴이 너무 적게 추출됨
해결:

MIN_FREQUENCY 낮추기 (0.6 → 0.4)
MIN_OCCURRENCES 낮추기 (3 → 2)
더 많은 프로젝트 수집 (MAX_PROJECTS 증가)

검증 실패
증상: Accuracy < 85%
해결:

더 많은 학습 데이터 수집
패턴 추출 기준 조정
수동으로 규칙 보완


📈 성능 최적화
캐싱
이미 다운로드된 프로젝트는 재사용:
pythonif target_dir.exists():
    print("Already exists, skipping...")
    return target_dir
병렬 처리 (향후 개선)
python# TODO: 멀티프로세싱으로 패턴 추출 가속화
from multiprocessing import Pool

with Pool(processes=4) as pool:
    pool.map(analyze_project, project_paths)
```

---

## 🚀 향후 개선 방향

### 1. ML 기반 학습

- [ ] TF-IDF로 패턴 중요도 계산
- [ ] 결정 트리로 규칙 자동 생성
- [ ] 신경망으로 심볼 분류

### 2. 증분 학습

- [ ] 새 프로젝트 추가 시 재학습
- [ ] 규칙 버전 관리
- [ ] A/B 테스트

### 3. 도메인 특화

- [ ] 전자상거래 프로젝트 전용 규칙
- [ ] 소셜 미디어 앱 전용 규칙
- [ ] 금융 앱 전용 규칙

### 4. UI 도구

- [ ] 웹 대시보드
- [ ] 규칙 시각화
- [ ] 실시간 검증

---

## 🤝 기여하기

1. 새로운 패턴 발견 시 Issue 등록
2. 프레임워크 특화 추출 로직 개선
3. 검증 메트릭 추가
4. 문서 개선

---

## 📚 참고 자료

- [GitHub REST API](https://docs.github.com/en/rest)
- [YAML Specification](https://yaml.org/spec/)
- [Precision and Recall](https://en.wikipedia.org/wiki/Precision_and_recall)

---

## 📄 라이선스

MIT License - 자세한 내용은 상위 디렉토리의 LICENSE 참조

---

## 📞 문의

학습 시스템 관련 문의:
- GitHub Issues
- Email: your-email@example.com

---

Made with 🤖 by the Auto-Learning Team
```