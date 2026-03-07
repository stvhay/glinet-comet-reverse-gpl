# Ghidra Jython script: U-Boot binary analysis
# Locates command table, board init, env defaults
# @category Analysis

import json


def find_uboot_commands():
    """Locate U-Boot command table (cmd_tbl_t entries)."""
    st = currentProgram.getSymbolTable()
    commands = []
    for sym in st.getAllSymbols(True):
        name = sym.getName()
        # U-Boot commands are typically named __u_boot_cmd_* or _u_boot_list_2_cmd_*
        if "u_boot_cmd" in name or "_u_boot_list" in name:
            commands.append({
                "name": name,
                "address": str(sym.getAddress()),
            })

    # Also search for do_* functions which are command handlers
    fm = currentProgram.getFunctionManager()
    for func in fm.getFunctions(True):
        name = func.getName()
        if name.startswith("do_") and func.getBody().getNumAddresses() > 10:
            commands.append({
                "name": name,
                "address": str(func.getEntryPoint()),
                "type": "handler",
            })
    return commands


def find_board_init():
    """Find board initialization functions."""
    fm = currentProgram.getFunctionManager()
    init_funcs = []
    patterns = ["board_init", "board_early_init", "dram_init", "spl_board_init",
                "board_init_f", "board_init_r"]
    for func in fm.getFunctions(True):
        name = func.getName()
        if any(p in name for p in patterns):
            init_funcs.append({
                "name": name,
                "address": str(func.getEntryPoint()),
                "size": func.getBody().getNumAddresses(),
            })
    return init_funcs


def find_env_defaults():
    """Extract default environment variable strings."""
    from ghidra.program.model.data import StringDataInstance
    from ghidra.program.util import DefinedDataIterator

    env_vars = []
    for string_data in DefinedDataIterator.definedStrings(currentProgram):
        val = StringDataInstance.getStringDataInstance(string_data)
        s = val.getStringValue()
        if s and "=" in s and len(s) < 500:
            # Filter for likely env vars (key=value format)
            parts = s.split("=", 1)
            if parts[0].replace("_", "").isalnum() and len(parts[0]) < 40:
                env_vars.append({
                    "address": str(string_data.getAddress()),
                    "key": parts[0],
                    "value": parts[1][:200],
                })
    return env_vars


def main():
    result = {
        "binary": currentProgram.getName(),
        "type": "uboot",
        "commands": find_uboot_commands(),
        "board_init_functions": find_board_init(),
        "env_defaults": find_env_defaults(),
        "function_count": currentProgram.getFunctionManager().getFunctionCount(),
    }
    print("===GHIDRA_JSON_BEGIN===")
    print(json.dumps(result, indent=2))
    print("===GHIDRA_JSON_END===")


main()
