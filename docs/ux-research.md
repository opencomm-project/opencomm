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
