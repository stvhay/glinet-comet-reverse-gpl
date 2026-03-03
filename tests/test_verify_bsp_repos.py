"""Tests for scripts/verify_bsp_repos.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import tomlkit

# Add scripts directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from verify_bsp_repos import (
    BUILDROOT_KNOWN_TREE_SHA,
    KERNEL_KNOWN_TREE_SHA,
    build_toml,
    clone_shallow,
    count_commits,
    find_matching,
    get_commit_info,
    git,
    list_defconfigs,
    list_files,
    main,
    repo_name_from_url,
    verify_repo,
)


class TestGit:
    """Test git() helper function."""

    @patch("subprocess.run")
    def test_git_returns_stripped_stdout(self, mock_run: Any) -> None:
        """Test that git() returns stripped stdout."""
        mock_run.return_value = MagicMock(stdout="  hello world  \n")

        result = git("status")

        assert result == "hello world"
        mock_run.assert_called_once_with(
            ["git", "status"],
            cwd=None,
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("subprocess.run")
    def test_git_passes_multiple_args(self, mock_run: Any) -> None:
        """Test that git() passes all arguments to subprocess."""
        mock_run.return_value = MagicMock(stdout="output\n")

        git("log", "-1", "--format=%H")

        mock_run.assert_called_once_with(
            ["git", "log", "-1", "--format=%H"],
            cwd=None,
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("subprocess.run")
    def test_git_passes_cwd(self, mock_run: Any) -> None:
        """Test that git() passes cwd to subprocess."""
        mock_run.return_value = MagicMock(stdout="output\n")
        repo = Path("/tmp/repo")

        git("status", cwd=repo)

        mock_run.assert_called_once_with(
            ["git", "status"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )

    @patch("subprocess.run")
    def test_git_raises_on_failure(self, mock_run: Any) -> None:
        """Test that git() propagates subprocess errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(subprocess.CalledProcessError):
            git("status")


class TestFindMatching:
    """Test find_matching() pure function."""

    def test_finds_matching_files(self) -> None:
        """Test finding files that match glob patterns."""
        files = [
            "arch/arm/boot/dts/rv1126-rm1.dts",
            "arch/arm/boot/dts/rv1126-evb.dts",
            "arch/arm/boot/dts/rv1126-glrm1.dts",
        ]
        patterns = ["arch/arm/boot/dts/*rm1*", "arch/arm/boot/dts/*glrm1*"]

        result = find_matching(files, patterns)

        assert result == [
            "arch/arm/boot/dts/rv1126-glrm1.dts",
            "arch/arm/boot/dts/rv1126-rm1.dts",
        ]

    def test_returns_empty_on_no_match(self) -> None:
        """Test that no matches returns empty list."""
        files = ["arch/arm/boot/dts/rv1126-evb.dts"]
        patterns = ["arch/arm/boot/dts/*rm1*"]

        result = find_matching(files, patterns)

        assert result == []

    def test_case_insensitive_matching(self) -> None:
        """Test that matching is case-insensitive (lowercases filename)."""
        files = ["configs/GL-INET-defconfig"]
        patterns = ["*gl-inet*"]

        result = find_matching(files, patterns)

        assert result == ["configs/GL-INET-defconfig"]

    def test_returns_sorted_results(self) -> None:
        """Test that results are sorted."""
        files = ["c.txt", "a.txt", "b.txt"]
        patterns = ["*.txt"]

        result = find_matching(files, patterns)

        assert result == ["a.txt", "b.txt", "c.txt"]

    def test_empty_files_list(self) -> None:
        """Test with empty files list."""
        result = find_matching([], ["*.txt"])

        assert result == []

    def test_empty_patterns_list(self) -> None:
        """Test with empty patterns list."""
        result = find_matching(["a.txt"], [])

        assert result == []


