# tech-art

Minimal robotics × code posters in the Edreate brand palette (Brand Book in
[Brand-Identity-Media](https://github.com/edreate/Brand-Identity-Media)). Every drawing comes
from the maths or code printed on it.

| Poster | Idea | Made with |
| --- | --- | --- |
| reach. | forward kinematics of a 3-link arm, ghost poses + end-effector trace | Python → SVG |
| see. | a laser scan: only the points the robot perceives, never the room | Python → SVG |
| settle. | one plant, three PID tunings | Python → SVG |
| hello. | Python vs C++ on a brand diagonal | Python → SVG |
| build. | a robot face out of a triangular lattice (brand cover motif) | Python → SVG |
| drive. | differential drive: two wheel tracks and the poses along the path | Python → SVG |
| plan. | A* on an occupancy grid, explored cells fading by order | Python → SVG |
| connect. | node graph with brand icons, topics on the arrows | draw.io |
| assemble. | a rover from draw.io primitives, annotated like a spec sheet | draw.io |

**Sensors** (`src/sensors.py`):

| Poster | Sensor | Idea |
| --- | --- | --- |
| feel. | IMU | drifting gyro, noisy accelerometer, and the complementary filter between them |
| ping. | ultrasonic | wavefronts out, echoes back, and Δt on the scope → d = cΔt/2 |
| count. | wheel encoder | slotted disc, A/B quadrature waves, the ×4-decoded count going up and back down |
| project. | camera | pinhole model: a cube, its rays, and the picture left on the image plane |
| orient. | magnetometer | raw ellipse recentred and rescaled into a circle (hard + soft iron) |
| locate. | GNSS / beacons | range rings and Gauss–Newton walking from a guess to the fix |
| chirp. | FMCW radar | chirp + echo, the beat signal, and the FFT that turns it into ranges |
| triangulate. | stereo camera | pixel rays from two cameras cross in a lattice that coarsens with depth |

Palette: Cornflower Blue `#4531CC`, Teal Blue `#448882`, Lavender Blue `#8C8AFE`,
Rich Black `#0C0C0C`, Cream `#FCF3D1`, and their tints. Fonts: Poppins (titles),
Fira Code (code), Urbanist (diagram labels). The `edr.` mark sits in the corner triangle.

## Build

```bash
uv run --no-project --with fonttools --with brotli python src/posters.py     # out/svg/*.svg
uv run --no-project --with fonttools --with brotli python src/sensors.py     # out/svg/*.svg (sensors)
uv run --no-project --with fonttools --with brotli python src/drawio_art.py  # out/drawio/*.drawio + out/svg
./src/render.sh                                                              # out/png/*.png (2160×2700)
```

- SVGs are self-contained: fonts are subset and embedded.
- `.drawio` files open and edit in draw.io. To see the brand fonts there, install
  Poppins and Fira Code from `brand/fonts/` (Urbanist must be installed too).
- PNGs are rendered with headless Chrome; draw.io's CLI can't load fonts that aren't installed,
  so the draw.io pieces are exported to SVG, get the fonts injected, then rendered.

`brand/` holds copies of the fonts, icons and logo mark from Brand-Identity-Media.
