# learning/config.py

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """학습 시스템 설정"""

    # 경로
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    CACHE_DIR = BASE_DIR / "cache"
    PROJECTS_DIR = CACHE_DIR / "downloaded_projects"

    # GitHub API
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # ✅ .env에서 자동 로드
    GITHUB_API_URL = "https://api.github.com"

    # 수집 기준
    MIN_STARS = 100
    MAX_PROJECTS = 50
    LANGUAGE = "Swift"

    # 패턴 추출 기준
    MIN_FREQUENCY = 0.6  # 60% 이상의 프로젝트에서 등장
    MIN_OCCURRENCES = 3  # 최소 3회 이상 등장
    MIN_SWIFT_PERCENTAGE = 0.8  # 80% 이상

    # 검증 기준
    MIN_ACCURACY = 0.85  # 85% 이상 정확도
    MAX_FALSE_POSITIVE = 0.05  # 5% 이하 오탐률

    # 프레임워크 목록 (의존성 감지용)
    POPULAR_FRAMEWORKS = [
        "Alamofire",
        "RxSwift",
        "Kingfisher",
        "SnapKit",
        "Realm",
        "SwiftyJSON",
        "Moya",
        "Firebase",
        "Combine"
    ]

    # 도메인 키워드
    DOMAIN_KEYWORDS = {
        "ecommerce": ["cart", "checkout", "payment", "order", "product"],
        "social": ["feed", "post", "like", "follow", "comment", "share"],
        "finance": ["transaction", "account", "balance", "payment", "wallet"],
        "health": ["workout", "activity", "health", "fitness", "nutrition"],
        "media": ["player", "video", "audio", "playlist", "stream"]
    }

    @classmethod
    def ensure_dirs(cls):
        """필요한 디렉토리 생성"""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)
        cls.PROJECTS_DIR.mkdir(exist_ok=True)


# 디렉토리 생성
Config.ensure_dirs()

# Token 로드 확인
if Config.GITHUB_TOKEN:
    print(f"✅ GitHub Token loaded (length: {len(Config.GITHUB_TOKEN)})")
else:
    print("⚠️  GitHub Token not found. Set GITHUB_TOKEN in .env file")