class TestListDefconfigs:
    """Test list_defconfigs() pure function."""

    def test_finds_defconfigs_with_prefix(self) -> None:
        """Test finding defconfig files under a prefix."""
        files = [
            "arch/arm/configs/rv1126_defconfig",
            "arch/arm/configs/rv1126_robot_defconfig",
            "arch/arm/configs/rv1109_defconfig",
            "arch/arm/configs/other_config",
        ]

        result = list_defconfigs(files, "arch/arm/configs/rv1126")

        assert result == [
            "arch/arm/configs/rv1126_defconfig",
            "arch/arm/configs/rv1126_robot_defconfig",
        ]

    def test_returns_empty_on_no_match(self) -> None:
        """Test that no matches returns empty list."""
        files = ["arch/arm/configs/other_defconfig"]

        result = list_defconfigs(files, "arch/arm/configs/rv1126")

        assert result == []

    def test_requires_defconfig_in_name(self) -> None:
        """Test that files must contain 'defconfig' in name."""
        files = [
            "arch/arm/configs/rv1126_defconfig",
            "arch/arm/configs/rv1126_config",
        ]

        result = list_defconfigs(files, "arch/arm/configs/rv1126")

        assert result == ["arch/arm/configs/rv1126_defconfig"]

    def test_returns_sorted_results(self) -> None:
        """Test that results are sorted."""
        files = [
            "configs/rockchip_rv1126_b_defconfig",
            "configs/rockchip_rv1126_a_defconfig",
        ]

        result = list_defconfigs(files, "configs/rockchip_rv1126")

        assert result == [
            "configs/rockchip_rv1126_a_defconfig",
            "configs/rockchip_rv1126_b_defconfig",
        ]


class TestGetCommitInfo:
    """Test get_commit_info() function."""

    @patch("verify_bsp_repos.git")
    def test_parses_commit_info(self, mock_git: Any) -> None:
        """Test parsing git log output into commit info dict."""
        mock_git.return_value = (
            "abc123def456\n"
            "John Doe\n"
            "john@example.com\n"
            "2026-01-15T10:00:00+08:00\n"
            "first commit\n"
            "tree789sha"
        )

        result = get_commit_info(Path("/tmp/repo"))

        assert result == {
            "commit": "abc123def456",
            "author_name": "John Doe",
            "author_email": "john@example.com",
            "author_date": "2026-01-15T10:00:00+08:00",
            "subject": "first commit",
            "tree_sha": "tree789sha",
        }
        mock_git.assert_called_once_with(
            "log", "-1", "--format=%H%n%an%n%ae%n%aI%n%s%n%T", cwd=Path("/tmp/repo")
        )


class TestCountCommits:
    """Test count_commits() function."""

    @patch("verify_bsp_repos.git")
    def test_returns_commit_count(self, mock_git: Any) -> None:
        """Test parsing rev-list count output."""
        mock_git.return_value = "1"

        result = count_commits(Path("/tmp/repo"))

        assert result == 1
        mock_git.assert_called_once_with("rev-list", "--count", "HEAD", cwd=Path("/tmp/repo"))

    @patch("verify_bsp_repos.git")
    def test_returns_multiple_commits(self, mock_git: Any) -> None:
        """Test with multiple commits."""
        mock_git.return_value = "42"

        result = count_commits(Path("/tmp/repo"))

        assert result == 42


class TestListFiles:
    """Test list_files() function."""

    @patch("verify_bsp_repos.git")
    def test_parses_file_list(self, mock_git: Any) -> None:
        """Test parsing ls-tree output into file list."""
        mock_git.return_value = "file1.c\nfile2.h\ndir/file3.txt"

        result = list_files(Path("/tmp/repo"))

        assert result == ["file1.c", "file2.h", "dir/file3.txt"]
        mock_git.assert_called_once_with(
            "ls-tree", "-r", "--name-only", "HEAD", cwd=Path("/tmp/repo")
        )

    @patch("verify_bsp_repos.git")
    def test_returns_empty_for_empty_output(self, mock_git: Any) -> None:
        """Test that empty output returns empty list."""
        mock_git.return_value = ""

        result = list_files(Path("/tmp/repo"))

        assert result == []


class TestCloneShallow:
    """Test clone_shallow() function."""

    @patch("verify_bsp_repos.git")
    def test_clone_flags(self, mock_git: Any) -> None:
        """Test that clone_shallow passes correct flags."""
        dest = Path("/tmp/dest")

        clone_shallow("https://github.com/test/repo.git", dest)

        mock_git.assert_called_once_with(
            "clone",
            "--depth=1",
            "--no-checkout",
            "--filter=blob:none",
            "https://github.com/test/repo.git",
            str(dest),
        )


