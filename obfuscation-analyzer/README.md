# 📦 CLI 배포용 패키지 구조화 가이드

## 1️⃣ 디렉토리 재구성

```bash
# 새 패키지 디렉토리 생성
mkdir obfuscation-analyzer
cd obfuscation-analyzer

# 필수 디렉토리 생성
mkdir -p bin lib/extractors lib/analyzer lib/utils rules
```

## 2️⃣ 파일 이동 및 정리

### 📁 bin/ - 실행 파일만
```bash
# Swift 빌드 후 바이너리만 복사
cd swift-extractor
swift build -c release
cp .build/release/SymbolExtractor ../obfuscation-analyzer/bin/

# 실행 권한 부여
chmod +x ../obfuscation-analyzer/bin/SymbolExtractor
```

### 📁 lib/extractors/ - 추출기 모듈
```bash
cd obfuscation-analyzer/lib/extractors

# __init__.py 생성 (모듈 선언)
cat > __init__.py << 'EOF'
"""외부 식별자 추출기 모듈"""
from .header_extractor import HeaderScanner
from .resource_identifier_extractor import ResourceScanner

__all__ = ['HeaderScanner', 'ResourceScanner']
EOF

# 원본에서 파일 복사
cp <원본경로>/python-engine/external_extractors/header_extractor.py .
cp <원본경로>/python-engine/external_extractors/resource_identifier_extractor.py .
```

### 📁 lib/analyzer/ - 규칙 엔진 모듈
```bash
cd ../analyzer

cat > __init__.py << 'EOF'
"""규칙 기반 분석 엔진 모듈"""
from .graph_loader import SymbolGraph
from .pattern_matcher import PatternMatcher, RuleLoader
from .analysis_engine import AnalysisEngine

__all__ = ['SymbolGraph', 'PatternMatcher', 'RuleLoader', 'AnalysisEngine']
EOF

# 파일 복사 및 임포트 경로 수정
cp <원본경로>/python-engine/rule_engine/graph/graph_loader.py .
cp <원본경로>/python-engine/rule_engine/rules/pattern_matcher.py .
cp <원본경로>/python-engine/rule_engine/rules/rule_loader.py .
cp <원본경로>/python-engine/rule_engine/core/analysis_engine.py .
```

### 📁 lib/utils/ - 유틸리티
```bash
cd ../utils

cat > __init__.py << 'EOF'
"""유틸리티 모듈"""
from .report_generator import ReportGenerator

__all__ = ['ReportGenerator']
EOF

cp <원본경로>/python-engine/rule_engine/reporting/report_generator.py .
```

### 📁 rules/ - YAML 규칙 파일
```bash
cd ../../rules
cp <원본경로>/rules/swift_exclusion_rules.yaml .
```

## 3️⃣ 임포트 경로 수정

각 Python 파일에서 상대 임포트를 절대 임포트로 변경:

**예: analysis_engine.py**
```python
# Before (상대 임포트)
from ..graph.graph_loader import SymbolGraph
from ..rules.rule_loader import RuleLoader

# After (절대 임포트)
from lib.analyzer.graph_loader import SymbolGraph
from lib.analyzer.pattern_matcher import RuleLoader
```

**pattern_matcher.py**
```python
# Before
from ..graph.graph_loader import SymbolGraph

# After
from lib.analyzer.graph_loader import SymbolGraph
```

## 4️⃣ 메인 파일 및 설정 생성

### analyze.py (위에서 생성한 artifact)
```bash
# 루트에 배치
cp <artifact의 analyze.py> ./analyze.py
chmod +x analyze.py
```

### requirements.txt
```txt
networkx>=2.8
pyyaml>=6.0
```

### README.md
```markdown
# Swift Obfuscation Analyzer

## 빠른 시작

### 설치
```bash
pip install -r requirements.txt
```

### 사용법
```bash
python analyze.py /path/to/YourProject.xcodeproj
```

### 옵션
- `-o, --output`: 결과 출력 디렉토리
- `-p, --project-name`: DerivedData 검색용 프로젝트 이름

## 출력 파일
- `external_identifiers.txt`: 외부 참조 식별자
- `symbol_graph.json`: 심볼 그래프
- `exclusion_report.json`: 상세 분석 결과
- `exclusion_list.txt`: 제외 대상 이름 목록
```

## 5️⃣ 최종 패키지 구조

```
obfuscation-analyzer/
├── bin/
│   └── SymbolExtractor              # Swift 실행 파일
├── lib/
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── header_extractor.py
│   │   └── resource_identifier_extractor.py
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── graph_loader.py
│   │   ├── pattern_matcher.py
│   │   ├── rule_loader.py
│   │   └── analysis_engine.py
│   └── utils/
│       ├── __init__.py
│       └── report_generator.py
├── rules/
│   └── swift_exclusion_rules.yaml
├── analyze.py                       # 메인 CLI
├── requirements.txt
└── README.md
```

## 6️⃣ 배포 및 사용

### 압축하여 전달
```bash
cd ..
tar -czf obfuscation-analyzer.tar.gz obfuscation-analyzer/
```

### CLI 개발자가 받아서 사용
```bash
# 압축 해제
tar -xzf obfuscation-analyzer.tar.gz
cd obfuscation-analyzer

# 의존성 설치
pip install -r requirements.txt

# 분석 실행
python analyze.py ../MyProject.xcodeproj -o ./results
```

## 7️⃣ 고급: Python 패키지로 설치 가능하게 만들기

### setup.py 추가
```python
from setuptools import setup, find_packages

setup(
    name="swift-obfuscation-analyzer",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "networkx>=2.8",
        "pyyaml>=6.0",
    ],
    entry_points={
        'console_scripts': [
            'swift-analyze=analyze:main',
        ],
    },
    package_data={
        '': ['bin/SymbolExtractor', 'rules/*.yaml'],
    },
)
```

### 설치 후 사용
```bash
pip install .

# 어디서든 실행 가능
swift-analyze /path/to/project
```

## 8️⃣ 검증 체크리스트

- [ ] SymbolExtractor 바이너리 포함 및 실행 권한 확인
- [ ] 모든 Python 모듈 임포트 경로 수정 완료
- [ ] requirements.txt 의존성 설치 확인
- [ ] 샘플 프로젝트로 테스트 실행
- [ ] README에 사용법 명시
- [ ] 에러 처리 추가 (SymbolExtractor 없을 때 등)