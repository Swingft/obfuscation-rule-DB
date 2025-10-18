# 🚀 Swift Obfuscation Analyzer

Swift 프로젝트의 난독화 제외 대상을 자동으로 분석하는 도구입니다.

## 📦 설치 방법

### 1단계: 압축 해제

```bash
# tar.gz 파일인 경우
tar -xzf obfuscation-analyzer.tar.gz

# zip 파일인 경우
unzip obfuscation-analyzer.zip
```

### 2단계: 디렉토리 이동

```bash
cd obfuscation-analyzer
```

### 3단계: Python 의존성 설치

```bash
# Python 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 4단계: 설치 확인

```bash
python analyze.py --help
```

정상적으로 설치되었다면 도움말이 출력됩니다.

---

## 🎯 기본 사용법

### 가장 간단한 사용

```bash
python analyze.py /path/to/YourProject.xcodeproj
```

**결과:**
- `analysis_output/exclusion_list.txt` 파일 생성
- 난독화에서 제외해야 할 심볼 이름 목록

### 프로젝트 타입별 사용

```bash
# Xcode 프로젝트
python analyze.py /path/to/MyApp.xcodeproj

# Xcode 워크스페이스
python analyze.py /path/to/MyApp.xcworkspace

# Swift Package Manager (SPM)
python analyze.py /path/to/spm-project