class TestVerifyRepo:
    """Test verify_repo() function."""

    @patch("verify_bsp_repos.count_commits")
    @patch("verify_bsp_repos.list_files")
    @patch("verify_bsp_repos.get_commit_info")
    @patch("verify_bsp_repos.clone_shallow")
    def test_returns_info_files_count(
        self,
        mock_clone: Any,
        mock_info: Any,
        mock_files: Any,
        mock_count: Any,
        tmp_path: Path,
    ) -> None:
        """Test verify_repo returns (info, files, count) tuple."""
        mock_info.return_value = {
            "commit": "abc123",
            "author_name": "Test",
            "author_email": "test@example.com",
            "author_date": "2026-01-01T00:00:00Z",
            "subject": "first commit",
            "tree_sha": "tree123",
        }
        mock_files.return_value = ["file1.c", "file2.h"]
        mock_count.return_value = 1

        info, files, count = verify_repo("https://github.com/test/repo.git", str(tmp_path))

        assert info["commit"] == "abc123"
        assert files == ["file1.c", "file2.h"]
        assert count == 1
        mock_clone.assert_called_once()

    @patch("verify_bsp_repos.count_commits")
    @patch("verify_bsp_repos.list_files")
    @patch("verify_bsp_repos.get_commit_info")
    @patch("verify_bsp_repos.clone_shallow")
    def test_repo_name_from_url(
        self,
        mock_clone: Any,
        mock_info: Any,
        mock_files: Any,
        mock_count: Any,
        tmp_path: Path,
    ) -> None:
        """Test that repo name is derived from URL."""
        mock_info.return_value = {
            "commit": "abc",
            "author_name": "Test",
            "author_email": "t@e.com",
            "author_date": "2026-01-01",
            "subject": "test",
            "tree_sha": "tree",
        }
        mock_files.return_value = []
        mock_count.return_value = 1

        verify_repo("https://github.com/gl-inet/kernel-4.19.git", str(tmp_path))

        # clone_shallow should be called with dest = tmpdir / "kernel-4.19"
        clone_dest = mock_clone.call_args[0][1]
        assert clone_dest == tmp_path / "kernel-4.19"


class TestRepoNameFromUrl:
    """Test repo_name_from_url() function."""

    def test_strips_git_suffix(self) -> None:
        """Test that .git suffix is stripped."""
        assert repo_name_from_url("https://github.com/gl-inet/kernel-4.19.git") == "kernel-4.19"

    def test_no_git_suffix(self) -> None:
        """Test URL without .git suffix."""
        assert repo_name_from_url("https://github.com/gl-inet/buildroot-2018") == "buildroot-2018"

    def test_trailing_slash(self) -> None:
        """Test URL with trailing slash."""
        assert repo_name_from_url("https://github.com/gl-inet/kernel-4.19.git/") == "kernel-4.19"

    def test_url_with_query_params(self) -> None:
        """Test URL with query parameters."""
        assert repo_name_from_url("https://github.com/gl-inet/repo.git?ref=main") == "repo"


