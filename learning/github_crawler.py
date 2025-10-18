# learning/github_crawler.py (개선 버전)

import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from config import Config


class GitHubCrawler:
    """GitHub에서 Swift 프로젝트를 수집"""

    def __init__(self):
        self.token = Config.GITHUB_TOKEN
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_language_stats(self, owner: str, repo: str) -> Dict[str, int]:
        """
        저장소의 언어 통계 가져오기

        Args:
            owner: 소유자
            repo: 저장소 이름

        Returns:
            언어별 바이트 수 딕셔너리
        """
        try:
            url = f"{Config.GITHUB_API_URL}/repos/{owner}/{repo}/languages"
            response = self.session.get(url)

            if response.status_code == 200:
                return response.json()
        except:
            pass

        return {}

    def calculate_swift_percentage(self, languages: Dict[str, int]) -> float:
        """
        Swift 비율 계산

        Args:
            languages: 언어별 바이트 수

        Returns:
            Swift 비율 (0.0 ~ 1.0)
        """
        if not languages:
            return 0.0

        total_bytes = sum(languages.values())
        swift_bytes = languages.get("Swift", 0)

        if total_bytes == 0:
            return 0.0

        return swift_bytes / total_bytes

    def search_repositories(
            self,
            language: str = "Swift",
            min_stars: int = 100,
            max_results: int = 50,
            min_swift_percentage: float = 0.8  # ✅ Swift 80% 이상
    ) -> List[Dict]:
        """
        GitHub에서 저장소 검색

        Args:
            language: 프로그래밍 언어
            min_stars: 최소 스타 수
            max_results: 최대 결과 수
            min_swift_percentage: 최소 Swift 비율 (0.0 ~ 1.0)

        Returns:
            저장소 정보 리스트
        """
        print(f"🔍 Searching GitHub repositories...")
        print(f"   Language: {language}, Min Stars: {min_stars}")
        print(f"   Min Swift %: {min_swift_percentage * 100:.0f}%")
        print(f"   Target: {max_results} projects")

        query = f"language:{language} stars:>={min_stars}"
        url = f"{Config.GITHUB_API_URL}/search/repositories"

        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 100  # ✅ 많이 가져온 후 필터링
        }

        repositories = []
        page = 1
        checked_count = 0
        max_checks = max_results * 3  # ✅ 목표의 3배까지 검사

        while len(repositories) < max_results and checked_count < max_checks:
            params["page"] = page

            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                items = data.get("items", [])

                if not items:
                    break

                for item in items:
                    if len(repositories) >= max_results:
                        break

                    checked_count += 1

                    owner = item["owner"]["login"]
                    repo_name = item["name"]

                    # ✅ 언어 통계 가져오기
                    languages = self.get_language_stats(owner, repo_name)
                    swift_percentage = self.calculate_swift_percentage(languages)

                    # ✅ Swift 비율 체크
                    if swift_percentage < min_swift_percentage:
                        print(f"   ⏭️  [{checked_count}] {item['full_name']} - Swift {swift_percentage:.1%} (skip)")
                        continue

                    repo_info = {
                        "name": item["name"],
                        "full_name": item["full_name"],
                        "owner": owner,
                        "stars": item["stargazers_count"],
                        "forks": item["forks_count"],
                        "language": item["language"],
                        "swift_percentage": swift_percentage,  # ✅ 추가
                        "languages": languages,  # ✅ 추가
                        "description": item.get("description", ""),
                        "url": item["html_url"],
                        "clone_url": item["clone_url"],
                        "default_branch": item["default_branch"],
                        "created_at": item["created_at"],
                        "updated_at": item["updated_at"]
                    }

                    repositories.append(repo_info)
                    print(
                        f"   ✅ [{len(repositories)}/{max_results}] {repo_info['full_name']} ({repo_info['stars']}⭐, Swift {swift_percentage:.1%})")

                    # Rate limit 조심
                    time.sleep(0.5)  # ✅ API 호출 간 대기

                page += 1

                # Rate limit 체크
                if response.headers.get("X-RateLimit-Remaining") == "0":
                    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                    wait_time = reset_time - time.time()
                    if wait_time > 0:
                        print(f"⏳ Rate limit reached. Waiting {wait_time:.0f}s...")
                        time.sleep(wait_time + 1)

            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching repositories: {e}")
                break

        print(f"\n✅ Found {len(repositories)} repositories (checked {checked_count})")
        print(f"   Average Swift %: {sum(r['swift_percentage'] for r in repositories) / len(repositories) * 100:.1f}%")

        return repositories

    # ... 나머지 메서드는 동일 ...

    def get_repository_dependencies(self, owner: str, repo: str) -> List[str]:
        """저장소의 의존성 확인 (Package.swift, Podfile)"""
        dependencies = []

        # Package.swift 확인
        try:
            url = f"{Config.GITHUB_API_URL}/repos/{owner}/{repo}/contents/Package.swift"
            response = self.session.get(url)

            if response.status_code == 200:
                content = response.json()
                import base64
                decoded = base64.b64decode(content["content"]).decode("utf-8")

                for framework in Config.POPULAR_FRAMEWORKS:
                    if framework.lower() in decoded.lower():
                        dependencies.append(framework)
        except:
            pass

        # Podfile 확인
        try:
            url = f"{Config.GITHUB_API_URL}/repos/{owner}/{repo}/contents/Podfile"
            response = self.session.get(url)

            if response.status_code == 200:
                content = response.json()
                import base64
                decoded = base64.b64decode(content["content"]).decode("utf-8")

                for framework in Config.POPULAR_FRAMEWORKS:
                    if framework.lower() in decoded.lower():
                        if framework not in dependencies:
                            dependencies.append(framework)
        except:
            pass

        return dependencies

    def download_repository(self, repo_info: Dict) -> Optional[Path]:
        """저장소를 로컬로 다운로드"""
        full_name = repo_info["full_name"].replace("/", "_")
        target_dir = Config.PROJECTS_DIR / full_name

        if target_dir.exists():
            print(f"   ⏭️  Already exists: {full_name}")
            return target_dir

        swift_pct = repo_info.get("swift_percentage", 0)
        print(f"   📥 Downloading: {repo_info['full_name']} (Swift {swift_pct:.1%})...")

        try:
            import subprocess

            result = subprocess.run(
                ["git", "clone", "--depth", "1", repo_info["clone_url"], str(target_dir)],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print(f"   ✅ Downloaded: {full_name}")
                return target_dir
            else:
                print(f"   ❌ Failed: {result.stderr}")
                return None

        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None

    def save_projects(self, projects: List[Dict], filename: str = "projects.json"):
        """프로젝트 목록 저장"""
        output_path = Config.DATA_DIR / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(projects, f, indent=2, ensure_ascii=False)

        print(f"💾 Saved {len(projects)} projects to {output_path}")

    def load_projects(self, filename: str = "projects.json") -> List[Dict]:
        """프로젝트 목록 로드"""
        input_path = Config.DATA_DIR / filename

        if not input_path.exists():
            return []

        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)


