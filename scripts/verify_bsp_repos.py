#!/usr/bin/env python3
"""Verify GL.iNet BSP repository contents against known Rockchip BSP commits.

Usage: uv run python3 scripts/verify_bsp_repos.py [--write]

Clones gl-inet/kernel-4.19 and gl-inet/buildroot-2018 (shallow, no checkout),
records commit metadata, and checks for absence of RM1-specific artifacts
(device trees, defconfigs, board overlays).

With --write, saves results to results/bsp_repos.toml.
Otherwise prints TOML to stdout.
"""

import argparse
import fnmatch
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import tomlkit

# Known Rockchip BSP commit hashes.
# Source: samueldr's diff analysis (KERNEL_DIFF_GIST below) compared GL.iNet's
# squashed commit against the Rockchip SDK release and found near-identical content.
# The Rockchip BSP SDK is distributed privately to partners; these commits are NOT
# reachable from the public rockchip-linux/kernel GitHub repo, so automated
# verification against upstream is not feasible.
KERNEL_BSP_COMMIT = "cc9228323509bf2bd59ed73ade9dd3276c97549c"
BUILDROOT_BSP_COMMIT = "a439fb32a06a78a2283aa03e32cabb6e531e73bd"

# Known tree SHAs from GL.iNet repos (content-addressable).
# If these change on a future run, GL.iNet has modified their repos.
KERNEL_KNOWN_TREE_SHA = "1dc3d7b37ac2410a89b20d376c3c43012f7baa24"
BUILDROOT_KNOWN_TREE_SHA = "7c66b4fcb991a19aed0d51bdfa7ab77c27b08bc8"

# Repository URLs
KERNEL_REPO_URL = "https://github.com/gl-inet/kernel-4.19.git"
BUILDROOT_REPO_URL = "https://github.com/gl-inet/buildroot-2018.git"

# External verification references
KERNEL_ISSUE_URL = "https://github.com/gl-inet/kernel-4.19/issues/1"
BUILDROOT_ISSUE_URL = "https://github.com/gl-inet/buildroot-2018/issues/1"
KERNEL_DIFF_GIST = "https://gist.github.com/samueldr/b68142df0b7843263294e913fee4f037"

# Patterns for RM1-specific files
KERNEL_RM1_DTS_PATTERNS = [
    "arch/arm/boot/dts/*rm1*",
    "arch/arm/boot/dts/*glrm1*",
    "arch/arm/boot/dts/*gl-rm1*",
]
KERNEL_RM1_DEFCONFIG_PATTERNS = [
    "arch/arm/configs/*rm1*",
    "arch/arm/configs/*glrm1*",
    "arch/arm/configs/*gl_rm1*",
]
BUILDROOT_RM1_DEFCONFIG_PATTERNS = [
    "configs/*rm1*",
    "configs/*glrm1*",
    "configs/*gl_rm1*",
]
# Broad GL.iNet search patterns (case-insensitive via fnmatch)
GLINET_PATTERNS = [
    "*gl-inet*",
    "*glinet*",
    "*gl_inet*",
]


def git(*args: str, cwd: Path | None = None) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def clone_shallow(url: str, dest: Path) -> None:
    """Shallow clone without checkout (downloads tree objects only)."""
    git("clone", "--depth=1", "--no-checkout", "--filter=blob:none", url, str(dest))


def get_commit_info(repo: Path) -> dict[str, str]:
    """Get HEAD commit metadata."""
    fmt = "%H%n%an%n%ae%n%aI%n%s%n%T"
    output = git("log", "-1", f"--format={fmt}", cwd=repo)
    lines = output.split("\n")
    return {
        "commit": lines[0],
        "author_name": lines[1],
        "author_email": lines[2],
        "author_date": lines[3],
        "subject": lines[4],
        "tree_sha": lines[5],
    }


def list_files(repo: Path) -> list[str]:
    """List all files in HEAD tree without checking out."""
    output = git("ls-tree", "-r", "--name-only", "HEAD", cwd=repo)
    return output.split("\n") if output else []


def count_commits(repo: Path) -> int:
    """Count commits reachable from HEAD (may be limited by clone depth)."""
    return int(git("rev-list", "--count", "HEAD", cwd=repo))


def find_matching(files: list[str], patterns: list[str]) -> list[str]:
    """Find files matching any of the given glob patterns."""
    matches = []
    for f in files:
        if any(fnmatch.fnmatch(f.lower(), p) for p in patterns):
            matches.append(f)
    return sorted(matches)


def list_defconfigs(files: list[str], prefix: str) -> list[str]:
    """List existing defconfig files under a prefix."""
    return sorted(f for f in files if f.startswith(prefix) and "defconfig" in f)


