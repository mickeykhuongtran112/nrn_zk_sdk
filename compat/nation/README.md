# NATION reference

This directory contains the upstream NATION driver for comparison and regression
tests. Its origin and local changes are recorded in [UPSTREAM.md](UPSTREAM.md).
The original [MIT license](LICENSE) is retained.

The reference driver uses blocking I/O, threads, and pyserial. The native ZK SDK
and its adapter do not import it. It is included in the source archive for
provenance checks and excluded from the wheel.

Comments, docstrings, and four diagnostic messages have been translated into
English. Protocol logic is unchanged; this is a documented local revision,
not a byte-identical upstream copy.

This directory contains reference material only. The optional runtime adapter,
conversion cases and full API manual are in
[mapping/nation_to_zk](../../mapping/nation_to_zk/README.md).
Neither the native ZK core nor that adapter imports this driver.
