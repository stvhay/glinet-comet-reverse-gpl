# Ghidra Jython script: Kernel module (.ko) analysis
# Finds module_init/exit, EXPORT_SYMBOL markers, file_operations structs
# @category Analysis

import json
import re


def find_module_init_exit():
    """Find module_init and module_exit functions."""
    fm = currentProgram.getFunctionManager()
    results = {"init": None, "exit": None}
    for func in fm.getFunctions(True):
        name = func.getName()
        if "init_module" in name or "module_init" in name:
            results["init"] = {"name": name, "address": str(func.getEntryPoint())}
        if "cleanup_module" in name or "module_exit" in name:
            results["exit"] = {"name": name, "address": str(func.getEntryPoint())}
    return results


def find_exported_symbols():
    """Find EXPORT_SYMBOL and EXPORT_SYMBOL_GPL markers."""
    from ghidra.program.model.data import StringDataInstance
    from ghidra.program.util import DefinedDataIterator

    exported = []
    for string_data in DefinedDataIterator.definedStrings(currentProgram):
        val = StringDataInstance.getStringDataInstance(string_data)
        s = val.getStringValue()
        if not s:
            continue
        # Kernel module symbol entries include the symbol name
        if "__ksymtab" in str(string_data.getAddress()) or "EXPORT_SYMBOL" in s:
            exported.append({
                "name": s[:200],
                "address": str(string_data.getAddress()),
                "is_gpl": "GPL" in s,
            })
    return exported


def find_ioctl_handlers():
    """Identify potential ioctl handler functions."""
    fm = currentProgram.getFunctionManager()
    handlers = []
    for func in fm.getFunctions(True):
        name = func.getName()
        if "ioctl" in name.lower():
            handlers.append({
                "name": name,
                "address": str(func.getEntryPoint()),
                "size": func.getBody().getNumAddresses(),
            })
    return handlers


def find_file_operations():
    """Search for file_operations struct instances."""
    st = currentProgram.getSymbolTable()
    fops = []
    for sym in st.getAllSymbols(True):
        name = sym.getName()
        if "file_operations" in name or "fops" in name.lower():
            fops.append({
                "name": name,
                "address": str(sym.getAddress()),
            })
    return fops


def get_module_info():
    """Extract MODULE_* info strings."""
    from ghidra.program.model.data import StringDataInstance
    from ghidra.program.util import DefinedDataIterator

    info = {}
    for string_data in DefinedDataIterator.definedStrings(currentProgram):
        val = StringDataInstance.getStringDataInstance(string_data)
        s = val.getStringValue()
        if not s:
            continue
        for prefix in ["license=", "author=", "description=", "version=", "alias="]:
            if s.startswith(prefix):
                key = prefix.rstrip("=")
                info[key] = s[len(prefix):]
    return info


def main():
    init_exit = find_module_init_exit()
    result = {
        "binary": currentProgram.getName(),
        "type": "kernel_module",
        "module_init": init_exit["init"],
        "module_exit": init_exit["exit"],
        "exported_symbols": find_exported_symbols(),
        "ioctl_handlers": find_ioctl_handlers(),
        "file_operations": find_file_operations(),
        "module_info": get_module_info(),
    }
    print("===GHIDRA_JSON_BEGIN===")
    print(json.dumps(result, indent=2))
    print("===GHIDRA_JSON_END===")


main()
