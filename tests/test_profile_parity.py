"""Parity and health tests for biotec-line organization profile and public catalog."""

import re
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

SOURCE_PATHS = {
    "root_readme": REPO_ROOT / "README.md",
    "profile_readme_en": REPO_ROOT / "profile" / "README.md",
    "profile_readme_de": REPO_ROOT / "profile" / "README_de.md",
    "llms": REPO_ROOT / "llms.txt",
    "changelog": REPO_ROOT / "CHANGELOG.md",
}
SOURCE_IDS = tuple(SOURCE_PATHS)
REQUIRED_REPOS = ("genotype-to-vcf", "VFDistiller", ".github")
ISO_DATE = r"\d{4}-\d{2}-\d{2}"
LAST_CHECK_PATTERNS = {
    "root_readme": rf"<!-- public-index-last-checked:\s*({ISO_DATE})\s*-->",
    "profile_readme_en": rf"<!-- last-checked:\s*({ISO_DATE})\s*-->",
    "profile_readme_de": rf"<!-- last-checked:\s*({ISO_DATE})\s*-->",
    "llms": rf"^## Last-checked:\s*({ISO_DATE})\s*$",
    "changelog": rf"<!-- last-checked:\s*({ISO_DATE})\s*-->",
}
INVENTORY_HEADINGS = {
    "root_readme": "## Public Repository Directory",
    "profile_readme_en": "## Public Repository Directory",
    "profile_readme_de": "## Verzeichnis Öffentlicher Repositories",
    "llms": "## Public repository directory",
}


def latest_changelog_section(text):
    """Return only the newest version section, excluding historical snapshots."""
    headings = list(re.finditer(rf"^## \[[^]]+\] - {ISO_DATE}\s*$", text, re.MULTILINE))
    assert headings, "No versioned changelog section found"
    end = headings[1].start() if len(headings) > 1 else len(text)
    return text[headings[0].start() : end]


def current_text(source_id, text):
    """Limit snapshot-like parsing to the current declaration."""
    return latest_changelog_section(text) if source_id == "changelog" else text


def markdown_section(text, heading):
    match = re.search(
        rf"^{re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE,
    )
    assert match, f"Required section missing: {heading}"
    return match.group(1)


def extract_last_checked(source_id, text):
    matches = re.findall(
        LAST_CHECK_PATTERNS[source_id],
        current_text(source_id, text),
        flags=re.MULTILINE,
    )
    assert len(matches) == 1, f"Expected one last-checked marker in {source_id}, found {matches}"
    return matches[0]


def assert_last_checked_parity(contents):
    declared_dates = {
        source_id: extract_last_checked(source_id, contents[source_id])
        for source_id in SOURCE_IDS
    }
    assert len(set(declared_dates.values())) == 1, f"Last-checked mismatch: {declared_dates}"


def activity_declaration(source_id, text):
    """Select only lines that explicitly declare current repository activity."""
    text = current_text(source_id, text)
    if source_id == "changelog":
        lines = [line for line in text.splitlines() if "Push Metadata" in line]
    elif source_id == "llms":
        lines = [line for line in text.splitlines() if "last public push" in line]
    else:
        lines = [
            line
            for line in text.splitlines()
            if line.startswith("| [") and "github.com/biotec-line/" in line
        ]
    assert lines, f"No current repository activity declaration found in {source_id}"
    return "\n".join(lines)


def extract_repo_activity(source_id, text):
    declaration = activity_declaration(source_id, text)
    activity = {}
    for repo in REQUIRED_REPOS:
        if source_id == "llms":
            pattern = rf"{re.escape(repo)}\s+last public push\s+({ISO_DATE})"
        elif source_id == "changelog":
            pattern = rf"`{re.escape(repo)}`\s+\(`({ISO_DATE})`\)"
        else:
            pattern = rf"{re.escape(repo)}[^\n]*?\b({ISO_DATE})\b"
        matches = re.findall(pattern, declaration)
        assert len(matches) == 1, f"Expected one current activity date for {repo} in {source_id}"
        activity[repo] = matches[0]
    return activity


def extract_public_repo_inventory(source_id, text):
    if source_id == "changelog":
        declaration = "\n".join(
            line
            for line in latest_changelog_section(text).splitlines()
            if "Repository Index Refresh" in line
        )
        assert declaration, "No current repository inventory declaration found in changelog"
        markers = {repo: f"`{repo}`" for repo in REQUIRED_REPOS}
    else:
        declaration = markdown_section(text, INVENTORY_HEADINGS[source_id])
        markers = {
            repo: f"https://github.com/biotec-line/{repo}" for repo in REQUIRED_REPOS
        }
    return {repo for repo, marker in markers.items() if marker in declaration}


def assert_public_repo_inventory(source_id, text):
    inventory = extract_public_repo_inventory(source_id, text)
    expected = set(REQUIRED_REPOS)
    assert inventory == expected, f"Public repository inventory mismatch in {source_id}: {inventory}"


