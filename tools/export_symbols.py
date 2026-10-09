"""Export actual public Python symbols to the requested reviewable catalogue."""

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect():
    records = []
    for path in sorted((ROOT / "src/zk_rfid").rglob("*.py")):
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
                if relative.endswith("tag_features.py")
                or name in ("NationAdapter.get_beeper", "NationAdapter.set_filter_settings")
                else "unverified mapping; rejected explicitly"
                if name == "NationAdapter.set_rf_band"
                else "transport interface contract"
                if name.startswith("AsyncTransport")
                else "implemented; hardware unverified"
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
        "# Danh mục chức năng Python đã triển khai",
        "",
        "Sinh từ AST bằng `python tools/export_symbols.py`. Tên, chữ ký và dòng nguồn lấy trực tiếp từ implementation.",
        "",
        "Mức chứng cứ: manual V2.25/demo V6.8, unit/integration và runtime CPython/Pyodide. "
        "**Chưa nghiệm thu toàn bộ phần cứng.** Người dùng đã báo 3 hardware tests PASS qua ảnh trên COM13/115200; "
        "xem [phạm vi chứng cứ](demo_and_parity.md). Các giới hạn ở [ma trận hỗ trợ](supported_devices.md) và [errata](protocol/errata.md).",
        "",
        f"## API điều khiển ZKReader ({len(public)} symbol public)",
        "",
        "| Function/property | Chức năng | Implementation |",
        "|---|---|---|",
    ]
    for r in public:
        description = (r.get("description") or "").split("\n")[0].replace("|", "\\|")
        lines.append(
            f"| `{r['name']}` | {description} | [{r['file']}:{r['line']}](../{r['file']}#L{r['line']}) |"
        )
    lines += ["", "## Chữ ký public ZKReader", "", "```python"]
    for r in public:
        if "signature" in r:
            lines.append(("async " if r["async"] else "") + r["signature"])
    lines += [
        "```",
        "",
        "## Symbols theo tree package",
        "",
        "Bao gồm class, method, function và constant; mục vendor-tag được đánh dấu ngoài scope.",
        "",
    ]
    current = None
    for r in records:
        if r["file"] != current:
            current = r["file"]
            lines += ["", f"### {current}", ""]
        status = "" if r["status"].startswith("implemented") else " — **" + r["status"] + "**"
        lines.append(f"- **{r['kind']}** [`{r['name']}`](../{r['file']}#L{r['line']}){status}")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    records = collect()
    outputs = {
        ROOT / "docs/functions_implemented.md": render(records),
        ROOT / "docs/api_symbols.json": json.dumps(records, ensure_ascii=False, indent=2) + "\n",
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
            path.write_text(text, encoding="utf-8")
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