def verify_repo(url: str, tmpdir: str) -> tuple[dict[str, str], list[str], int]:
    """Clone and return (commit_info, file_list, commit_count)."""
    name = url.rstrip("/").split("/")[-1].replace(".git", "")
    repo = Path(tmpdir) / name
    print(f"Cloning {url} ...", file=sys.stderr)
    clone_shallow(url, repo)
    info = get_commit_info(repo)
    files = list_files(repo)
    count = count_commits(repo)
    print(f"  HEAD: {info['commit']}", file=sys.stderr)
    print(f"  Tree: {info['tree_sha']}", file=sys.stderr)
    print(f"  Author: {info['author_name']} <{info['author_email']}>", file=sys.stderr)
    print(f"  Date: {info['author_date']}", file=sys.stderr)
    print(f"  Subject: {info['subject']}", file=sys.stderr)
    print(f"  Commits: {count}", file=sys.stderr)
    print(f"  Files: {len(files)}", file=sys.stderr)
    return info, files, count


def add_repo_section(
    doc: tomlkit.TOMLDocument,
    prefix: str,
    label: str,
    url: str,
    bsp_commit: str,
    issue_url: str,
    info: dict[str, str],
    files: list[str],
    commit_count: int,
    rm1_checks: list[tuple[str, str, list[str], list[str]]],
    extra_checks: list[tuple[str, str, str, object]] | None = None,
) -> None:
    """Add a repository verification section to the TOML document."""
    doc.add(tomlkit.comment(f"--- {label} ---"))
    doc.add(tomlkit.nl())

    doc.add(tomlkit.comment("Source: GitHub repository"))
    doc.add(tomlkit.comment("Method: constant"))
    doc[f"{prefix}_repo_url"] = url.replace(".git", "")
    doc[f"{prefix}_issue_url"] = issue_url

    doc.add(tomlkit.nl())
    doc.add(tomlkit.comment("Source: git log -1"))
    doc.add(tomlkit.comment("Method: shallow clone, read commit metadata"))
    doc[f"{prefix}_head_commit"] = info["commit"]
    doc[f"{prefix}_tree_sha"] = info["tree_sha"]
    doc[f"{prefix}_commit_author"] = f"{info['author_name']} <{info['author_email']}>"
    doc[f"{prefix}_commit_date"] = info["author_date"]
    doc[f"{prefix}_commit_subject"] = info["subject"]
    doc[f"{prefix}_commit_count"] = commit_count

    doc.add(tomlkit.nl())
    doc.add(tomlkit.comment("Source: compare HEAD with known Rockchip BSP commit"))
    doc.add(tomlkit.comment("Method: GL.iNet squashed BSP into single commit; content equivalence"))
    doc.add(tomlkit.comment("verified externally via diff (see issue_url)"))
    doc[f"{prefix}_bsp_reference_commit"] = bsp_commit
    doc[f"{prefix}_is_squashed_import"] = commit_count == 1

    for field_suffix, method_comment, _patterns, found_files in rm1_checks:
        doc.add(tomlkit.nl())
        doc.add(tomlkit.comment("Source: git ls-tree -r HEAD | fnmatch"))
        doc.add(tomlkit.comment(f"Method: {method_comment}"))
        doc[f"{prefix}_{field_suffix}_found"] = len(found_files) > 0
        doc[f"{prefix}_{field_suffix}_files"] = found_files

    if extra_checks:
        for field_suffix, source_comment, method_comment, value in extra_checks:
            doc.add(tomlkit.nl())
            doc.add(tomlkit.comment(f"Source: {source_comment}"))
            doc.add(tomlkit.comment(f"Method: {method_comment}"))
            doc[f"{prefix}_{field_suffix}"] = value

    doc.add(tomlkit.nl())
    doc[f"{prefix}_total_files"] = len(files)


