# Documentation

Start with [Getting started](getting_started.md) to install the SDK and read your
first tags. The Python and browser interfaces use the same protocol implementation.

| Guide | Contents |
|---|---|
| [Python API](api.md) | Connections, results, errors, and recovery |
| [Examples](../examples/README.md) | Runnable commands for common tasks |
| [Inventory](inventory_modes.md) | Mode selection, tag data, and session cleanup |
| [Tag memory](tag_memory.md) | Bank layout, addressing, targeting, and writes |
| [RSSI and phase](phase_and_live_view.md) | Raw values, units, and measurement limits |
| [Browser integration](../web/README.md) | JavaScript / TypeScript with Web Serial |
| [Test console](../tests/demo_app/README.md) | Interactive commands and simulated reader |
| [NATION adapter](nation_comparison.md) | Migration and mapping limits |

## Reference

- [Compatibility](supported_devices.md) and [scope](scope.md)
- [API index](functions_implemented.md) and [machine-readable symbols](api_symbols.json)
- [Wire format](protocol/zk_frame.md), [commands](protocol/zk_commands.md),
  [tag reports](protocol/zk_tag_report.md), and [errata](protocol/errata.md)

## Validation

- [Software and hardware coverage](validation.md)
- [Recorded hardware session](hardware_live_view_check.md)
- [RF benchmark procedure](inventory_benchmark.md)
- [Vendor feature comparison](demo_and_parity.md)

For development and release checks, see [CONTRIBUTING.md](../CONTRIBUTING.md).
