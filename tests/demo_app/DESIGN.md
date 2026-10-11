# Console design

The console uses a neutral light palette, system fonts, and compact controls for
reader evaluation. Semantic color distinguishes success, warnings, and failures;
status text remains visible independently of color.

## Structure

Connection settings lead into reader state, command/result panels, the tag table,
and transaction log. Navigation groups operations by reader configuration, RF and
antennas, inventory, tag memory, buffer, and diagnostics.

At 1280 px and above, command and result panels use two columns. Smaller screens
stack them. Tables and logs scroll within their own regions. Tag selection and
log details support keyboard interaction, visible focus, and persistent selection
through live updates.

## Styling

Tokens are defined in `static/style.css`. Fonts use Segoe UI/system-ui for controls
and Cascadia Code/Consolas/monospace for data; no remote fonts are loaded.
Motion is limited to short transitions and respects `prefers-reduced-motion`.

The initial style research used
[UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/50d8a7de0900119855614541f15a1a616691eb33).
The console layout, tokens, and behavior are maintained in this repository.

## Live updates

Tag data uses a separate NDJSON stream with cumulative counts. The client updates
existing rows using `requestAnimationFrame`; log and state requests run separately.
This keeps selection and focus stable and prevents a slow log render from blocking
tag updates. See [measurements and live display](../../docs/phase_and_live_view.md).

For visual checks, exercise connection, simulator, tag selection, result errors,
log details, and narrow layouts. Keep screenshots in ignored `artifacts/`.
