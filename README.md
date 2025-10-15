# Swift 난독화 제외 대상 분석기

이 프로젝트는 Swift 프로젝트 내에서 난독화 대상에서 제외해야 할 심볼(클래스, 메서드, 프로퍼티 등)을 식별하기 위해 설계된 정교한 다단계 분석 엔진입니다. 소스 코드, 리소스 파일, 외부 라이브러리를 분석하여 런타임 충돌을 방지하고 애플리케이션 기능을 보장하기 위해 반드시 이름이 유지되어야 하는 식별자들의 정확한 목록을 생성합니다.

---

## 🏛️ 아키텍처

분석 프로세스는 파일 기반의 광범위한 스캔에서 시작하여, 깊이 있는 의미론적 그래프 분석으로 이어지는 3단계 파이프라인으로 구성됩니다. 이 아키텍처는 높은 정확도와 확장성을 보장합니다.

### **1단계: 외부 식별자 추출 (External Identifier Extraction)**
* **역할**: 모든 Swift 외 파일을 스캔하여 하드코딩된 문자열 식별자를 찾습니다.
* **프로세스**: 파이썬 스크립트 모음(`header_extractor.py`, `resource_identifier_extractor.py`)이 Objective-C 헤더(`.h`), 스토리보드(`.storyboard`), Plist(`.plist`), 에셋 카탈로그(`.xcassets`) 등을 파싱합니다.
* **결과물**: Swift 소스 코드 외부에서 발견된 모든 고유 식별자 목록을 담고 있는 간단한 텍스트 파일, `external_exclusions.txt`가 생성됩니다.

### **2단계: 심볼 그래프 생성 (Symbol Graph Generation)**
* **역할**: 모든 Swift 소스 코드를 파싱하여 프로젝트의 포괄적인 모델을 구축합니다.
* **프로세스**: Swift로 빌드된 `swift-extractor` 커맨드라인 도구가 **SwiftSyntax**를 사용하여 모든 `.swift` 파일의 추상 구문 트리(AST)를 순회합니다. 이 과정에서 모든 심볼과 그들 간의 관계(예: 상속, 프로토콜 채택, 포함 관계)를 식별합니다.
* **핵심 기능**: 이 단계에서 1단계의 `external_exclusions.txt` 파일을 읽어옵니다. 만약 Swift 심볼의 이름이 이 목록에 포함되어 있다면, 해당 심볼에 `isReferencedByExternalFile: true` 라는 태그가 추가됩니다.
* **결과물**: 전체 프로젝트를 노드(심볼)와 엣지(관계)의 그래프로 표현하는 상세한 `symbol_graph.json` 파일이 생성됩니다.

### **3단계: 규칙 기반 분석 (Rule-Based Analysis)**
* **역할**: 유연한 규칙 세트를 심볼 그래프에 적용하여 제외해야 할 모든 심볼을 찾아냅니다.
* **프로세스**: `python-engine`이 `symbol_graph.json`을 읽어들인 후, 사람이 쉽게 읽고 쓸 수 있는 `swift_exclusion_rules.yaml` 파일로부터 패턴 목록을 로드합니다. 강력한 패턴 매처가 이 제외 규칙(예: "`@objc` 속성을 가진 모든 메서드를 찾아라" 또는 "이름에 'ViewController'를 포함하는 모든 클래스를 찾아라")과 일치하는 모든 심볼을 그래프에서 쿼리합니다.
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
│   │   ├── header_extractor.py
│   │   └── resource_identifier_extractor.py
│   ├── 📂 rule_engine/              # 분석 엔진 핵심 로직 (3단계)
│   │   ├── core/
│   │   ├── graph/
│   │   ├── reporting/
│   │   └── rules/
│   ├── main.py                      # 파이썬 엔진 실행 파일
│   └── run_external_extractors.sh   # 모든 외부 추출기를 실행하는 헬퍼 스크립트
│
├── 📂 rules/
│   └── swift_exclusion_rules.yaml   # 분석기의 심장: 커스터마이징 가능한 제외 규칙
│
└── 📂 swift-extractor/
├── Sources/                     # Swift 심볼 그래프 생성기 소스 코드
└── Package.swift                # Swift 패키지 의존성
``` 

---

## 🚀 실행 방법

대상 프로젝트에 대한 전체 분석을 실행하려면, 루트 디렉토리(`obfuscation-rule-DB/`)에서 아래 3단계를 순서대로 진행하세요.

### **1단계: 외부 식별자 추출**
이 단계는 헤더, 스토리보드 등을 스캔하는 파이썬 스크립트를 실행합니다.

```bash
cd python-engine && ./run_external_extractors.sh /path/to/YourSwiftProject ../output/external_exclusions.txt
참고: /path/to/YourSwiftProject 부분을 분석하고 싶은 프로젝트의 실제 경로로 바꿔주세요.

2단계: 심볼 그래프 생성
이 단계는 Swift 도구를 빌드하고 실행하여 symbol_graph.json을 생성합니다.

Bash

cd ../swift-extractor && swift build -c release && ./.build/release/SymbolExtractor /path/to/YourSwiftProject --output ../output/symbol_graph.json --external-exclusion-list ../output/external_exclusions.txt
참고: 여기에 입력하는 프로젝트 경로는 1단계에서 사용한 경로와 동일해야 합니다.

3단계: 규칙 엔진 실행
마지막으로, 그래프와 규칙을 분석하여 최종 제외 목록을 생성합니다.

Bash

cd ../python-engine && python3 main.py ../output/symbol_graph.json
이 단계가 끝나면, output 디렉토리에서 최종 결과물을 확인할 수 있습니다.

🧩 핵심 구성 요소
rules/swift_exclusion_rules.yaml: 분석을 커스터마이징하기 위한 가장 중요한 파일입니다. 코드 수정 없이 이곳에서 규칙을 쉽게 추가하거나 수정할 수 있습니다. 규칙은 다음과 같은 형태를 가집니다.

YAML

- id: "UI_CONTROLLER_CLASSES"
  description: "ViewController 또는 NavigationController 클래스들"
  reason: "UI 관련 클래스는 스토리보드나 코드에서 이름으로 참조될 위험이 매우 높습니다."
  pattern:
    - find: { target: C }
    - where:
        - "C.kind == 'class'"
        - "C.name contains 'Controller'"
의존성:

Swift: Swift 툴체인 (swift-extractor 빌드용).

Python 3: 분석 엔진 및 추출기 실행용.

Python 라이브러리: PyYAML, networkx. pip install pyyaml networkx 명령어로 설치할 수 있습니다.