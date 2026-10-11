# Python examples

Install the SDK with `python -m pip install ".[serial]"` from the repository root.
All examples take an explicit port; none opens hardware when imported or when
called with `--help`.

```sh
python examples/reader_info.py --port COM3 --baud 115200 --ports 1
python examples/inventory_answer.py --port COM3 --baud 115200 --antenna 1 --scan-time 3
```

Replace the port and baud rate with your reader's configuration. Antennas are
numbered from 1. Examples default to 57600 baud and one port when omitted.

| Example | Task |
|---|---|
| [reader_info.py](reader_info.py) | Read identification and capabilities |
| [get_set_power.py](get_set_power.py) | Read power; add `--dbm` to change it, `--persist` to save |
| [inventory_answer.py](inventory_answer.py) | One EPC inventory round |
| [inventory_fastid.py](inventory_fastid.py) | EPC + TID from compatible FastID tags |
| [inventory_mix.py](inventory_mix.py) | EPC + selected memory words |
| [inventory_scenario.py](inventory_scenario.py) | Continuous session with explicit stop |
| [read_memory.py](read_memory.py) | Read a bank using a known TID target |
| [write_user_memory.py](write_user_memory.py) | Write User words and verify |
| [write_epc.py](write_epc.py) | Update PC/EPC and verify using a stable TID |
| [nation_adapter.py](nation_adapter.py) | NATION-style power and information methods |

## Memory examples

Use a writable test tag and replace the example TID with a known unique identifier.
Read addresses/counts are in words; `--data` and `--password` are hex bytes.

```sh
python examples/read_memory.py --port COM3 --baud 115200 --tid E280116060000205DEADBEEF --bank 3 --word-address 0 --words 2
python examples/write_user_memory.py --port COM3 --baud 115200 --tid E280116060000205DEADBEEF --word-address 0 --data 1234ABCD
python examples/write_epc.py --port COM3 --baud 115200 --tid E280116060000205DEADBEEF --data E20034120123456789000002
```

The write examples execute the requested write. A TID prefix that matches multiple
tags is not a unique target. See [Tag memory](../docs/tag_memory.md) before writing.

For JavaScript/TypeScript, use the [Web Serial example](webserial/README.md).
