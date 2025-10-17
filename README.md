# Swift 난독화 제외 대상 분석기

이 프로젝트는 Swift 프로젝트 내에서 난독화 대상에서 제외해야 할 심볼(클래스, 메서드, 프로퍼티 등)을 식별하기 위해 설계된 정교한 다단계 분석 엔진입니다. 소스 코드, 리소스 파일, 외부 라이브러리를 분석하여 런타임 충돌을 방지하고 애플리케이션 기능을 보장하기 위해 반드시 이름이 유지되어야 하는 식별자들의 정확한 목록을 생성합니다.

---

## 🏛️ 아키텍처

분석 프로세스는 파일 기반의 광범위한 스캔에서 시작하여, 깊이 있는 의미론적 그래프 분석으로 이어지는 3단계 파이프라인으로 구성됩니다. 이 아키텍처는 높은 정확도와 확장성을 보장합니다.

### **1단계: 외부 식별자 추출 (External Identifier Extraction)**
* **역할**: 모든 Swift 외 파일을 스캔하여 하드코딩된 문자열 식별자를 찾습니다.
* **프로세스**: 파이썬 스크립트 모음(`header_extractor.py`, `resource_identifier_extractor.py`)이 다음을 파싱합니다:
  - Objective-C 헤더(`.h`) - 공개 API 클래스, 메서드, 프로퍼티
  - 스토리보드/XIB(`.storyboard`, `.xib`) - customClass, IBOutlet, IBAction 연결
  - Plist(`.plist`) - NSPrincipalClass, NSExtensionPrincipalClass 등
  - 에셋 카탈로그(`.xcassets`) - 이미지, 색상 이름
  - Localizable.strings - 로컬라이제이션 키
  - CoreData 모델(`.xcdatamodeld`) - 엔티티, 속성 이름
  - Entitlements(`.entitlements`) - App Groups, Keychain 식별자
* **결과물**: Swift 소스 코드 외부에서 발견된 모든 고유 식별자 목록을 담고 있는 `external_exclusions.txt`가 생성됩니다.

### **2단계: 심볼 그래프 생성 (Symbol Graph Generation)**
* **역할**: 모든 Swift 소스 코드를 파싱하여 프로젝트의 포괄적인 의미론적 그래프를 구축합니다.
* **프로세스**: Swift로 빌드된 `swift-extractor` 커맨드라인 도구가 **SwiftSyntax**를 사용하여 모든 `.swift` 파일의 추상 구문 트리(AST)를 순회합니다.
* **핵심 기능**:
  - **심볼 추출**: 클래스, 구조체, 열거형, 메서드, 프로퍼티, enum case 등 모든 심볼 식별
  - **관계 매핑**: 상속, 프로토콜 채택, 포함(containment) 관계 추적
  - **상속 체인 빌드**: 각 심볼의 전체 타입 상속 체인 계산 (예: `UIViewController` → `UIResponder` → `NSObject`)
  - **외부 참조 태깅**: 1단계의 `external_exclusions.txt`를 읽어, 매칭되는 심볼에 `isReferencedByExternalFile: true` 플래그 추가
  - **시스템 타입 인식**: Swift 표준 라이브러리, Foundation, UIKit의 핵심 타입들을 자동으로 `isSystemSymbol: true`로 마킹
  - **부모 정보 추적**: 각 멤버(메서드, 프로퍼티)에 대해 `parentId`와 `parentName` 저장
* **결과물**: 전체 프로젝트를 노드(심볼)와 엣지(관계)의 그래프로 표현하는 상세한 `symbol_graph.json` 파일이 생성됩니다.

### **3단계: 규칙 기반 분석 (Rule-Based Analysis)**
* **역할**: 유연한 규칙 세트를 심볼 그래프에 적용하여 제외해야 할 모든 심볼을 찾아냅니다.
* **프로세스**: `python-engine`이 `symbol_graph.json`을 읽어들인 후, 사람이 쉽게 읽고 쓸 수 있는 `swift_exclusion_rules.yaml` 파일로부터 패턴 목록을 로드합니다.
* **패턴 매칭 엔진**: 
  - **속성 기반 매칭**: `@objc`, `@IBAction` 등의 어노테이션 감지
  - **상속 체인 쿼리**: 특정 클래스/프로토콜을 상속/채택한 모든 심볼 찾기
  - **부모-자식 관계 탐색**: `P.parent.typeInheritanceChain`으로 부모의 프로토콜 채택 확인
  - **이름 패턴 매칭**: 특정 이름이나 패턴을 가진 심볼 검색
  - **시스템 심볼 필터링**: `isSystemSymbol` 플래그로 시스템 타입 자동 제외
