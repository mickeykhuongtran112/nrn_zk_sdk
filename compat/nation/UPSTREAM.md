# Upstream provenance

- Repository: [Nextwaves SDK](https://github.com/Nextwaves-Industries/nextwaves-sdk).
- Commit: `d416b0d3bd5a103cf6b1833b13f0c88e9dfbe24b`.
- Imported: 2026-10-09 from the pinned Git blobs.
- Upstream paths: `sdk/nation/python/nrn.py` and `sdk/nation/python/LICENSE`.
- License: upstream MIT notice retained without modification.

| File / revision | SHA-256 | Bytes |
|---|---|---:|
| Original upstream nrn.py | `28ffcbd698a04dc35a324c7b7b3cfdb8edc2ff7b61dd730924e29c6cc1975596` | 97,790 |
| English nrn.py, 2026-10-11 | `b1d6c13db195428c73ee1df390a18b93ff6f0ad1d5b4864a36c006751211747a` | 97,644 |
| Original LICENSE | `faaf4cdb3a3c000b6084cb82ab938c465756d2925d5c11b76d78aa56388c2741` | 1,308 |

## Local changes

The 2026-10-11 revision translates Vietnamese comments, docstrings, two exception
messages, a timeout message, and a debug message. It also replaces two drafting
comments with descriptions of their functions and normalizes source line endings.

Control flow, protocol constants, frame handling, and public signatures are
unchanged. Reversing the text substitutions reproduces the original Python AST.
The integrity test pins this documented English revision and the original license.

Further changes should update this record, the integrity test, and
[CHANGELOG.md](CHANGELOG.md). The reference is not part of the ZK runtime.
