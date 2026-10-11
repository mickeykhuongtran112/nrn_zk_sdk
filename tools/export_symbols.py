"""Generate the API index, symbols, and RF profile reference from the SDK source."""

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect():
    records = []
    for path in [ROOT / "src/zk_rfid.py"]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        relative = path.relative_to(ROOT).as_posix()

        def add(node, name, kind):
            record = dict(file=relative, line=node.lineno, name=name, kind=kind)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                record["signature"] = f"{name}({ast.unparse(node.args)})"
                if node.returns:
                    record["signature"] += " -> " + ast.unparse(node.returns)
                record["async"] = isinstance(node, ast.AsyncFunctionDef)
            record["description"] = (
                ast.get_docstring(node)
                if not isinstance(node, (ast.Assign, ast.AnnAssign))
                else None
            )
            record["status"] = (
                "unsupported by design"
                if name in ("VENDOR_TAG_COMMANDS", "require_vendor_feature")
                else "transport interface contract"
                if name.startswith("AsyncTransport")
                else "implemented"
            )
            records.append(record)

        for node in tree.body:
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                add(node, node.name, "class")
                for member in node.body:
                    if isinstance(
                        member, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ) and not member.name.startswith("_"):
                        if any(
                            isinstance(d, ast.Attribute) and d.attr in ("setter", "deleter")
                            for d in member.decorator_list
                        ):
                            continue
                        kind = (
                            "property"
                            if any(
                                isinstance(d, ast.Name) and d.id == "property"
                                for d in member.decorator_list
                            )
                            else "method"
                        )
                        add(member, node.name + "." + member.name, kind)
                    elif isinstance(member, ast.Assign):
                        for target in member.targets:
                            if isinstance(target, ast.Name) and target.id.isupper():
                                add(member, node.name + "." + target.id, "constant")
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and not node.name.startswith("_"):
                add(node, node.name, "function")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        add(node, target.id, "constant")
    return records


def render(records):
    public = [r for r in records if r["name"].startswith("ZKReader.")]
    lines = [
        "# API index",
        "",
        "Use `ZKReader` for device I/O. See [Python API](api.md) for results and lifecycle,",
        "[compatibility](supported_devices.md) for deployment limits, and [examples](../examples/README.md) for common tasks.",
        "",
        "Generated from source with `python tools/export_symbols.py`; edit source docstrings to update descriptions.",
        "",
        "## ZKReader",
        "",
        "| Method / property | Purpose | Source |",
        "|---|---|---|",
    ]
    for r in public:
        description = (r.get("description") or "").split("\n")[0].replace("|", "\\|")
        lines.append(
            f"| `{r['name']}` | {description} | [{r['file']}:{r['line']}](../{r['file']}#L{r['line']}) |"
        )
    lines += ["", "<details>", "<summary>Method signatures</summary>", "", "```text"]
    for r in public:
        if "signature" in r:
            lines.append(("async " if r["async"] else "") + r["signature"])
    lines += [
        "```",
        "",
        "</details>",
        "",
        "## Supporting symbols",
        "",
        "Native types, transport interfaces, command builders, and decoders.",
        "Module-level command builders return `Request` values without device I/O.",
        "Hardware coverage is recorded in [validation](validation.md).",
        "",
        "<details>",
        "<summary>All source symbols</summary>",
        "",
    ]
    current = None
    for r in records:
        if r["file"] != current:
            current = r["file"]
            lines += ["", f"### {current}", ""]
        status = "" if r["status"].startswith("implemented") else " â€” **" + r["status"] + "**"
        lines.append(f"- **{r['kind']}** [`{r['name']}`](../{r['file']}#L{r['line']}){status}")
    lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


def render_profiles():
    tree = ast.parse((ROOT / "src/zk_rfid.py").read_text(encoding="utf-8"))
    table = next(
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PROFILES" for t in node.targets)
    )
    lines = [
        "# RF profiles",
        "",
        "Known native Ex10 IDs from the SDK's `PROFILES` table. See [RF settings](rf_settings.md)",
        "for selection and [Inventory](inventory_modes.md#s-cst) for S-CST slots.",
        "",
        "Generated with `python tools/export_symbols.py`; edit source metadata to update it.",
        "Availability depends on reader firmware and tag support. Encoding labels are retained",
        "from the manual; these entries are not measured performance or detected capabilities.",
        "",
        "| ID | Modulation | PIE | Tari (us) | BLF (kHz) | Encoding |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for node in table.values:
        values = [ast.literal_eval(arg) for arg in node.args]
        lines.append("| " + " | ".join(str(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    records = collect()
    outputs = {
        ROOT / "docs/functions_implemented.md": render(records),
        ROOT / "docs/api_symbols.json": json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        ROOT / "docs/rf_profiles.md": render_profiles(),
    }
    if args.check:
        stale = [
            str(path)
            for path, text in outputs.items()
            if not path.exists() or path.read_text(encoding="utf-8") != text
        ]
        if stale:
            raise SystemExit("Stale catalogue: " + ", ".join(stale))
    else:
        for path, text in outputs.items():
            path.write_text(text, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            dict(
                symbols=len(records),
                reader_public=sum(r["name"].startswith("ZKReader.") for r in records),
            )
        )
    )


if __name__ == "__main__":
    main()