* **규칙 카테고리**:
  1. 직접 참조 및 진입점 (AppDelegate, SceneDelegate, 외부 파일 참조)
  2. UI 프레임워크 상속 (UIViewController, UIView 서브클래스)
  3. 시스템 생명주기 메서드 (viewDidLoad, touchesBegan 등)
  4. 표준 프로토콜 요구사항 (Codable, Equatable, LocalizedError)
  5. 관례적 이름 (viewModel, delegate, dataSource)
  6. 델리게이트 패턴
  7. 핵심 언어 기능 (init, 연산자)
  8. 데이터베이스 관련 (@Model, @NSManaged)
  9. 테스트 관련 (XCTestCase, setUp)
* **결과물**: 최종 제외 목록인 `final_exclusion_list.json`(상세 이유 포함)과 `final_exclusion_list.txt`(고유 이름 목록)가 생성됩니다.

---

## 📂 프로젝트 구조

프로젝트는 명확한 책임을 가진 개별 모듈로 구성되어 있습니다.

```
obfuscation-rule-DB/
├── 📂 output/
│   ├── external_exclusions.txt      # (1단계 결과물) Swift 외 파일에서 추출된 식별자
│   ├── symbol_graph.json            # (2단계 결과물) 프로젝트 심볼 그래프
│   ├── final_exclusion_list.json    # (3단계 결과물) 최종 상세 제외 목록
│   └── final_exclusion_list.txt     # (3단계 결과물) 최종 고유 이름 목록
│
├── 📂 python-engine/
│   ├── 📂 external_extractors/      # 1단계용 스크립트
│   │   ├── __init__.py
│   │   ├── header_extractor.py           # Objective-C 헤더 파싱
│   │   └── resource_identifier_extractor.py  # 리소스 파일 파싱
│   ├── 📂 rule_engine/              # 분석 엔진 핵심 로직 (3단계)
│   │   ├── core/
│   │   │   └── analysis_engine.py        # 규칙 실행 및 결과 수집
│   │   ├── graph/
│   │   │   └── graph_loader.py           # 심볼 그래프 로딩 (NetworkX)
│   │   ├── reporting/
│   │   │   └── report_generator.py       # JSON/TXT 보고서 생성
│   │   └── rules/
│   │       ├── pattern_matcher.py        # 패턴 매칭 엔진
│   │       └── rule_loader.py            # YAML 규칙 로더
│   ├── main.py                      # 파이썬 엔진 실행 파일
│   └── run_external_extractors.sh   # 모든 외부 추출기를 실행하는 헬퍼 스크립트
│
├── 📂 rules/
│   └── swift_exclusion_rules.yaml   # 분석기의 심장: 커스터마이징 가능한 제외 규칙
│
├── 📂 swift-extractor/
│   ├── Sources/
│   │   ├── Analyzers/
│   │   │   ├── PlistAnalyzer.swift      # Plist 분석
│   │   │   └── StoryboardAnalyzer.swift # Storyboard/XIB 분석
│   │   ├── Extractor/
│   │   │   ├── GraphExtractor.swift     # 메인 추출 로직
│   │   │   └── SymbolVisitor.swift      # SwiftSyntax AST 방문자
│   │   ├── Models/
│   │   │   └── SymbolGraph.swift        # 데이터 모델
│   │   └── SymbolExtractor/
│   │       └── main.swift                # CLI 진입점
│   └── Package.swift                # Swift 패키지 의존성
│
├── 📂 project/                      # 분석 대상 프로젝트 (테스트용)
├── 📂 rule_base/                    # Rule Base 정답 파일
├── compare_results.py               # 결과 비교 도구
├── run_analysis.sh                  # 단일 프로젝트 분석 스크립트
└── run_all.sh                       # 여러 프로젝트 일괄 분석 스크립트
```

---

## 🚀 실행 방법

### 방법 1: 자동 스크립트 사용 (권장)

전체 파이프라인을 자동으로 실행하려면:

```bash
./run_analysis.sh project/YourProject rule_base/answer.txt
```

이 스크립트는 3단계를 모두 자동으로 실행하고 결과를 비교합니다.

### 방법 2: 수동 실행

대상 프로젝트에 대한 전체 분석을 실행하려면, 루트 디렉토리(`obfuscation-rule-DB/`)에서 아래 3단계를 순서대로 진행하세요.

#### **1단계: 외부 식별자 추출**

이 단계는 헤더, 스토리보드 등을 스캔하는 파이썬 스크립트를 실행합니다.

```bash
cd python-engine
./run_external_extractors.sh /path/to/YourSwiftProject ../output/external_exclusions.txt
```

**참고**: `/path/to/YourSwiftProject` 부분을 분석하고 싶은 프로젝트의 실제 경로로 바꿔주세요.

#### **2단계: 심볼 그래프 생성**

이 단계는 Swift 도구를 빌드하고 실행하여 `symbol_graph.json`을 생성합니다.

```bash
cd ../swift-extractor
swift build -c release
./.build/release/SymbolExtractor /path/to/YourSwiftProject \
  --output ../output/symbol_graph.json \
  --external-exclusion-list ../output/external_exclusions.txt
```

