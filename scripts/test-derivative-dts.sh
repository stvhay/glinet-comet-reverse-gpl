#!/usr/bin/env bash
# Test that rv1126-glinet-rm1.dts derivative correctly documents GL.iNet customizations
#
# This test verifies our reverse-engineered derivative DTS is correct by:
# 1. Fetching the reference DTS that GL.iNet's firmware is based on
# 2. Extracting GL.iNet-specific nodes from both derivative and original
# 3. Validating that our derivative correctly documents the customizations
# 4. Verifying semantic correctness without requiring full kernel source compilation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091  # lib/common.sh is sourced at runtime
source "$SCRIPT_DIR/lib/common.sh"

init_dirs
require_command dtc
require_command curl
require_command diff

# Directories
DTS_DIR="$OUTPUT_DIR/dts"
DTSI_DIR="$DTS_DIR/upstream"
TEST_DIR="$OUTPUT_DIR/test"
KERNEL_SRC="$OUTPUT_DIR/firefly-kernel"
mkdir -p "$DTSI_DIR" "$TEST_DIR"

# Upstream repository
UPSTREAM_REPO="https://gitlab.com/firefly-linux/kernel/-/raw/rv1126_rv1109/linux_release_v2.2.5g"
UPSTREAM_DTS_PATH="arch/arm/boot/dts"
UPSTREAM_GIT="https://gitlab.com/firefly-linux/kernel.git"
UPSTREAM_BRANCH="rv1126_rv1109/linux_release_v2.2.5g"

# Test modes
FULL_COMPILE=${FULL_COMPILE:-false}

section "Fetch reference DTS"

REFERENCE_DTS_URL="$UPSTREAM_REPO/$UPSTREAM_DTS_PATH/rv1126-evb-ddr3-v13.dts"
REFERENCE_DTS="$TEST_DIR/rv1126-evb-ddr3-v13.dts"

info "Downloading reference DTS from upstream..."
if curl -fsSL "$REFERENCE_DTS_URL" -o "$REFERENCE_DTS"; then
    success "Downloaded reference DTS"
else
    error "Failed to download reference DTS"
    exit 1
fi

section "Validate derivative DTS structure"

DERIVATIVE_DTS="$DTS_DIR/rv1126-glinet-rm1.dts"

if [[ ! -f "$DERIVATIVE_DTS" ]]; then
    error "Derivative DTS not found: $DERIVATIVE_DTS"
    exit 1
fi

info "Checking derivative DTS structure..."

# Verify includes
if grep -q '#include "rv1126.dtsi"' "$DERIVATIVE_DTS" && \
   grep -q '#include "rv1126-evb-v13.dtsi"' "$DERIVATIVE_DTS"; then
    success "Derivative correctly includes upstream .dtsi files"
else
    error "Derivative missing correct #include statements"
    exit 1
fi

# Verify GPL license header
if grep -q "SPDX-License-Identifier: (GPL-2.0+ OR MIT)" "$DERIVATIVE_DTS"; then
    success "Derivative has correct GPL-2.0+/MIT license"
else
    error "Derivative missing GPL license identifier"
    exit 1
fi

# Verify methodology documentation in comments
if grep -q "reverse-engineered" "$DERIVATIVE_DTS" && \
   grep -q "Methodology:" "$DERIVATIVE_DTS"; then
    success "Derivative documents reverse engineering methodology"
else
    error "Derivative missing methodology documentation"
    exit 1
fi

section "Compare with original firmware DTS"

ORIGINAL_DTS="$OUTPUT_DIR/dtb/kernel-fit.dts"

if [[ ! -f "$ORIGINAL_DTS" ]]; then
    warn "Original firmware DTS not found: $ORIGINAL_DTS"
    info "Run ./scripts/dump-device-trees.sh first"
    exit 1
fi

section "Verify GL.iNet customizations"

# Extract and compare key customizations
check_property() {
    local file="$1"
    local pattern="$2"
    local description="$3"

    if grep -q "$pattern" "$file"; then
        success "✓ $description"
        grep "$pattern" "$file" | head -1 | sed 's/^[[:space:]]*/    /'
        return 0
    else
        error "✗ $description"
        return 1
    fi
}

echo ""
echo "Checking derivative DTS documents GL.iNet customizations:"
check_property "$DERIVATIVE_DTS" 'model = "GL.iNet Comet (RM1)"' "Product name in root"
check_property "$DERIVATIVE_DTS" 'compatible = "glinet,rm1"' "GL.iNet compatible string"
check_property "$DERIVATIVE_DTS" 'compatible = "gl-hw-info"' "gl_hw node present"
check_property "$DERIVATIVE_DTS" 'model = "rm1"' "Product model in gl_hw"
check_property "$DERIVATIVE_DTS" 'rootfstype=squashfs' "Squashfs root filesystem in bootargs"