@pytest.fixture(scope="module")
def file_contents():
    contents = {}
    for source_id, path in SOURCE_PATHS.items():
        assert path.is_file(), f"Required file missing: {path}"
        data = path.read_bytes()
        text = data.decode("utf-8")
        assert "\ufffd" not in text, f"Invalid UTF-8 character in {path}"
        contents[source_id] = text
    return contents


def test_sources_have_unique_addresses():
    relative_paths = [path.relative_to(REPO_ROOT).as_posix() for path in SOURCE_PATHS.values()]
    assert len(relative_paths) == 5
    assert len(set(relative_paths)) == len(relative_paths)
    assert SOURCE_PATHS["root_readme"] != SOURCE_PATHS["profile_readme_en"]


def test_markdown_fence_balance(file_contents):
    """Verify that all markdown files have balanced triple backticks."""
    for filename, text in file_contents.items():
        if filename.endswith((".md", ".txt")):
            matches = re.findall(r"^```", text, flags=re.MULTILINE)
            assert len(matches) % 2 == 0, f"Unbalanced code fences in {filename}: {len(matches)} count"


@pytest.mark.parametrize("source_id", SOURCE_IDS)
def test_public_repo_inventory(file_contents, source_id):
    """Verify that all 3 public repositories are mentioned in index files."""
    assert_public_repo_inventory(source_id, file_contents[source_id])


def test_public_repo_inventory_parity(file_contents):
    inventories = {
        source_id: extract_public_repo_inventory(source_id, file_contents[source_id])
        for source_id in SOURCE_IDS
    }
    assert len({frozenset(inventory) for inventory in inventories.values()}) == 1, inventories


@pytest.mark.parametrize("source_id", SOURCE_IDS)
def test_inventory_regression_isolated_per_source(file_contents, source_id):
    """Prove that an isolated inventory drift is detected in every source."""
    mutated = re.sub(re.escape("VFDistiller"), "missing-repository", file_contents[source_id])
    with pytest.raises(AssertionError, match="inventory mismatch"):
        assert_public_repo_inventory(source_id, mutated)


def test_check_timestamp_parity(file_contents):
    """Compare the last-checked values declared by all five sources."""
    assert_last_checked_parity(file_contents)


@pytest.mark.parametrize("source_id", SOURCE_IDS)
def test_check_timestamp_regression_isolated_per_source(file_contents, source_id):
    """Prove that an isolated marker drift is detected in every source."""
    current = extract_last_checked(source_id, file_contents[source_id])
    replacement = (date.fromisoformat(current) + timedelta(days=1)).isoformat()
    mutated_text, replacements = re.subn(
        LAST_CHECK_PATTERNS[source_id],
        lambda match: match.group(0).replace(match.group(1), replacement),
        file_contents[source_id],
        count=1,
        flags=re.MULTILINE,
    )
    assert replacements == 1
    mutated_contents = {**file_contents, source_id: mutated_text}
    with pytest.raises(AssertionError, match="Last-checked mismatch"):
        assert_last_checked_parity(mutated_contents)


def test_push_timestamp_parity(file_contents):
    """Compare parsed current activity dates instead of fixed snapshots."""
    activity_by_source = {
        source_id: extract_repo_activity(source_id, file_contents[source_id])
        for source_id in SOURCE_IDS
    }
    for repo in REQUIRED_REPOS:
        repo_dates = {
            source_id: activity[repo] for source_id, activity in activity_by_source.items()
        }
        assert len(set(repo_dates.values())) == 1, f"Activity date mismatch for {repo}: {repo_dates}"


def test_ecosystem_cross_linking(file_contents):
    """Verify that all 9 sister organizations are properly linked."""
    ecosystem_orgs = [
        "open-bricks",
        "research-line",
        "ellmos-ai",
        "doc-bricks",
        "dev-bricks",
        "file-bricks",
        "entertain-and-more",
        "assistassets-ai",
        "lukisch",
    ]
    for org in ecosystem_orgs:
        assert org in file_contents["profile_readme_en"], f"Missing ecosystem org '{org}' in English profile"
        assert org in file_contents["profile_readme_de"], f"Missing ecosystem org '{org}' in German profile"
        assert org in file_contents["llms"], f"Missing ecosystem org '{org}' in llms.txt"


def test_banner_urls_and_assets(file_contents):
    """Verify that banner assets are referenced correctly."""
    assert "genotype-to-vcf/master/assets/banner.svg" in file_contents["profile_readme_en"]
    assert "VFDistiller/main/assets/banner.svg" in file_contents["profile_readme_en"]
    assert "genotype-to-vcf/master/assets/banner.svg" in file_contents["profile_readme_de"]
    assert "VFDistiller/main/assets/banner.svg" in file_contents["profile_readme_de"]


def test_profile_language_cross_links(file_contents):
    assert 'href="README_de.md"' in file_contents["profile_readme_en"]
    assert 'href="README.md"' in file_contents["profile_readme_de"]


def test_research_use_boundary_disclaimer(file_contents):
    """Verify that Research Use Only boundary is stated."""
    assert "Research Use Only" in file_contents["profile_readme_en"]
    assert "Forschungszwecke" in file_contents["profile_readme_de"]
    assert "Not for clinical or diagnostic use" in file_contents["llms"]