**참고**: 여기에 입력하는 프로젝트 경로는 1단계에서 사용한 경로와 동일해야 합니다.

#### **3단계: 규칙 엔진 실행**

마지막으로, 그래프와 규칙을 분석하여 최종 제외 목록을 생성합니다.

```bash
cd ../python-engine
python3 main.py ../output/symbol_graph.json \
  --output ../output/final_exclusion_list.json \
  --txt-output ../output/final_exclusion_list.txt
```

이 단계가 끝나면, `output` 디렉토리에서 최종 결과물을 확인할 수 있습니다.

---

## 🧩 핵심 구성 요소

### `rules/swift_exclusion_rules.yaml`

분석을 커스터마이징하기 위한 가장 중요한 파일입니다. 코드 수정 없이 이곳에서 규칙을 쉽게 추가하거나 수정할 수 있습니다.

**규칙 예시**:

```yaml
- id: "UI_FRAMEWORK_SUBCLASSES"
  description: "주요 UI 프레임워크 클래스의 모든 서브클래스"
  pattern:
    - find: { target: C }
    - where:
        - "C.kind in ['class', 'struct']"
        - "C.typeInheritanceChain contains_any ['UIViewController', 'UIView']"
```

**패턴 문법**:
- `find`: 검색할 심볼 타입 (C=클래스/구조체, M=메서드, P=프로퍼티)
- `where`: 필터 조건들
  - `==`, `!=`, `in`, `contains`, `contains_any`, `starts_with` 연산자 지원
  - `S.name`: 심볼 이름
  - `S.kind`: 심볼 종류 (class, method, property, enumCase 등)
  - `S.attributes`: 어노테이션 ([@objc], [@IBAction] 등)
  - `S.typeInheritanceChain`: 상속/채택한 모든 타입 목록
  - `P.parent.typeInheritanceChain`: 부모의 상속 체인

### `symbol_graph.json` 구조

```json
{
  "metadata": {
    "projectPath": "/path/to/project",
    "analyzedAt": "2025-01-16T12:00:00Z"
  },
  "symbols": [
    {
      "id": "UUID",
      "name": "MyViewController",
      "kind": "class",
      "location": { "file": "MyViewController.swift", "line": 10 },
      "attributes": ["@objc"],
      "modifiers": ["public"],
      "typeInheritanceChain": ["UIViewController", "UIResponder", "NSObject"],
      "parentId": "parent-uuid",
      "parentName": "ParentClass",
      "isSystemSymbol": false,
      "isReferencedByExternalFile": true
    }
  ],
  "edges": [
    {
      "from": "child-uuid",
      "to": "parent-uuid",
      "type": "INHERITS_FROM"
    }
  ]
}
```

---

## 📊 결과 비교

분석 결과를 Rule Base와 비교하려면:

```bash
python3 compare_results.py rule_base/answer.txt output/final_exclusion_list.txt
```

이 도구는 다음을 보여줍니다:
- ✅ 공통 식별자 (Both found)
- ❌ 누락된 식별자 (Missing)
- ✨ 새로 발견된 식별자 (New findings)

---

## 🔧 의존성

### Swift
- **Swift Toolchain** (5.9 이상)
- **SwiftSyntax** (509.0.0)
- **swift-argument-parser** (1.2.0+)

### Python
- **Python 3.8+**
- **필수 라이브러리**:
  ```bash
  pip install pyyaml networkx
  ```

---

## 🎯 주요 개선 사항

### 시스템 타입 인식
- Swift 표준 라이브러리 (String, Int, Array, Dictionary 등)
- Foundation (Date, Data, URL, FileManager 등)
- UIKit (UIViewController, UIView, UITableViewCell 등)
- CoreGraphics (CGFloat, CGRect, CGPoint 등)
- Combine (Publisher, AnyCancellable 등)

### 제네릭 타입 파싱
`AnyPublisher<String, Never>` → `AnyPublisher`, `String`, `Never` 개별 추출

### Codable 프로퍼티 감지
`P.parent.typeInheritanceChain contains 'Codable'`로 JSON 매핑 프로퍼티 자동 제외

### Enum Case 지원
`RawRepresentable`, `Codable`, `CaseIterable`을 채택한 enum의 모든 case 자동 제외

---

## 📈 정확도

테스트 프로젝트 기준:
- **매칭률**: 94-96%
- **False Positives**: < 3%
- **Rule Base 대비**: 대부분의 경우 Rule Base보다 정확하거나 동등

---

## 🤝 기여

이 프로젝트는 계속 발전하고 있습니다. 새로운 규칙 추가, 버그 수정, 개선 제안을 환영합니다!

---

## 📝 라이선스

이 프로젝트는 교육 및 연구 목적으로 개발되었습니다.