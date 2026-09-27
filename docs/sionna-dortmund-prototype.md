# Dortmund Sionna RT bounded prototype, September 27, 2026

**Result: the expansion hypothesis remains unproven, even though a bounded simulation runs.** A real CPU Sionna RT 2.1.0 scene and radio map ran locally. Across five longitude-block folds on 10m-deduplicated H-Bahn receiver sites, adding simulated path gain to a measured-only sector/distance ridge baseline yields only a small mixed result, with four of five folds worse (mean MAE 6.91 dB vs 6.82 dB). Final metrics below use a site-exclusive fold assignment; no rounded receiver site is both train and test. This is a research test of a noisy assumed site on the same route, not off-route validation, global transfer, a tower map, or measured city-block coverage. Do not display this synthetic radio map as coverage.

## Reproduce and inputs

Run `scripts/sionna_dortmund_prototype.py` and `scripts/evaluate_sionna_dortmund.py` from this branch with the private local source files described in [clutter research](./clutter-research.md). The script verifies the DoNext MD5, samples 1 in 47 rows, and filters one anonymous MNO-C key (cell_index 28365056, PCI 371, EARFCN 1300). Its 741 raw samples are grouped by rounded 10m receiver location, then the location groups are split into five contiguous longitude-quantile folds. For each fold, the signal-weighted *reception center* is recomputed from that fold's training samples only. It assumes this point is a transmitter for a falsifiable test, but it is **not** a surveyed site; the known location is only of the receiver. It deduplicates to one sample per rounded 10m coordinate before scoring. Route samples remain time-correlated. The model uses training-only targets and a fixed Ridge alpha=50 for both arms. The features are distance/bearing/offset and optionally simulated path gain plus a path-found bit. No hyperparameter was picked from the test segment.

The local scene triangulates 50m GLO-30 digital **surface** model samples and extrudes 276 OSM building footprints inside a 400m radius at assumed uniform 12m height, with assumed concrete material. This can double-count structures already captured in the DSM. WorldCover was licensed and available, but is **not** used in the present Sionna scene; no landcover-aware simulation was tested. An isotropic 2.1GHz, 40dBm assumed transmitter sits 25m above the DSM at the receiver-derived center. This is not known antenna metadata or a valid NR SS-RSRP link budget. Sionna runs a 10m grid and receiver-position paths (terrain height + 1.5m), first-order reflection with refraction and diffraction off. The flat map receiver plane is above the area's maximum DSM and differs from actual ground receiver height; evaluate only receiver-position paths. The geometry is clipped, omitted non-convex footprints, uses an approximate local coordinate conversion, and has no material survey. Many measured sites have no simulated ray: 145/285 held-out sites across five folds have positive gain; counts per fold are below. Zero path gain is solver/scene abstention, *not* proof of no cellular service.

| Contiguous x-block | Measured-only sector/distance MAE dB | Plus Sionna path-gain MAE dB | Held-out sites | Positive Sionna path sites |
| --- | ---: | ---: | ---: | ---: |
| Fold 0 | **7.378** | 7.565 | 57 | 38 |
| Fold 1 | **8.394** | 8.573 | 57 | 25 |
| Fold 2 | **8.639** | 8.752 | 57 | 25 |
| Fold 3 | **5.762** | 5.856 | 57 | 29 |
| Fold 4 | 3.913 | **3.810** | 57 | 28 |
| Mean across folds | **6.817** | 6.911 | 285 | 145 |

The 0.094 dB aggregate degradation is small, model-specific, and on the *same rail route*. It does not establish transfer or justify a prediction layer. Each rounded receiver site belongs to exactly one fold and is excluded from that fold's anchor and regression fit. Random-ray and scene priors are fixed, not tuned or sensitivity-tested.

