# Contributing

Use Python 3.11 or later. Install the development dependencies in a virtual
environment from the repository root:

```sh
python -m pip install -e ".[dev,serial]"
```

## Checks

```sh
python -m ruff check src tests tools examples web
python -m ruff format --check src tests tools examples web
python -m pytest
python tools/export_symbols.py --check
python tools/compare_results.py
python tools/check_repository.py
```

After changing public source signatures or docstrings, regenerate the API index
with `python tools/export_symbols.py` and review the generated diff.

Browser checks use Node.js 22 and a separately installed runtime:

```sh
npm install --prefix local_data/pyodide pyodide@314.0.7 typescript@5.9.3
node --test tests/browser/demo_client.test.cjs tests/browser/webserial.test.mjs
node local_data/pyodide/node_modules/typescript/bin/tsc --noEmit --strict --lib es2022,dom web/zk-rfid-webserial.d.ts
node tests/runtime/run_pyodide.mjs local_data/pyodide/node_modules/pyodide/pyodide.mjs
```

Hardware tests are excluded by default. Follow [validation](docs/validation.md)
to select a device explicitly.

## Changes

Keep the runtime self-contained in `src/zk_rfid.py`. Use `ZKReader` as the device
I/O entry point and preserve native results, uncertain outcomes, and explicit
recovery. Add a regression for protocol or lifecycle fixes; a simulated result
must not be presented as hardware validation.

Write code comments, examples, and public documentation in English. Guides should
start with a working example or the decision an integrator needs to make. Keep
headings short and put byte layouts, firmware exceptions, and validation records
in reference pages. Use editable SVG diagrams for static layouts.

For bug reports, include SDK version, reader model/firmware, port count, operation,
expected/actual result, and a minimal reproducer. Attach only reviewed traces.
Tag passwords, unique identifiers, and workstation paths may need redaction.

## Repository contents

Keep local settings, vendor manuals/binaries, raw captures, and test logs under
`local_data/`. Use `artifacts/` for temporary screenshots and `tmp/` for scratch
files. These paths, environments, credentials, and build output are ignored.
`plan_agent.md` is a private planning file and may use Vietnamese.

The repository checker examines tracked files as well as untracked candidates:
adding a path to `.gitignore` does not remove an already tracked file.
It checks common secret patterns without printing matched values. This is a
guardrail, not a complete secret scanner.

Reviewed fixtures belong under `fixtures/` and identify their source as documented,
synthetic, or captured. Preserve upstream license notices and record any changes
to the [NATION reference](compat/nation/UPSTREAM.md).

## Release preparation

```sh
python -m build
python -m twine check dist/*
python tools/check_repository.py --dist dist
```

Review both archives. The wheel should contain `zk_rfid.py` and package metadata;
the source archive should also include examples, tests, browser assets, diagrams,
and the licensed reference. Neither should contain local plans, secrets, raw logs,
or vendor binaries.

Inspect `git status --short`, the diff, and any existing Git history before making
a public release. Removing a private file from the latest tree does not remove
earlier committed copies. Publish only after reviewing the release version,
compatibility notes, license, and archive contents.