# 프로젝트 루트 디렉토리 (자동 탐색)
python analyze.py /path/to/project-root
```

---

## ⚙️ 주요 옵션

### 출력 디렉토리 지정

```bash
python analyze.py /path/to/project -o ./my-results
```

결과 파일이 `./my-results/exclusion_list.txt`에 저장됩니다.

### 프로젝트 이름 명시

DerivedData에서 SPM 의존성을 찾을 때 사용:

```bash
python analyze.py /path/to/project -p "MyProjectName"
```

**언제 필요한가요?**
- 프로젝트 이름에 공백이 있을 때: `Food Truck` → `Food_Truck`
- 자동 추출된 이름이 DerivedData와 다를 때

### 빌드 건너뛰기 (빠른 분석)

```bash
python analyze.py /path/to/project --skip-build
```

프로젝트 빌드를 생략하고 바로 분석합니다 (1-5분 단축).

**추천:**
- 처음 실행: 빌드 포함 (기본값)
- 두 번째 실행부터: `--skip-build` 사용

### 디버그 모드

```bash
python analyze.py /path/to/project --debug
```

**디버그 모드에서:**
- 중간 파일 보존 (`external_identifiers.txt`, `symbol_graph.json`, `exclusion_report.json`)
- 빌드 에러 상세 출력
- 문제 해결 시 유용

---

## 📊 출력 파일

### `exclusion_list.txt` (메인 결과)

```
AppDelegate
SceneDelegate
viewDidLoad
button
title
...
```

**사용법:**
- 난독화 도구의 제외 목록으로 직접 사용
- 한 줄에 하나씩 심볼 이름

### `exclusion_report.json` (디버그 모드)

```json
{
  "name": "viewDidLoad",
  "kind": "instance.method",
  "location": "ViewController.swift:15",
  "reasons": [
    {
      "rule_id": "SYSTEM_LIFECYCLE_METHODS",
      "description": "UIKit lifecycle methods"
    }
  ]
}
```

**포함 정보:**
- 심볼 이름, 타입, 위치
- 제외 이유 (적용된 규칙)

---

## 🔧 고급 사용법

### 1. 여러 프로젝트 일괄 분석

```bash
#!/bin/bash
for project in projects/*.xcodeproj; do
    python analyze.py "$project" -o "results/$(basename $project .xcodeproj)"
done
```

### 2. CI/CD 파이프라인 통합

```yaml
# .github/workflows/analyze.yml
- name: Analyze obfuscation exclusions
  run: |
    python analyze.py ./MyApp.xcodeproj --skip-build
    cat analysis_output/exclusion_list.txt
```

### 3. 결과 비교 (이전 분석과 차이)

```bash
# 첫 번째 분석
python analyze.py /path/to/project -o ./results-v1

# 코드 수정 후
python analyze.py /path/to/project -o ./results-v2

# 차이 확인
diff results-v1/exclusion_list.txt results-v2/exclusion_list.txt
```

---

## 🐛 문제 해결

### "SymbolExtractor not found" 오류

**원인:** Swift 바이너리가 없습니다.

**해결:**
```bash
cd swift-extractor
swift build -c release
cp .build/release/SymbolExtractor ../bin/
cd ..
```

### "No schemes found" 경고

**원인:** Xcode Scheme이 Shared로 설정되지 않음

**해결:**
1. Xcode에서 프로젝트 열기
2. `Product > Scheme > Manage Schemes`
3. 사용할 Scheme의 "Shared" 체크박스 선택
4. 다시 분석 실행

### DerivedData에서 프로젝트를 찾을 수 없음

**원인:** 프로젝트를 한 번도 빌드하지 않았거나 이름이 다름

**해결 방법 1:** 프로젝트 이름 명시
```bash
python analyze.py /path/to/project -p "ExactProjectName"
```

**해결 방법 2:** Xcode에서 직접 빌드 후 실행
```bash
# Xcode에서 ⌘+B (빌드)
python analyze.py /path/to/project
```

**해결 방법 3:** 빌드 건너뛰기
```bash
python analyze.py /path/to/project --skip-build
```

대부분의 경우 프로젝트 내부 헤더만으로도 충분합니다.

### 빌드 타임아웃

**원인:** 대형 프로젝트는 빌드에 5분 이상 소요

**해결:**
```bash
# 빌드 건너뛰기
python analyze.py /path/to/project --skip-build
```

---

## 📂 디렉토리 구조

```
obfuscation-analyzer/
├── bin/
│   └── SymbolExtractor          # Swift 심볼 추출 바이너리
├── lib/
│   ├── extractors/              # 외부 식별자 추출기
│   │   ├── header_extractor.py
│   │   └── resource_identifier_extractor.py
│   ├── analyzer/                # 규칙 엔진
│   │   ├── graph_loader.py
│   │   ├── pattern_matcher.py
│   │   ├── rule_loader.py
│   │   └── analysis_engine.py
│   └── utils/
│       └── report_generator.py
├── rules/
│   └── swift_exclusion_rules.yaml  # 난독화 제외 규칙
├── analyze.py                   # 메인 CLI
├── requirements.txt
└── README.md
```

---

## 🎓 동작 원리

### 3단계 분석 프로세스

```
1. 외부 식별자 추출
   ├─ Objective-C 헤더 스캔
   │  ├─ 프로젝트 내부 헤더
   │  └─ DerivedData의 SPM 패키지 헤더
   └─ 리소스 파일 스캔
      ├─ Storyboard/XIB
      ├─ Assets.xcassets
      ├─ Info.plist
      └─ Localizable.strings

2. 심볼 그래프 생성
   └─ SymbolExtractor로 Swift 심볼 추출

3. 규칙 기반 분석
   └─ 202개 규칙 적용
      ├─ UIKit/SwiftUI 프레임워크 API
      ├─ 델리게이트 패턴
      ├─ 라이프사이클 메서드
      ├─ 일반적인 프로퍼티/메서드 이름
      └─ 외부 참조 심볼
```

### 제외 대상 판단 기준

**자동으로 제외되는 항목:**
- ✅ 시스템 프레임워크 오버라이드 (`viewDidLoad`, `applicationDidFinishLaunching`)
- ✅ Objective-C 브릿징 심볼 (`@objc` 속성)
- ✅ 리소스 파일에서 참조되는 이름 (Storyboard의 클래스명, IBOutlet 등)
- ✅ 외부 라이브러리 공개 API
- ✅ 델리게이트 메서드 (`UITableViewDataSource`, `UITextFieldDelegate`)
- ✅ 매우 일반적인 프로퍼티 이름 (`title`, `name`, `id`, `data`)

---

## 💡 팁

### 더 정확한 분석을 위한 팁

1. **빌드 포함 실행 (첫 실행)**
   ```bash
   python analyze.py /path/to/project
   ```
   DerivedData에 SPM 의존성 헤더가 생성됩니다.

2. **프로젝트 이름 확인**
   ```bash
   # DerivedData 폴더 확인
   ls ~/Library/Developer/Xcode/DerivedData/
   
   # 정확한 이름으로 실행
   python analyze.py /path/to/project -p "YourProjectName"
   ```

3. **규칙 커스터마이징**
   `rules/swift_exclusion_rules.yaml` 파일을 수정하여 프로젝트별 규칙 추가 가능

### 성능 최적화

```bash
# 첫 실행: 빌드 + 전체 분석 (느림, 정확함)
python analyze.py /path/to/project

# 이후 실행: 빌드 생략 (빠름)
python analyze.py /path/to/project --skip-build
```

---

## 📞 지원

### 로그 수집 (이슈 리포트 시)

```bash
python analyze.py /path/to/project --debug > analysis.log 2>&1
```

`analysis.log` 파일과 함께 이슈를 보고해주세요.

### 일반적인 질문

**Q: 분석에 얼마나 걸리나요?**
- 빌드 포함: 3-10분
- 빌드 제외: 10-30초

**Q: 여러 번 실행해도 되나요?**
- 네, 안전합니다. 프로젝트 파일을 수정하지 않습니다.

**Q: exclusion_list.txt를 어떻게 사용하나요?**
- 난독화 도구의 제외 목록으로 직접 입력하거나 import합니다.

**Q: 분석 결과가 너무 많아요 (과잉 제외)**
- `rules/swift_exclusion_rules.yaml`에서 일부 규칙을 비활성화할 수 있습니다.

---

## 📄 라이선스

이 프로젝트의 라이선스는 별도로 문의하세요.

---

## 🎉 시작하기

```bash
# 1. 압축 해제
tar -xzf obfuscation-analyzer.tar.gz
cd obfuscation-analyzer

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 분석 실행
python analyze.py /path/to/YourProject.xcodeproj

# 4. 결과 확인
cat analysis_output/exclusion_list.txt
```

분석 완료! 🎊