class TestBuildToml:
    """Test build_toml() end-to-end function."""

    @patch("verify_bsp_repos.verify_repo")
    def test_produces_valid_toml(self, mock_verify: Any) -> None:
        """Test that build_toml produces valid TOML."""
        # Mock both kernel and buildroot verify_repo calls
        kernel_info = {
            "commit": "fc316e95",
            "author_name": "xiaojiang2017",
            "author_email": "xj@example.com",
            "author_date": "2026-01-15T10:00:00+08:00",
            "subject": "first commit",
            "tree_sha": "ktree123",
        }
        kernel_files = [
            "arch/arm/configs/rv1126_defconfig",
            "arch/arm/configs/rv1126_robot_defconfig",
            "Makefile",
        ]

        buildroot_info = {
            "commit": "4a4f065a",
            "author_name": "xiaojiang2017",
            "author_email": "xj@example.com",
            "author_date": "2026-01-15T10:00:00+08:00",
            "subject": "first commit",
            "tree_sha": "btree456",
        }
        buildroot_files = [
            "configs/rockchip_rv1126_defconfig",
            "Makefile",
        ]

        mock_verify.side_effect = [
            (kernel_info, kernel_files, 1),
            (buildroot_info, buildroot_files, 1),
        ]

        result = build_toml()

        # Should be valid TOML
        parsed = tomlkit.loads(result)
        assert parsed["kernel_head_commit"] == "fc316e95"
        assert parsed["kernel_is_squashed_import"] is True
        assert parsed["kernel_rm1_dts_found"] is False
        assert parsed["kernel_rm1_dts_files"] == []
        assert parsed["kernel_rm1_defconfig_found"] is False
        assert parsed["kernel_glinet_files_found"] is False
        assert parsed["kernel_tree_sha_unchanged"] is False  # test SHA != known SHA
        assert parsed["kernel_total_files"] == 3

        assert parsed["buildroot_head_commit"] == "4a4f065a"
        assert parsed["buildroot_is_squashed_import"] is True
        assert parsed["buildroot_rm1_defconfig_found"] is False
        assert parsed["buildroot_glinet_files_found"] is False
        assert parsed["buildroot_tree_sha_unchanged"] is False  # test SHA != known SHA
        assert parsed["buildroot_total_files"] == 2

    @patch("verify_bsp_repos.verify_repo")
    def test_detects_rm1_files(self, mock_verify: Any) -> None:
        """Test that build_toml detects RM1-specific files when present."""
        kernel_info = {
            "commit": "abc123",
            "author_name": "Test",
            "author_email": "t@e.com",
            "author_date": "2026-01-01",
            "subject": "test",
            "tree_sha": "tree",
        }
        kernel_files = [
            "arch/arm/boot/dts/rv1126-rm1.dts",
            "arch/arm/configs/rv1126_rm1_defconfig",
            "arch/arm/configs/rv1126_defconfig",
        ]

        buildroot_info = dict(kernel_info)
        buildroot_info["commit"] = "def456"
        buildroot_files = [
            "configs/rockchip_rv1126_rm1_defconfig",
        ]

        mock_verify.side_effect = [
            (kernel_info, kernel_files, 1),
            (buildroot_info, buildroot_files, 1),
        ]

        result = build_toml()
        parsed = tomlkit.loads(result)

        assert parsed["kernel_rm1_dts_found"] is True
        assert "rv1126-rm1.dts" in parsed["kernel_rm1_dts_files"][0]
        assert parsed["kernel_rm1_defconfig_found"] is True
        assert parsed["buildroot_rm1_defconfig_found"] is True

    @patch("verify_bsp_repos.verify_repo")
    def test_tree_sha_unchanged_when_matching(self, mock_verify: Any) -> None:
        """Test that tree_sha_unchanged is True when tree SHA matches known value."""
        kernel_info = {
            "commit": "fc316e95",
            "author_name": "xiaojiang2017",
            "author_email": "xj@example.com",
            "author_date": "2026-01-15T10:00:00+08:00",
            "subject": "first commit",
            "tree_sha": KERNEL_KNOWN_TREE_SHA,
        }
        buildroot_info = {
            "commit": "4a4f065a",
            "author_name": "xiaojiang2017",
            "author_email": "xj@example.com",
            "author_date": "2026-01-15T10:00:00+08:00",
            "subject": "first commit",
            "tree_sha": BUILDROOT_KNOWN_TREE_SHA,
        }

        mock_verify.side_effect = [
            (kernel_info, [], 1),
            (buildroot_info, [], 1),
        ]

        result = build_toml()
        parsed = tomlkit.loads(result)

        assert parsed["kernel_tree_sha_unchanged"] is True
        assert parsed["buildroot_tree_sha_unchanged"] is True

    @patch("verify_bsp_repos.verify_repo")
    def test_not_squashed_when_multiple_commits(self, mock_verify: Any) -> None:
        """Test that is_squashed_import is False when commit_count > 1."""
        info = {
            "commit": "abc",
            "author_name": "Test",
            "author_email": "t@e.com",
            "author_date": "2026-01-01",
            "subject": "test",
            "tree_sha": "tree",
        }

        mock_verify.side_effect = [
            (info, [], 5),
            (info, [], 3),
        ]

        result = build_toml()
        parsed = tomlkit.loads(result)

        assert parsed["kernel_is_squashed_import"] is False
        assert parsed["buildroot_is_squashed_import"] is False


class TestMain:
    """Test main() entry point."""

    @patch("verify_bsp_repos.build_toml")
    @patch("sys.argv", ["verify_bsp_repos.py"])
    def test_default_prints_to_stdout(
        self, mock_build: Any, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that main() prints TOML to stdout by default."""
        mock_build.return_value = 'kernel_head_commit = "abc123"\n'

        main()

        captured = capsys.readouterr()
        assert 'kernel_head_commit = "abc123"' in captured.out

    @patch("verify_bsp_repos.build_toml")
    @patch("sys.argv", ["verify_bsp_repos.py", "--write"])
    def test_write_flag_creates_file(
        self, mock_build: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that --write flag writes to results/bsp_repos.toml."""
        mock_build.return_value = 'kernel_head_commit = "abc123"\n'

        monkeypatch.chdir(tmp_path)
        main()

        out_path = tmp_path / "results" / "bsp_repos.toml"
        assert out_path.exists()
        assert 'kernel_head_commit = "abc123"' in out_path.read_text()
