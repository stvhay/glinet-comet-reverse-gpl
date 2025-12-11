#!/usr/bin/env bash
#
# Test analysis script for POC
#
# Outputs dummy JSON data to demonstrate the analysis framework
# Includes source attribution for automatic footnoting

set -euo pipefail

# Output JSON with test data
# Values with {name}_source and {name}_method will become TrackedValues
cat <<'EOF'
{
  "test_value": 42,
  "test_value_source": "test",
  "test_value_method": "echo 42",

  "test_hex": "0x2a",
  "test_hex_source": "test",
  "test_hex_method": "printf '0x%x' 42",

  "test_string": "Hello from test analysis",
  "test_string_source": "test",
  "test_string_method": "echo 'Hello from test analysis'",

  "discovered_offset": "0x2000",
  "discovered_offset_source": "test",
  "discovered_offset_method": "binwalk firmware.img | grep 'Kernel' | awk '{print $1}'",

  "cache_test": "This value should be cached between runs"
}
EOF