Source terms and attribution: [DoNext DOI](https://doi.org/10.17877/TUDODATA-2026-T6MYPO) CC BY 4.0; © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) under ODbL with [OSMF guidance](https://osmfoundation.org/wiki/Attribution_Guidelines); GLO-30 produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA, all rights reserved, with [modified-use terms](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM). [Sionna RT](https://github.com/NVlabs/sionna-rt/blob/main/LICENSE) Apache-2.0. No raw measurements or external geometries are checked into this branch. The scene and result arrays remain local rather than being redistributed under uncertain derived-data obligations.

Local runtime: Ubuntu Jammy CPU-only, pip `sionna-rt==2.1.0`, Dr.Jit 1.5.0, Mitsuba 3.9.1. System LLVM 15 aborts code generation (`Cannot select ... fminimum/fmaximum`); LLVM 11 is too old for opaque pointers. The test used `DRJIT_LIBLLVM_PATH` pointing to LLVM 18 shared library from the Ubuntu Jammy [apt.llvm.org](https://apt.llvm.org/jammy/) package, locally unpacked, not committed. Run:

```bash
for fold in 0 1 2 3 4; do
  DRJIT_LIBLLVM_PATH=/path/to/libLLVM-18.so.1 python3 scripts/sionna_dortmund_prototype.py --fold "$fold" --rays 30000 --out "/tmp/sionna-dortmund-fold-$fold"
  python3 scripts/evaluate_sionna_dortmund.py --run "/tmp/sionna-dortmund-fold-$fold"
done
```

The first smoke run used the already-published full-sample reception center and was **not** used for validation. SPLAT! 1.4.2 was also run against a converted DEM tile for a ~70m link. It yielded 6.15dB Longley-Rice loss despite 75.67dB free-space loss and thus a nonsensical +42.14dBm received signal from 10W ERP, so it was not scored as a comparable baseline at this short urban distance. Report such failed sanity checks rather than selecting flattering results.

## Expansion-oriented re-evaluation

The user's goal is to extend predictions into places without measured RF, not necessarily beat a local model trained where readings exist. The first table tests whether simulated features help a measured-data regression; it does **not** alone answer the intended transfer question. We therefore ran [`scripts/evaluate_sionna_transfer.py`](../scripts/evaluate_sionna_transfer.py) on the same site-exclusive longitude blocks, entirely withholding the test block's readings from anchor estimation and every calibration. A proxy transmitter remains inferred from readings in *other blocks along the same rail route*, not supplied by an independent site register. This is a **zero-target-label route-block** test, not a true zero-measurement city or global transfer test.

The controlled baselines are (a) textbook free-space path loss at assumed 2.1GHz and 40dBm, (b) its offset calibrated on training-area NR SS-RSRP, and (c) a training-area fitted log-distance model. The exploratory Sionna-only prediction uses path gain with a training-only offset and a loss floor for missing rays. The hybrid uses simulated path attenuation when a ray is found and the free-space proxy on a solver miss, with one training-only offset. All variants have identical holdout groups. Uncalibrated free-space predicts total generic received power, *not* NR SS-RSRP, and is deliberately shown as a failed sanity check rather than an easy benchmark to beat.

| Zero-target-label block | Calibrated free-space MAE dB | Distance-only MAE dB | Sionna path only MAE dB | Sionna/free-space fallback MAE dB |
| --- | ---: | ---: | ---: | ---: |
| 0 | 13.549 | 16.907 | 23.692 | **12.682** |
| 1 | 8.414 | **8.097** | 29.452 | 9.376 |
| 2 | 9.647 | **9.344** | 21.127 | 9.539 |
| 3 | 5.520 | **4.256** | 18.680 | 5.064 |
| 4 | 4.134 | **3.794** | 19.250 | 3.973 |
| Mean (285 sites) | 8.253 | 8.480 | 22.440 | 8.127 |

The hybrid's 0.126dB mean edge over *calibrated free space* is minor and loses against it in block 1. A training-residual absolute 90th-percentile interval covers only 83.1% of held-out sites for the hybrid and 81.4% for calibrated free space, so these are not calibrated 90% uncertainty estimates. Sionna alone is much worse and has no ray at 140 of the 285 held-out sites; a solver miss is an abstention, not a no-service judgment. Raw uncalibrated free-space yields 39.666dB mean MAE because its RF quantity and assumed EIRP are incompatible with the recorded SS-RSRP. A 0.126dB advantage is not strong enough to call the hybrid a validated wider-area predictor, especially without independent sites, sectors or off-route readings. No layer was deployed.

**Next gate:** independent, matchable sites and antenna metadata; an off-rail geographically held-out measured region with matching NR metric; randomized height/material/antenna priors; uncertainty and abstention calibration. Until then, call outputs `unvalidated_transfer` and keep them out of service-quality UI.
