"""Parity and health tests for biotec-line organization profile and public catalog."""

import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

PARITY_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "profile" / "README.md",
    REPO_ROOT / "profile" / "README_de.md",
    REPO_ROOT / "llms.txt",
    REPO_ROOT / "CHANGELOG.md",
]


@pytest.fixture(scope="module")
def file_contents():
    contents = {}
    for path in PARITY_FILES:
        assert path.is_file(), f"Required file missing: {path}"
        data = path.read_bytes()
        text = data.decode("utf-8")
        assert "\ufffd" not in text, f"Invalid UTF-8 character in {path}"
        rel_key = path.relative_to(REPO_ROOT).as_posix()
        contents[rel_key] = text
    return contents


def test_markdown_fence_balance(file_contents):
    """Verify that all markdown files have balanced triple backticks."""
    for filename, text in file_contents.items():
        if filename.endswith((".md", ".txt")):
            matches = re.findall(r"^```", text, flags=re.MULTILINE)
            assert len(matches) % 2 == 0, f"Unbalanced code fences in {filename}: {len(matches)} count"


def test_public_repo_inventory(file_contents):
    """Verify that all 3 public repositories are mentioned in index files."""
    required_repos = ["genotype-to-vcf", "VFDistiller", ".github"]
    for filename in ["README.md", "profile/README.md", "profile/README_de.md", "llms.txt", "CHANGELOG.md"]:
        text = file_contents[filename]
        for repo in required_repos:
            assert repo in text, f"Missing public repo '{repo}' in {filename}"


def test_check_timestamp_parity(file_contents):
    """Verify that check timestamps are synchronized to 2026-09-09."""
    assert "2026-09-09" in file_contents["README.md"]
    assert "2026-09-09" in file_contents["profile/README.md"]
    assert "9. September 2026" in file_contents["profile/README_de.md"]
    assert "2026-09-09" in file_contents["llms.txt"]
    assert "2026-09-09" in file_contents["CHANGELOG.md"]


def test_push_timestamp_parity(file_contents):
    """Verify that latest push timestamps match repository metadata."""
    for filename in ["README.md", "profile/README.md", "profile/README_de.md", "llms.txt", "CHANGELOG.md"]:
        text = file_contents[filename]
        assert "2026-08-14" in text, f"Missing VFDistiller push date 2026-08-14 in {filename}"
        assert "2026-08-05" in text, f"Missing genotype-to-vcf push date 2026-08-05 in {filename}"
        assert "2026-09-09" in text, f"Missing .github push date 2026-09-09 in {filename}"


def test_ecosystem_cross_linking(file_contents):
    """Verify that all sister organizations are properly linked."""
    ecosystem_orgs = [
        "open-bricks",
        "research-line",
        "ellmos-ai",
        "doc-bricks",
        "dev-bricks",
        "file-bricks",
        "entertain-and-more",
        "assistassets-ai",
        "um-bruch",
        "lukisch",
    ]
    for org in ecosystem_orgs:
        assert org in file_contents["profile/README.md"], f"Missing ecosystem org '{org}' in English profile"
        assert org in file_contents["profile/README_de.md"], f"Missing ecosystem org '{org}' in German profile"
        assert org in file_contents["llms.txt"], f"Missing ecosystem org '{org}' in llms.txt"


def test_banner_urls_and_assets(file_contents):
    """Verify that banner assets are referenced correctly."""
    assert "genotype-to-vcf/master/assets/banner.svg" in file_contents["profile/README.md"]
    assert "VFDistiller/main/assets/banner.svg" in file_contents["profile/README.md"]
    assert "genotype-to-vcf/master/assets/banner.svg" in file_contents["profile/README_de.md"]
    assert "VFDistiller/main/assets/banner.svg" in file_contents["profile/README_de.md"]


def test_research_use_boundary_disclaimer(file_contents):
    """Verify that Research Use Only boundary is stated."""
    assert "Research Use Only" in file_contents["profile/README.md"]
    assert "Forschungszwecke" in file_contents["profile/README_de.md"]
    assert "Not for clinical or diagnostic use" in file_contents["llms.txt"]
