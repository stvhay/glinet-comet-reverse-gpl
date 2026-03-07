#!/usr/bin/env bash
# Fetch upstream kernel and U-Boot source trees for cross-referencing.
#
# Usage: ./scripts/fetch_upstream.sh [--cache-dir DIR]
#
# Clones vanilla kernel 4.19.111 and U-Boot 2017.09 to a cache directory.
# Idempotent: skips if repos exist at correct tags.
#
# Default cache: ~/.cache/glinet-comet-re/upstream/

set -euo pipefail

KERNEL_REPO="https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git"
KERNEL_TAG="v4.19.111"
UBOOT_REPO="https://github.com/u-boot/u-boot.git"
UBOOT_TAG="v2017.09"

DEFAULT_CACHE_DIR="${HOME}/.cache/glinet-comet-re/upstream"

usage() {
    echo "Usage: $0 [--cache-dir DIR]"
    echo ""
    echo "Fetches upstream kernel ${KERNEL_TAG} and U-Boot ${UBOOT_TAG} source."
    echo ""
    echo "Options:"
    echo "  --cache-dir DIR   Cache directory (default: ${DEFAULT_CACHE_DIR})"
    echo "  --help            Show this help"
    exit 0
}

clone_at_tag() {
    local repo="$1"
    local tag="$2"
    local target_dir="$3"
    local name
    name="$(basename "${target_dir}")"

    if [[ -d "${target_dir}/.git" ]]; then
        # Check if at correct tag
        local current_tag
        current_tag="$(git -C "${target_dir}" describe --tags --exact-match 2>/dev/null || echo "")"
        if [[ "${current_tag}" == "${tag}" ]]; then
            echo "[OK] ${name} already at ${tag}, skipping"
            return 0
        fi

        echo "[INFO] ${name} exists but not at ${tag} (currently: ${current_tag:-unknown})"
        echo "[INFO] Checking out ${tag}..."
        git -C "${target_dir}" fetch --tags --depth 1 origin "refs/tags/${tag}:refs/tags/${tag}" 2>/dev/null || \
            git -C "${target_dir}" fetch --tags origin
        git -C "${target_dir}" checkout "${tag}" --quiet
        echo "[OK] ${name} checked out at ${tag}"
        return 0
    fi

    echo "[INFO] Cloning ${name} at ${tag} (shallow clone)..."
    git clone --depth 1 --branch "${tag}" "${repo}" "${target_dir}"
    echo "[OK] ${name} cloned at ${tag}"
}

main() {
    local cache_dir="${DEFAULT_CACHE_DIR}"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --cache-dir)
                cache_dir="$2"
                shift 2
                ;;
            --help)
                usage
                ;;
            *)
                echo "[ERROR] Unknown option: $1"
                usage
                ;;
        esac
    done

    mkdir -p "${cache_dir}"
    echo "[INFO] Cache directory: ${cache_dir}"

    clone_at_tag "${KERNEL_REPO}" "${KERNEL_TAG}" "${cache_dir}/linux"
    clone_at_tag "${UBOOT_REPO}" "${UBOOT_TAG}" "${cache_dir}/u-boot"

    echo ""
    echo "[INFO] Upstream sources ready:"
    echo "  Kernel: ${cache_dir}/linux (${KERNEL_TAG})"
    echo "  U-Boot: ${cache_dir}/u-boot (${UBOOT_TAG})"
}

main "$@"
