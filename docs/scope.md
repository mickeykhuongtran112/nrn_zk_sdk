# Scope

This project maintains a native Python implementation of the ZK Gen2/6C host
protocol: reader configuration, RF and antenna controls, inventory, tag memory,
buffer operations, GPIO, and diagnostics.

The core runs on CPython and Pyodide through an injected asynchronous byte
transport. `SerialTransport` provides the desktop serial connection; the
[Web Serial bridge](../web/README.md) connects browser applications.
The [local test console](../tests/demo_app/README.md) is a separate CPython tool.

The SDK does not implement application workflows such as checkout, attendance,
or warehouse reconciliation. ISO 18000-6B, a NATION wire emulator, shared network
services, and unsupported chip-specific extensions are outside its scope.

Supported commands and deployment conditions are listed in
[compatibility](supported_devices.md). Method signatures are in the
[API index](functions_implemented.md).
