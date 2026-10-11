# Protocol fixtures

Keep fixture origins explicit:

| Directory | Source |
|---|---|
| `documented/` | Published command definitions or independent historical vectors |
| `synthetic/` | Constructed test data and simulated behavior |
| `captured/` | Bytes recorded from physical hardware |

Each case identifies its source/revision, TX/RX bytes, expected result, byte order,
units, and applicable conditions. Stream cases include chunk boundaries and timing;
fault cases describe the injected failure.

Hardware captures also identify reader model/firmware, baud, antennas/RF settings,
tag chip, date, and operation. Keep unreviewed captures under `local_data/`; remove
sensitive identifiers/passwords before promoting a case to a public fixture.
Never relabel synthetic or documented data as a new hardware capture.

The eight [ZK TX vectors](zk/documented/frames.json) are used by the runtime checks.
The simulated RX peer is in [tests/conftest.py](../tests/conftest.py).
