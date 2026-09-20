# Public examples

Install the core package and only the native/geo dependencies required by the chosen example. Each example writes to a fresh output directory, has no hidden dependency on another example and never downloads model weights. External-asset examples generate explicit requirements until you provide real assets.

| Example | What executes | External requirements |
|---|---|---|
| 01 | Genuine CPU detector runs, re-evaluation and capsule | Native stack installed |
| 02 | Static inspection and wrapper preparation | Your trusted MM checkout/interpreter for native execution |
| 03 | Verified-run comparison and static views | Two actual run bundles |
| 04 | Generated GeoTIFF + real CPU inference and recovery | Native and rasterio |
| 05 | Six-arm planning; optional real CPU execution | Native for `--execute` |
| 06 | Grounding worker on an explicit job | Local model/processor/image/prompt identities |
| 07 | Genuine Mask R-CNN and exact RLE interchange | Native stack installed |
| 08 | Local original/reproduction registry and exchange | Native stack installed |

No fixture-only path is labeled execution of an unavailable pretrained model.
