#!/usr/bin/env bash
# Orchestrator for Ghidra headless analysis of firmware binaries.
# Usage: ./scripts/ghidra/run_ghidra_analysis.sh <extracted_firmware_dir>
#
# Expects extracted firmware with rootfs containing .ko files and U-Boot binary.
# Outputs JSON files to results/ghidra/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RESULTS_DIR="${PROJECT_ROOT}/results/ghidra"
GHIDRA_PROJECT_DIR=""

usage() {
    echo "Usage: $0 <extracted_firmware_dir>"
    echo ""
    echo "Arguments:"
    echo "  extracted_firmware_dir  Path to extracted firmware (contains rootfs, u-boot, etc.)"
    exit 1
}

cleanup() {
    if [[ -n "${GHIDRA_PROJECT_DIR}" && -d "${GHIDRA_PROJECT_DIR}" ]]; then
        echo "[INFO] Cleaning up Ghidra project directory: ${GHIDRA_PROJECT_DIR}"
        rm -rf "${GHIDRA_PROJECT_DIR}"
    fi
}
trap cleanup EXIT

extract_json() {
    # Extract JSON between markers from Ghidra output
    local output="$1"
    echo "${output}" | sed -n '/===GHIDRA_JSON_BEGIN===/,/===GHIDRA_JSON_END===/p' \
        | grep -v '===GHIDRA_JSON' || true
}

analyze_binary() {
    local binary_path="$1"
    local script_name="$2"
    local output_name="$3"
    local binary_name
    binary_name="$(basename "${binary_path}")"

    echo "[INFO] Analyzing ${binary_name} with ${script_name}..."

    local ghidra_output
    ghidra_output="$(analyzeHeadless \
        "${GHIDRA_PROJECT_DIR}" "analysis_${output_name}" \
        -import "${binary_path}" \
        -processor ARM:LE:32:v7 \
        -postScript "${SCRIPT_DIR}/${script_name}" \
        -deleteProject \
        -noanalysis \
        -scriptlog "${RESULTS_DIR}/${output_name}_script.log" \
        2>&1)" || {
        echo "[WARN] Ghidra analysis failed for ${binary_name}, continuing..."
        return 1
    }

    local json_data
    json_data="$(extract_json "${ghidra_output}")"

    if [[ -n "${json_data}" ]]; then
        echo "${json_data}" > "${RESULTS_DIR}/${output_name}.json"
        echo "[OK] Wrote ${RESULTS_DIR}/${output_name}.json"
    else
        echo "[WARN] No JSON output from ${script_name} for ${binary_name}"
        return 1
    fi
}

main() {
    if [[ $# -lt 1 ]]; then
        usage
    fi

    local firmware_dir="$1"

    if [[ ! -d "${firmware_dir}" ]]; then
        echo "[ERROR] Directory not found: ${firmware_dir}"
        exit 1
    fi

    # Verify analyzeHeadless is available
    if ! command -v analyzeHeadless &>/dev/null; then
        echo "[ERROR] analyzeHeadless not found. Run within 'nix develop' shell."
        exit 1
    fi

    # Set up output and temp directories
    mkdir -p "${RESULTS_DIR}"
    GHIDRA_PROJECT_DIR="$(mktemp -d /tmp/ghidra_project_XXXXXX)"
    echo "[INFO] Ghidra project dir: ${GHIDRA_PROJECT_DIR}"
    echo "[INFO] Results dir: ${RESULTS_DIR}"

    local analyzed=0
    local failed=0

    # Find and analyze kernel modules
    echo "[INFO] Searching for kernel modules in ${firmware_dir}..."
    while IFS= read -r -d '' ko_file; do
        local ko_name
        ko_name="$(basename "${ko_file}" .ko)"
        if analyze_binary "${ko_file}" "analyze_kernel_module.py" "ko_${ko_name}"; then
            # Also run generic analysis
            analyze_binary "${ko_file}" "analyze_binary.py" "generic_${ko_name}" || true
            # Run struct reconstruction
            analyze_binary "${ko_file}" "reconstruct_structs.py" "structs_${ko_name}" || true
            analyzed=$((analyzed + 1))
        else
            failed=$((failed + 1))
        fi
    done < <(find "${firmware_dir}" -name "*.ko" -print0 2>/dev/null)

    # Find and analyze U-Boot binary
    # U-Boot is typically extracted by binwalk as a raw binary
    local uboot_bin=""
    for candidate in "${firmware_dir}/uboot.bin" "${firmware_dir}/u-boot.bin" \
                     "${firmware_dir}/u-boot" "${firmware_dir}/"*uboot*; do
        if [[ -f "${candidate}" ]]; then
            uboot_bin="${candidate}"
            break
        fi
    done

    if [[ -n "${uboot_bin}" ]]; then
        echo "[INFO] Found U-Boot binary: ${uboot_bin}"
        if analyze_binary "${uboot_bin}" "analyze_uboot_binary.py" "uboot"; then
            analyze_binary "${uboot_bin}" "analyze_binary.py" "generic_uboot" || true
            analyze_binary "${uboot_bin}" "reconstruct_structs.py" "structs_uboot" || true
            analyzed=$((analyzed + 1))
        else
            failed=$((failed + 1))
        fi
    else
        echo "[WARN] No U-Boot binary found in ${firmware_dir}"
    fi

    # Summary
    echo ""
    echo "[INFO] Ghidra analysis complete."
    echo "[INFO] Analyzed: ${analyzed} binaries"
    echo "[INFO] Failed: ${failed} binaries"
    echo "[INFO] Results: ${RESULTS_DIR}/"
    ls -la "${RESULTS_DIR}/"*.json 2>/dev/null || echo "[WARN] No JSON output files."
}

main "$@"