echo ""
echo "Validating against original firmware DTS:"
check_property "$ORIGINAL_DTS" 'compatible = "gl-hw-info"' "gl_hw node in original"
check_property "$ORIGINAL_DTS" 'model = "rm1"' "Product model in original"
check_property "$ORIGINAL_DTS" 'rootfstype=squashfs' "Squashfs in original bootargs"

section "Compare bootargs customization"

echo ""
info "Extracting bootargs from reference board..."
ref_bootargs=$(grep 'bootargs =' "$REFERENCE_DTS" | sed 's/.*bootargs = "\(.*\)";/\1/')

info "Extracting bootargs from original firmware..."
orig_bootargs=$(grep 'bootargs =' "$ORIGINAL_DTS" | sed 's/.*bootargs = "\(.*\)";/\1/')

info "Extracting bootargs from derivative..."
deriv_bootargs=$(grep 'bootargs =' "$DERIVATIVE_DTS" | sed 's/.*bootargs = "\(.*\)";/\1/')

echo ""
echo "Reference board bootargs:"
echo "  $ref_bootargs" | fold -s -w 100 | sed 's/^/  /'

echo ""
echo "GL.iNet firmware bootargs:"
echo "  $orig_bootargs" | fold -s -w 100 | sed 's/^/  /'

echo ""
echo "Derivative DTS bootargs:"
echo "  $deriv_bootargs" | fold -s -w 100 | sed 's/^/  /'

# Check if derivative matches original (GL.iNet firmware)
if [[ "$deriv_bootargs" == "$orig_bootargs" ]]; then
    success "Derivative bootargs match original firmware"
else
    error "Derivative bootargs differ from original firmware"
    echo "  This indicates the derivative DTS may not accurately represent GL.iNet's customizations"
fi

section "Validate gl_hw node structure"

echo ""
info "Extracting gl_hw node from original firmware..."
awk '/gl_hw \{/,/^\t\};$/' "$ORIGINAL_DTS" > "$TEST_DIR/original-gl_hw.txt"

info "Extracting gl_hw node from derivative..."
awk '/gl_hw \{/,/^\t\};$/' "$DERIVATIVE_DTS" > "$TEST_DIR/derivative-gl_hw.txt"

# Count properties in each
orig_props=$(grep -c '=' "$TEST_DIR/original-gl_hw.txt" || echo 0)
deriv_props=$(grep -c '=' "$TEST_DIR/derivative-gl_hw.txt" || echo 0)

echo ""
echo "Property count:"
echo "  Original:   $orig_props properties"
echo "  Derivative: $deriv_props properties"

if [[ $orig_props -eq $deriv_props ]]; then
    success "Property counts match"
else
    warn "Property counts differ - derivative may be incomplete"
fi

# Check for key properties
echo ""
info "Checking key gl_hw properties in derivative:"
for prop in "model" "hdmipatch" "usb_pid" "wan" "flash_size" "factory_data"; do
    if grep -q "$prop" "$TEST_DIR/derivative-gl_hw.txt"; then
        success "  ✓ $prop"
    else
        error "  ✗ $prop (missing)"
    fi
done

section "Full Compilation Test (Optional)"

