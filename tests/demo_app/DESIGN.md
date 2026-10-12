# Console design

The console uses a neutral light palette, system fonts, and compact controls for
reader evaluation. Semantic color distinguishes success, warnings, and failures;
status text remains visible independently of color.

## Structure

Connection settings collapse after connection. Inventory opens with three tasks:
continuous EPC, continuous FastID and a single scan. Antenna checkboxes translate
to the selected task's native mask or ordered sequence. Raw protocol controls are
kept in All APIs; changing a task cannot retain an incompatible port argument.

Connection discovery resolves model code through the Ex10 V6.8 reader-type table
and checks the per-port power response in Answer mode. All guided pages use the
resolved SDK capability, not the initial CLI port count or enabled mask. A manual
override remains explicit. Failed discovery closes the connection; no RF, antenna
or Work Mode settings are written automatically.

Antenna/power and RF settings use separate cards with explicit Read and Save/Apply
actions. Writes are followed by read-back; failed verification keeps the write
acknowledgement visible. Per-port values start blank until read. Start does not
save antenna selection. Configuration controls lock while reading or applying.

The main task, Start/Stop and observations take priority. Query settings, request
JSON, native result and transaction log use progressive disclosure. Other command
groups remain available for tag memory, Ex10 settings, buffers and diagnostics.

At 1280 px and above, command and result panels use two columns. Smaller screens
stack them. Tables and logs scroll within their own regions. Tag selection and
log details support keyboard interaction, visible focus, and persistent selection
through live updates.

## Styling

Tokens are defined in `static/style.css`. Fonts use Segoe UI/system-ui for controls
and Cascadia Code/Consolas/monospace for data; no remote fonts are loaded.
Motion is limited to short transitions and respects `prefers-reduced-motion`.

Task grouping and supported-setting visibility were informed by
[Zebra 123RFID's reader configuration](https://docs.zebra.com/us/en/rfid/123rfid-desktop/c-123rfid-desktop-application-features/c-123rfid-desktop-online-reader-configuration.html).
Save and Apply are separate from run controls, consistent with its
[configuration workflow](https://docs.zebra.com/us/en/rfid/123rfid-desktop/c-123rfid-desktop-saving-an-online-config.html).
The layout is maintained here; no vendor RF settings or hardware capabilities
are inferred from another reader's interface.

## Live updates

Tag data uses a separate NDJSON stream with cumulative counts. The client updates
existing rows using `requestAnimationFrame`; log and state requests run separately.
This keeps selection and focus stable and prevents a slow log render from blocking
tag updates. See [measurements and live display](../../docs/phase_and_live_view.md).

For visual checks, exercise connection, simulator, tag selection, result errors,
log details, and narrow layouts. Keep screenshots in ignored `artifacts/`.