def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("🚀 GitHub Swift Project Crawler")
    print("=" * 70)

    crawler = GitHubCrawler()

    # 1. 프로젝트 검색
    projects = crawler.search_repositories(
        language=Config.LANGUAGE,
        min_stars=Config.MIN_STARS,
        max_results=Config.MAX_PROJECTS,
        min_swift_percentage=0.8  # ✅ Swift 80% 이상
    )

    # 2. 의존성 확인
    print("\n📦 Checking dependencies...")
    for i, project in enumerate(projects, 1):
        print(f"   [{i}/{len(projects)}] {project['full_name']}")
        deps = crawler.get_repository_dependencies(
            project["owner"],
            project["name"]
        )
        project["dependencies"] = deps
        if deps:
            print(f"      Dependencies: {', '.join(deps)}")

    # 3. 저장
    crawler.save_projects(projects)

    # 4. 다운로드 (선택적)
    print("\n📥 Download projects? (y/n): ", end="")
    choice = input().strip().lower()

    if choice == "y":
        print("\n📥 Downloading projects...")
        downloaded = 0
        for i, project in enumerate(projects, 1):
            print(f"\n[{i}/{len(projects)}]")
            path = crawler.download_repository(project)
            if path:
                project["local_path"] = str(path)
                downloaded += 1

        print(f"\n✅ Downloaded {downloaded}/{len(projects)} projects")
        crawler.save_projects(projects)

    print("\n" + "=" * 70)
    print("🎉 Crawling completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()