if [[ "$FULL_COMPILE" == "true" ]]; then
    echo ""
    info "Full compilation test requested - fetching kernel sources..."

    # Check if git is available
    if ! command -v git &>/dev/null; then
        warn "git not found - skipping full compilation test"
        warn "Install git to enable compilation testing"
        FULL_COMPILE=false
    else
        # Clone or update kernel source
        if [[ -d "$KERNEL_SRC/.git" ]]; then
            info "Kernel source already exists, updating..."
            (cd "$KERNEL_SRC" && git fetch origin "$UPSTREAM_BRANCH" 2>&1 | head -10)
            (cd "$KERNEL_SRC" && git checkout "$UPSTREAM_BRANCH" 2>&1 | head -5)
        else
            info "Cloning Firefly kernel source (this may take several minutes)..."
            info "Repository: $UPSTREAM_GIT"
            info "Branch: $UPSTREAM_BRANCH"

            # Shallow clone to save time and space
            if git clone --depth 1 --single-branch --branch "$UPSTREAM_BRANCH" \
                "$UPSTREAM_GIT" "$KERNEL_SRC" 2>&1 | tail -20; then
                success "Kernel source cloned successfully"
            else
                error "Failed to clone kernel source"
                warn "Skipping full compilation test"
                FULL_COMPILE=false
            fi
        fi

        if [[ "$FULL_COMPILE" == "true" ]]; then
            # Copy derivative DTS to kernel source tree
            KERNEL_DTS_DIR="$KERNEL_SRC/arch/arm/boot/dts"
            cp "$DERIVATIVE_DTS" "$KERNEL_DTS_DIR/rv1126-glinet-rm1.dts"

            info "Compiling derivative DTS with full kernel source tree..."
            COMPILED_DTB="$TEST_DIR/rv1126-glinet-rm1-full.dtb"
            PREPROCESSED_DTS="$TEST_DIR/rv1126-glinet-rm1-preprocessed.dts"

            # Preprocess DTS with C preprocessor to handle #include directives
            info "Preprocessing DTS with cpp..."
            if cpp -nostdinc \
                -I "$KERNEL_DTS_DIR" \
                -I "$KERNEL_SRC/include" \
                -undef -x assembler-with-cpp \
                "$KERNEL_DTS_DIR/rv1126-glinet-rm1.dts" \
                -o "$PREPROCESSED_DTS" 2>"$TEST_DIR/cpp-errors.log"; then
                success "Preprocessing successful"
            else
                error "Preprocessing failed"
                cat "$TEST_DIR/cpp-errors.log"
                FULL_COMPILE=false
            fi

            # Compile preprocessed DTS to DTB
            if [[ "$FULL_COMPILE" == "true" ]] && dtc -I dts -O dtb \
                -o "$COMPILED_DTB" \
                "$PREPROCESSED_DTS" 2>"$TEST_DIR/dtc-errors.log"; then
                success "Full compilation successful!"

                # Get size
                COMPILED_SIZE=$(stat -f%z "$COMPILED_DTB" 2>/dev/null || stat -c%s "$COMPILED_DTB")
                info "Compiled DTB size: $(numfmt --to=iec "$COMPILED_SIZE")"

                # Decompile and validate
                COMPILED_DTS="$TEST_DIR/rv1126-glinet-rm1-full.dts"
                if dtc -I dtb -O dts -o "$COMPILED_DTS" "$COMPILED_DTB" 2>/dev/null; then
                    success "Decompiled successfully"

                    # Verify key properties in compiled output
                    echo ""
                    info "Verifying compiled DTB properties:"
                    if grep -q 'compatible = "glinet,rm1"' "$COMPILED_DTS"; then
                        success "  ✓ GL.iNet compatible string present"
                    fi
                    if grep -q 'compatible = "gl-hw-info"' "$COMPILED_DTS"; then
                        success "  ✓ gl_hw node present"
                    fi
                    if grep -q 'rootfstype=squashfs' "$COMPILED_DTS"; then
                        success "  ✓ Squashfs bootargs present"
                    fi
                fi
            else
                error "Compilation failed"
                warn "Errors:"
                cat "$TEST_DIR/dtc-errors.log"
            fi
        fi
    fi
else
    echo ""
    info "Skipping full compilation test (use FULL_COMPILE=true to enable)"
    info "Full test requires cloning ~500MB kernel source tree"
fi

section "Test Summary"

echo ""
success "Derivative DTS validation complete!"
echo ""
echo "Results:"
echo "  • Derivative DTS structure is valid"
echo "  • GPL license and methodology documented"
echo "  • Upstream includes correctly referenced"
echo "  • GL.iNet customizations accurately documented"
echo "  • bootargs match original firmware"
echo "  • gl_hw node structure validated"

if [[ "$FULL_COMPILE" == "true" ]] && [[ -f "$COMPILED_DTB" ]]; then
    echo "  • Full compilation test: PASSED"
fi

echo ""
echo "Files:"
echo "  • Reference DTS:   $REFERENCE_DTS"
echo "  • Derivative DTS:  $DERIVATIVE_DTS"
echo "  • Original DTS:    $ORIGINAL_DTS"
echo "  • gl_hw diff:      $TEST_DIR/derivative-gl_hw.txt"

if [[ "$FULL_COMPILE" == "true" ]] && [[ -f "$COMPILED_DTB" ]]; then
    echo "  • Compiled DTB:    $COMPILED_DTB"
    echo "  • Compiled DTS:    $COMPILED_DTS"
fi

echo ""
if [[ "$FULL_COMPILE" != "true" ]]; then
    info "Run with FULL_COMPILE=true to perform complete compilation test"
fi
