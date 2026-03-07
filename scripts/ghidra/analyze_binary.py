# Ghidra Jython script: Generic ELF binary analysis
# Runs via: analyzeHeadless ... -postScript analyze_binary.py
# Output: JSON to stdout
#
# Available globals: currentProgram, monitor, state
# @category Analysis

import json
import sys


def get_functions():
    """Extract all function names and addresses."""
    fm = currentProgram.getFunctionManager()
    functions = []
    for func in fm.getFunctions(True):
        functions.append({
            "name": func.getName(),
            "address": str(func.getEntryPoint()),
            "size": func.getBody().getNumAddresses(),
            "is_external": func.isExternal(),
            "is_thunk": func.isThunk(),
        })
    return functions


def get_symbols():
    """Extract symbol table entries."""
    st = currentProgram.getSymbolTable()
    symbols = []
    for sym in st.getAllSymbols(True):
        sym_type = str(sym.getSymbolType())
        if sym_type in ("Function", "Label"):
            symbols.append({
                "name": sym.getName(),
                "address": str(sym.getAddress()),
                "type": sym_type,
                "is_global": sym.isGlobal(),
                "is_external": sym.isExternalEntryPoint(),
                "source": str(sym.getSource()),
            })
    return symbols


def get_imports():
    """Extract imported symbols from ELF dynamic section."""
    st = currentProgram.getSymbolTable()
    imports = []
    for sym in st.getExternalSymbols():
        imports.append({
            "name": sym.getName(),
            "library": str(sym.getParentNamespace()),
        })
    return imports


def get_exports():
    """Extract exported symbols."""
    st = currentProgram.getSymbolTable()
    exports = []
    for sym in st.getAllSymbols(True):
        if sym.isExternalEntryPoint():
            exports.append({
                "name": sym.getName(),
                "address": str(sym.getAddress()),
            })
    return exports


def find_gpl_strings():
    """Search for GPL/license strings in the binary."""
    from ghidra.program.model.data import StringDataInstance
    from ghidra.program.util import DefinedDataIterator

    gpl_strings = []
    keywords = ["GPL", "General Public License", "EXPORT_SYMBOL", "license", "MODULE_LICENSE"]

    for string_data in DefinedDataIterator.definedStrings(currentProgram):
        val = StringDataInstance.getStringDataInstance(string_data)
        s = val.getStringValue()
        if s and any(kw in s for kw in keywords):
            gpl_strings.append({
                "address": str(string_data.getAddress()),
                "value": s[:200],  # Truncate long strings
            })
    return gpl_strings


def main():
    result = {
        "binary": currentProgram.getName(),
        "format": str(currentProgram.getExecutableFormat()),
        "language": str(currentProgram.getLanguage()),
        "compiler": str(currentProgram.getCompiler()),
        "image_base": str(currentProgram.getImageBase()),
        "function_count": currentProgram.getFunctionManager().getFunctionCount(),
        "functions": get_functions(),
        "symbols": get_symbols(),
        "imports": get_imports(),
        "exports": get_exports(),
        "gpl_strings": find_gpl_strings(),
    }
    # Print JSON to stdout with marker so orchestrator can extract it
    print("===GHIDRA_JSON_BEGIN===")
    print(json.dumps(result, indent=2))
    print("===GHIDRA_JSON_END===")


main()
