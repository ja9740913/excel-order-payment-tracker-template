from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "release-manifest.json"
CHECKSUM_PATH = ROOT / "SHA256SUMS.txt"

EXPECTED_FILES = {
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "release-manifest.json",
    "SHA256SUMS.txt",
    "verify_release.py",
    "release/Payment-Risk-Check-Lite-v1.0.0.zip",
    "workbooks/01-payment-risk-check-lite-blank.xlsx",
    "workbooks/02-payment-risk-check-lite-demo.xlsx",
    "assets/cover-1280x720.png",
    "assets/feature-checks-1280x720.png",
    "assets/thumbnail-600x600.png",
}

EXPECTED_CONTENT_URLS = {
    "https://payment-flow-studio-tw.masstech.chatgpt.site/en/free?source=github_lite_readme",
    "https://payment-flow-studio-tw.masstech.chatgpt.site/en/templates/payment-tracker-excel-template?source=github_lite_paid",
    "https://toolcraftstudio.gumroad.com/l/order-payment-dashboard-excel",
}

EXPECTED_REPOSITORY_URL = "https://github.com/ja9740913/excel-order-payment-tracker-template"
EXPECTED_RELEASE_URL = f"{EXPECTED_REPOSITORY_URL}/releases/tag/v1.0.0"
EXPECTED_RELEASE_ASSET_URL = (
    f"{EXPECTED_REPOSITORY_URL}/releases/download/v1.0.0/Payment-Risk-Check-Lite-v1.0.0.zip"
)
GITHUB_RELEASE_API_URL = (
    "https://api.github.com/repos/ja9740913/excel-order-payment-tracker-template/releases/tags/v1.0.0"
)
PREPARED_STATUS_MARKER = (
    "> Publication status: this package was prepared locally for a future GitHub repository. "
    "No remote repository or GitHub release has been created, and nothing in this folder has "
    "been uploaded by the preparation process."
)
PUBLISHED_STATUS_MARKER = (
    f"> Publication status: published at {EXPECTED_REPOSITORY_URL}. "
    f"The verified v1.0.0 release is available at {EXPECTED_RELEASE_URL}."
)

EXPECTED_ZIP_MEMBERS = [
    "01-payment-risk-check-lite-blank.xlsx",
    "02-payment-risk-check-lite-demo.xlsx",
    "README-QUICK-START.txt",
    "FREE-SAMPLE-LICENSE.txt",
    "SHA256SUMS.txt",
]

TEXT_FILES = {
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "release-manifest.json",
    "SHA256SUMS.txt",
    "verify_release.py",
}
PUBLIC_TEXT_FILES = TEXT_FILES - {"verify_release.py"}

URL_RE = re.compile(r"https://[^\s<>)\]\"']+")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
ABSOLUTE_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/](?:Users|Documents|OneDrive)[\\/]|/home/|/Users/)")
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret|otp)\b\s*[:=]\s*[\"']?[^\s,}\"']{6,}"
)
FORBIDDEN_FILENAME_RE = re.compile(
    r"(?i)(?:order-payment-dashboard|commercial.*\.(?:zip|xlsx)|paid.*\.(?:zip|xlsx)|"
    r"test[-_ ]?purchase|receipt|credential|password|private[-_ ]?key|\.env$|\.pem$|\.pfx$|\.key$)"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(expected_state: str) -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    require(manifest["schema_version"] == 1, "unsupported manifest schema")
    require(manifest["product"]["name"] == "Payment Risk Check Lite", "product identity mismatch")
    require(manifest["product"]["version"] == "1.0.0", "release version mismatch")
    expected_status = "prepared-local-only" if expected_state == "prepared" else "published"
    require(manifest["product"]["publication_status"] == expected_status, f"publication status is not {expected_status}")
    return manifest


def verify_inventory(expected_state: str) -> None:
    found = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(ROOT).parts
    }
    require(found == EXPECTED_FILES, f"unexpected public inventory: missing={sorted(EXPECTED_FILES - found)} extra={sorted(found - EXPECTED_FILES)}")
    if expected_state == "prepared":
        require(not (ROOT / ".git").exists(), "nested Git metadata exists; local-only preparation state is no longer clean")
    for relative in found:
        path = ROOT / relative
        require(not path.is_symlink(), f"symlinks are not allowed: {relative}")
        require(not FORBIDDEN_FILENAME_RE.search(relative), f"forbidden or paid/private filename detected: {relative}")


