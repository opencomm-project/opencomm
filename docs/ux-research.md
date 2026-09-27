# Map exploration patterns, September 2026

The decision is to present a single sampled measured-RF story, not claim national network coverage. The public site is an independent prototype, not affiliated with any product below.

| Reference | Grounded feature/pattern | Fit for opencomm now |
| --- | --- | --- |
| [nPerf coverage map](https://www.nperf.com/en/map/US/-/-/signal) | Coverage/bitrate are separate maps with technology and network context; the professional view also filters time. | Borrow one obvious filter row, but filter **measured RSRP only**. No speed data, carrier comparison or coverage claim. |
| [CellMapper](https://www.cellmapper.net/Index) and its [map](https://www.cellmapper.net/map) | Detailed map of contributed towers, signal trails, technology and IDs. | Borrow tap-a-point detail with source record and value. Do not label DoNext measurements as towers or infer routes between gaps. |
| [Opensignal coverage maps](https://insights.opensignal.com/coverage-maps) | Consumer-readable, place/network context for app-contributed results. | Make Dortmund and the H-Bahn scope visible before a user interprets the map; no operator ranking where operator labels are incomplete. |
| [Ookla Speedtest Maps](https://www.ookla.com/articles/introducing-speedtest-maps-ios) | Map-first navigation to explore levels of mobile service in places of interest. | Keep map prominent and give one obvious return-to-route action, without claiming service level or speed. |
| [Ofcom Map Your Mobile](https://www.ofcom.org.uk/mobile-coverage-checker) | Distinguishes coverage availability and performance in plain language. | Explain why observed RSRP points are neither comprehensive coverage nor performance. |

The interface uses a restrained typographic hierarchy, whitespace, one primary action, a small number of filter choices, visible provenance, responsive cards and reduced-motion handling. These are broad design principles rather than a copy of any competitor or Apple's trade dress. Signal thresholds are display bins, **not** a quality guarantee. The bins are ≥−85, −105 to <−85, and <−105 dBm. They have no network/operator-specific interpretation. A map view draws up to 2,000 sampled records per bin; total is 10,148 rows in the extract. No measurement outside DoNext H-Bahn is represented.

## Product-owner usability correction

A user test found the first redesign still required scrolling to reach the map and reading too much to interpret a point. The current iteration puts the map immediately after a compact one-line orientation, within the first viewport on desktop and mobile. The static on-map RSRP legend explains the three color bins before any tap; tap gives one large measured dBm value, then a voluntary Source details disclosure. The bins are display categories only, never an RF-quality or coverage score. This correction supersedes the earlier large-hero layout.

## Anonymized operator and signal-type views

DoNext H-Bahn exposes anonymized MNO codes A/B/C, not named German carriers or an MNC. Its sample is highly uneven: C=10,072, A=74, B=2. A per-code map view is possible, but cross-code comparisons are not a ranking or nationally representative. The source has `ss_rsrp` and `rsrp`, which support separate NR/5G-signal and LTE/4G-signal map views; this is based on the measured field, not a comprehensive device/RAT classification. Explicit `network` labels are rare and preserved separately in point detail. The v1 controls combine an RSRP bin, anonymized MNO code and signal type on the same map; no carrier name is guessed.

## Map-first mobile controls, September 27, 2026

The owner asked for a larger mobile map with filters, aggregations and layers on the map. This iteration uses the map as the first mobile viewport: a persistent evidence-grade legend and compact result count stay on it; a floating "Layers & filters" button opens a contained, scrollable bottom control panel. Region choice, evidence layers and filters use explicit selected states. The data card opens on a point tap, and provenance remains accessible from the card and the method page. Desktop retains its visible toolbar. This is a responsive presentation change, not a new aggregation algorithm or a coverage layer.

- [Material Design 3 bottom sheets](https://m3.material.io/components/bottom-sheets/overview) treats bottom sheets as secondary content anchored at the bottom, especially for compact phone widths; modal and standard variants trade access to primary content. We use a simple dismissible panel rather than block map navigation permanently.
- [Google Maps SDK controls and gestures](https://developers.google.com/maps/documentation/android-sdk/controls) describes edge-positioned controls, padding to avoid overlap, and map interactions such as pinch and pan. We reserve a separate zone for map controls and keep the map interactive when the panel is closed.
- [CellMapper's cellular map](https://www.cellmapper.net/map) demonstrates a cellular-data map as the main exploration surface. This product does not borrow its tower labels: OpenCellID positions and DoNext reception centers are estimates, not verified physical towers.
- [nPerf mobile map](https://www.nperf.com/en/map/5g) is a comparator for technology/network filtering, but its service/coverage semantics cannot be copied onto this inventory or one measured rail route.

Design guardrails: first-screen region/evidence grade must remain legible, measurement strength never appears on Israel inventory, every count distinguishes shown sampled points from matching records, and menu controls need visible focus and press states. Current points are sampled for display, not dynamically aggregated density. A future density/aggregation mode requires its own legend and cell-count semantics.