def build_toml() -> str:
    """Run verification and return TOML string."""
    doc = tomlkit.document()
    doc.add(tomlkit.comment("BSP repository verification results"))
    doc.add(tomlkit.comment(f"Generated: {datetime.now(UTC).isoformat()}"))
    doc.add(
        tomlkit.comment(
            "Method: git clone --depth=1 --no-checkout --filter=blob:none, git ls-tree -r HEAD"
        )
    )
    doc.add(tomlkit.nl())

    with tempfile.TemporaryDirectory(prefix="bsp_verify_") as tmpdir:
        # --- Kernel ---
        k_info, k_files, k_count = verify_repo(KERNEL_REPO_URL, tmpdir)
        k_tree_unchanged = k_info["tree_sha"] == KERNEL_KNOWN_TREE_SHA
        if not k_tree_unchanged:
            print(
                f"  WARNING: tree SHA changed! expected {KERNEL_KNOWN_TREE_SHA}, "
                f"got {k_info['tree_sha']}",
                file=sys.stderr,
            )
        k_rm1_dts = find_matching(k_files, KERNEL_RM1_DTS_PATTERNS)
        k_rm1_defconfig = find_matching(k_files, KERNEL_RM1_DEFCONFIG_PATTERNS)
        k_glinet_files = find_matching(k_files, GLINET_PATTERNS)
        k_rv1126_defconfigs = list_defconfigs(k_files, "arch/arm/configs/rv1126")

        add_repo_section(
            doc,
            prefix="kernel",
            label="Kernel Repository (gl-inet/kernel-4.19)",
            url=KERNEL_REPO_URL,
            bsp_commit=KERNEL_BSP_COMMIT,
            issue_url=KERNEL_ISSUE_URL,
            info=k_info,
            files=k_files,
            commit_count=k_count,
            rm1_checks=[
                (
                    "rm1_dts",
                    "search for RM1 device tree sources",
                    KERNEL_RM1_DTS_PATTERNS,
                    k_rm1_dts,
                ),
                (
                    "rm1_defconfig",
                    "search for RM1 kernel defconfig",
                    KERNEL_RM1_DEFCONFIG_PATTERNS,
                    k_rm1_defconfig,
                ),
                (
                    "glinet_files",
                    "search for GL.iNet-specific files",
                    GLINET_PATTERNS,
                    k_glinet_files,
                ),
            ],
            extra_checks=[
                (
                    "rv1126_defconfigs",
                    "git ls-tree -r HEAD",
                    "list existing RV1126 defconfigs",
                    k_rv1126_defconfigs,
                ),
                (
                    "tree_sha_unchanged",
                    "compare tree SHA against known value",
                    f"True if tree SHA matches {KERNEL_KNOWN_TREE_SHA}",
                    k_tree_unchanged,
                ),
                (
                    "diff_gist_url",
                    "external verification",
                    "diff between GL.iNet commit and BSP reference (by samueldr)",
                    KERNEL_DIFF_GIST,
                ),
            ],
        )

        doc.add(tomlkit.nl())

        # --- Buildroot ---
        b_info, b_files, b_count = verify_repo(BUILDROOT_REPO_URL, tmpdir)
        b_tree_unchanged = b_info["tree_sha"] == BUILDROOT_KNOWN_TREE_SHA
        if not b_tree_unchanged:
            print(
                f"  WARNING: tree SHA changed! expected {BUILDROOT_KNOWN_TREE_SHA}, "
                f"got {b_info['tree_sha']}",
                file=sys.stderr,
            )
        b_rm1_defconfig = find_matching(b_files, BUILDROOT_RM1_DEFCONFIG_PATTERNS)
        b_glinet_files = find_matching(b_files, GLINET_PATTERNS)
        b_rv1126_defconfigs = list_defconfigs(b_files, "configs/rockchip_rv1126")
        b_has_board_overlay = any(f.startswith("board/rockchip/") for f in b_files)

        add_repo_section(
            doc,
            prefix="buildroot",
            label="Buildroot Repository (gl-inet/buildroot-2018)",
            url=BUILDROOT_REPO_URL,
            bsp_commit=BUILDROOT_BSP_COMMIT,
            issue_url=BUILDROOT_ISSUE_URL,
            info=b_info,
            files=b_files,
            commit_count=b_count,
            rm1_checks=[
                (
                    "rm1_defconfig",
                    "search for RM1 Buildroot defconfig",
                    BUILDROOT_RM1_DEFCONFIG_PATTERNS,
                    b_rm1_defconfig,
                ),
                (
                    "glinet_files",
                    "search for GL.iNet-specific files",
                    GLINET_PATTERNS,
                    b_glinet_files,
                ),
            ],
            extra_checks=[
                (
                    "board_overlay_present",
                    "git ls-tree -r HEAD",
                    "check for board/rockchip/ overlay directory",
                    b_has_board_overlay,
                ),
                (
                    "rv1126_defconfigs",
                    "git ls-tree -r HEAD",
                    "list existing RV1126 defconfigs (none target RM1)",
                    b_rv1126_defconfigs,
                ),
                (
                    "tree_sha_unchanged",
                    "compare tree SHA against known value",
                    f"True if tree SHA matches {BUILDROOT_KNOWN_TREE_SHA}",
                    b_tree_unchanged,
                ),
            ],
        )

    return tomlkit.dumps(doc)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Verify GL.iNet BSP repositories against known Rockchip BSP commits"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write results to results/bsp_repos.toml",
    )
    args = parser.parse_args()

    toml_output = build_toml()

    if args.write:
        out_path = Path("results/bsp_repos.toml")
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(toml_output)
        print(f"Wrote {out_path}", file=sys.stderr)
    else:
        print(toml_output)


if __name__ == "__main__":
    main()