def parse_checksums() -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line_number, line in enumerate(CHECKSUM_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        require(match is not None, f"invalid checksum line {line_number}")
        digest, relative = match.groups()
        require(relative not in checksums, f"duplicate checksum path: {relative}")
        checksums[relative] = digest
    return checksums


def verify_hashes(manifest: dict) -> dict[str, str]:
    assets = {item["path"]: item["sha256"] for item in manifest["assets"]}
    require(len(assets) == len(manifest["assets"]), "duplicate asset path in manifest")
    require(all(item["public"] is True for item in manifest["assets"]), "all packaged assets must be explicitly public")
    checksums = parse_checksums()
    require(checksums == assets, "manifest assets and SHA256SUMS.txt differ")
    for relative, expected in checksums.items():
        path = ROOT / relative
        require(path.is_file(), f"hashed asset missing: {relative}")
        require(sha256(path) == expected, f"SHA-256 mismatch: {relative}")
    return checksums


def verify_local_links() -> None:
    for relative in PUBLIC_TEXT_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_RE.findall(text):
            target = target.strip().strip("<>")
            if target.startswith(("https://", "#")):
                continue
            local_part = target.split("#", 1)[0]
            require(local_part != "", f"empty local link in {relative}")
            require((ROOT / local_part).is_file(), f"broken local link in {relative}: {target}")


def extract_urls() -> set[str]:
    urls: set[str] = set()
    for relative in PUBLIC_TEXT_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        urls.update(match.rstrip(".,;:!?") for match in URL_RE.findall(text))
    return urls


def check_live_url(url: str) -> tuple[int, str]:
    headers = {"User-Agent": "Payment-Risk-Check-Lite-Verifier/1.0"}
    for method in ("HEAD", "GET"):
        request = Request(url, headers=headers, method=method)
        try:
            with urlopen(request, timeout=20) as response:
                status = response.getcode()
                require(200 <= status < 400, f"link returned HTTP {status}: {url}")
                return status, response.geturl()
        except HTTPError as exc:
            if method == "HEAD" and exc.code in {403, 405}:
                continue
            raise AssertionError(f"link returned HTTP {exc.code}: {url}") from exc
        except URLError as exc:
            raise AssertionError(f"link check failed: {url}: {exc.reason}") from exc
    raise AssertionError(f"link check failed: {url}")


def verify_urls(manifest: dict, offline: bool, expected_state: str) -> list[tuple[str, int, str]]:
    manifest_urls = set(manifest["links"].values())
    require(manifest_urls == EXPECTED_CONTENT_URLS, "manifest content URL set changed")
    found_urls = extract_urls()
    expected_urls = set(EXPECTED_CONTENT_URLS)
    if expected_state == "published":
        expected_urls.update({EXPECTED_REPOSITORY_URL, EXPECTED_RELEASE_URL, EXPECTED_RELEASE_ASSET_URL})
    require(found_urls == expected_urls, f"unapproved or missing URL: expected={sorted(expected_urls)} found={sorted(found_urls)}")
    verify_local_links()
    if offline:
        return []
    results = []
    for url in sorted(found_urls - {EXPECTED_RELEASE_ASSET_URL}):
        status, final_url = check_live_url(url)
        results.append((url, status, final_url))
    return results


def verify_text_safety() -> None:
    # The verifier contains the detection patterns as source code, so scan the
    # public-facing text payloads here and validate the script by inventory.
    for relative in PUBLIC_TEXT_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        require("-----BEGIN PRIVATE KEY-----" not in text, f"private key material in {relative}")
        require(not EMAIL_RE.search(text), f"email address detected in {relative}")
        require(not ABSOLUTE_PATH_RE.search(text), f"local absolute path detected in {relative}")
        require(not SECRET_ASSIGNMENT_RE.search(text), f"credential-like assignment detected in {relative}")


def validate_external_state_contract(manifest: dict, expected_state: str) -> None:
    state = manifest["external_state"]
    require(set(state) == {
        "remote_repository_created",
        "remote_repository_url",
        "github_release_created",
        "github_release_url",
        "release_asset_url",
        "files_uploaded",
        "published_at",
        "external_write_performed_by_preparation",
    }, "external-state schema changed")
    require(state["external_write_performed_by_preparation"] is False, "manifest claims an external write occurred")
    if expected_state == "prepared":
        require(state["remote_repository_created"] is False, "manifest claims a remote repository exists")
        require(state["remote_repository_url"] is None, "manifest contains a remote repository URL")
        require(state["github_release_created"] is False, "manifest claims a GitHub release exists")
        require(state["github_release_url"] is None, "manifest contains a GitHub release URL")
        require(state["release_asset_url"] is None, "manifest contains a release asset URL")
        require(state["files_uploaded"] is False, "manifest claims files were uploaded")
        require(state["published_at"] is None, "manifest contains a publication timestamp")
    else:
        require(state["remote_repository_created"] is True, "manifest does not confirm the public repository")
        require(state["remote_repository_url"] == EXPECTED_REPOSITORY_URL, "published repository URL mismatch")
        require(state["github_release_created"] is True, "manifest does not confirm the GitHub release")
        require(state["github_release_url"] == EXPECTED_RELEASE_URL, "published release URL mismatch")
        require(state["release_asset_url"] == EXPECTED_RELEASE_ASSET_URL, "published release asset URL mismatch")
        require(state["files_uploaded"] is True, "manifest does not confirm uploaded files")
        require(isinstance(state["published_at"], str), "published_at must be a timestamp string")
        require(re.fullmatch(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})", state["published_at"]) is not None, "published_at is not RFC 3339 seconds precision")


def verify_external_state(manifest: dict, expected_state: str) -> None:
    validate_external_state_contract(manifest, expected_state)
    git = subprocess.run(
        ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )
    if expected_state == "prepared":
        require(git.returncode != 0 or git.stdout.strip() == "", "a Git remote is configured; local-only publication state is no longer true")
    elif git.returncode == 0:
        require(git.stdout.strip().removesuffix(".git") == EXPECTED_REPOSITORY_URL, "Git origin does not match the published repository")


def verify_readme_publication_marker(expected_state: str) -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    expected = PREPARED_STATUS_MARKER if expected_state == "prepared" else PUBLISHED_STATUS_MARKER
    forbidden = PUBLISHED_STATUS_MARKER if expected_state == "prepared" else PREPARED_STATUS_MARKER
    require(expected in text, f"README publication marker does not match {expected_state} state")
    require(forbidden not in text, "README contains conflicting publication states")


def verify_contract_fixtures(manifest: dict) -> None:
    prepared = json.loads(json.dumps(manifest))
    prepared["product"]["publication_status"] = "prepared-local-only"
    prepared["external_state"] = {
        "remote_repository_created": False,
        "remote_repository_url": None,
        "github_release_created": False,
        "github_release_url": None,
        "release_asset_url": None,
        "files_uploaded": False,
        "published_at": None,
        "external_write_performed_by_preparation": False,
    }
    validate_external_state_contract(prepared, "prepared")
    published = json.loads(json.dumps(prepared))
    published["product"]["publication_status"] = "published"
    published["external_state"].update({
        "remote_repository_created": True,
        "remote_repository_url": EXPECTED_REPOSITORY_URL,
        "github_release_created": True,
        "github_release_url": EXPECTED_RELEASE_URL,
        "release_asset_url": EXPECTED_RELEASE_ASSET_URL,
        "files_uploaded": True,
        "published_at": "2026-07-15T08:30:00+08:00",
    })
    validate_external_state_contract(published, "published")
    published["external_state"]["remote_repository_url"] = "https://github.com/example/wrong"
    try:
        validate_external_state_contract(published, "published")
    except AssertionError:
        pass
    else:
        raise AssertionError("published-state contract accepted a wrong repository URL")


def verify_remote_publication() -> tuple[int, int]:
    repo_status, _ = check_live_url(EXPECTED_REPOSITORY_URL)
    release_status, _ = check_live_url(EXPECTED_RELEASE_URL)
    request = Request(
        GITHUB_RELEASE_API_URL,
        headers={"User-Agent": "Payment-Risk-Check-Lite-Verifier/1.0", "Accept": "application/vnd.github+json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (HTTPError, URLError) as exc:
        raise AssertionError(f"GitHub release API check failed: {exc}") from exc
    require(payload["tag_name"] == "v1.0.0", "GitHub release tag mismatch")
    require(payload["draft"] is False and payload["prerelease"] is False, "GitHub release is not final/public")
    assets = payload["assets"]
    require(len(assets) == 1, "GitHub release must have exactly one asset")
    require(assets[0]["name"] == "Payment-Risk-Check-Lite-v1.0.0.zip", "GitHub release asset name mismatch")
    require(assets[0]["browser_download_url"] == EXPECTED_RELEASE_ASSET_URL, "GitHub release asset URL mismatch")
    return repo_status, release_status


def verify_workbook(path: Path) -> None:
    with ZipFile(path) as workbook:
        require(workbook.testzip() is None, f"corrupt workbook container: {path.name}")
        names = workbook.namelist()
        lower_names = [name.lower() for name in names]
        require("xl/vbaproject.bin" not in lower_names, f"VBA project detected: {path.name}")
        require(not any("/externallinks/" in name for name in lower_names), f"external workbook link detected: {path.name}")
        require("xl/connections.xml" not in lower_names, f"external connection detected: {path.name}")
        core = workbook.read("docProps/core.xml").decode("utf-8")
        require("Product Creator" in core, f"neutral creator metadata missing: {path.name}")
        require("fictional" in core.lower(), f"fictional-data declaration missing: {path.name}")
        xml_text = "\n".join(
            workbook.read(name).decode("utf-8")
            for name in names
            if name.endswith((".xml", ".rels"))
        )
        require(not EMAIL_RE.search(xml_text), f"email address detected in workbook: {path.name}")
        require(not ABSOLUTE_PATH_RE.search(xml_text), f"local path detected in workbook: {path.name}")
        require("phone number" not in xml_text.lower() and "telephone" not in xml_text.lower(), f"phone field detected in workbook: {path.name}")


def read_png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"invalid PNG signature: {path.name}")
    require(len(data) >= 24 and data[12:16] == b"IHDR", f"missing PNG IHDR: {path.name}")
    offset = 8
    chunks: list[bytes] = []
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        payload_end = offset + 8 + length
        require(payload_end + 4 <= len(data), f"truncated PNG chunk: {path.name}")
        payload = data[offset + 8 : payload_end]
        recorded_crc = struct.unpack(">I", data[payload_end : payload_end + 4])[0]
        require(zlib.crc32(chunk_type + payload) & 0xFFFFFFFF == recorded_crc, f"PNG CRC mismatch: {path.name}")
        chunks.append(chunk_type)
        offset = payload_end + 4
        if chunk_type == b"IEND":
            break
    require(offset == len(data), f"unexpected bytes after PNG IEND: {path.name}")
    require(chunks[0] == b"IHDR" and chunks[-1] == b"IEND", f"invalid PNG chunk order: {path.name}")
    require(set(chunks) <= {b"IHDR", b"pHYs", b"IDAT", b"IEND"}, f"unapproved PNG metadata chunk: {path.name}")
    return struct.unpack(">II", data[16:24])


def verify_pngs(manifest: dict) -> None:
    for item in manifest["assets"]:
        if item["path"].endswith(".png"):
            size = read_png_size(ROOT / item["path"])
            require(size == (item["width"], item["height"]), f"PNG dimensions changed: {item['path']}")


def verify_release_zip(checksums: dict[str, str]) -> None:
    release_path = ROOT / "release/Payment-Risk-Check-Lite-v1.0.0.zip"
    with ZipFile(release_path) as archive:
        require(archive.testzip() is None, "release ZIP failed CRC validation")
        require(archive.namelist() == EXPECTED_ZIP_MEMBERS, f"release ZIP member list changed: {archive.namelist()}")
        require(all(not item.flag_bits & 0x1 for item in archive.infolist()), "encrypted ZIP member detected")
        internal: dict[str, str] = {}
        for line in archive.read("SHA256SUMS.txt").decode("utf-8").splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
            require(match is not None, "invalid internal ZIP checksum line")
            digest, name = match.groups()
            require(name not in internal, f"duplicate internal ZIP checksum: {name}")
            internal[name] = digest
        require(list(internal) == EXPECTED_ZIP_MEMBERS[:-1], "internal ZIP checksum inventory changed")
        for name, expected in internal.items():
            require(hashlib.sha256(archive.read(name)).hexdigest() == expected, f"internal ZIP hash mismatch: {name}")
        for name in EXPECTED_ZIP_MEMBERS[:2]:
            public_copy = ROOT / "workbooks" / name
            require(hashlib.sha256(archive.read(name)).hexdigest() == checksums[public_copy.relative_to(ROOT).as_posix()], f"ZIP workbook and public copy differ: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the local Payment Risk Check Lite public distribution package.")
    parser.add_argument("--offline", action="store_true", help="skip live HTTP checks; local links and all integrity checks still run")
    parser.add_argument("--state", choices=("prepared", "published"), default="prepared", help="verify the pre-publication or public evidence contract")
    args = parser.parse_args()

    manifest = load_manifest(args.state)
    verify_contract_fixtures(manifest)
    verify_inventory(args.state)
    checksums = verify_hashes(manifest)
    verify_text_safety()
    verify_external_state(manifest, args.state)
    verify_readme_publication_marker(args.state)
    verify_workbook(ROOT / "workbooks/01-payment-risk-check-lite-blank.xlsx")
    verify_workbook(ROOT / "workbooks/02-payment-risk-check-lite-demo.xlsx")
    verify_pngs(manifest)
    verify_release_zip(checksums)
    live_results = verify_urls(manifest, args.offline, args.state)
    remote_statuses = None
    if args.state == "published" and not args.offline:
        remote_statuses = verify_remote_publication()

    print("Payment Risk Check Lite public package verifier passed")
    print(f"Inventory: {len(EXPECTED_FILES)} exact files / {len(checksums)} hash-verified binary assets")
    print("Leak gate: no paid ZIP, unexpected binary, credential-like assignment, private key, email, or local path")
    if args.state == "prepared":
        print("External state: prepared locally / no nested repository / no configured Git remote / no GitHub release / no upload")
    else:
        print("External state: manifest, README, repository, release, and single release asset agree")
    if args.offline:
        print("Links: approved URL contract recorded; live HTTP checks skipped by --offline")
    else:
        for url, status, final_url in live_results:
            print(f"Link: HTTP {status} {url} -> {final_url}")
        if remote_statuses is not None:
            print(f"GitHub publication: repository HTTP {remote_statuses[0]} / release HTTP {remote_statuses[1]} / one API-confirmed asset")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"VERIFY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
