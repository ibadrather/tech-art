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

**Robots** (`src/robots.py`, one folder per kind of robot in `out/robots/`, contact sheet in
`out/robots/overview.png`). Each robot type gets three posters, each on something that makes it hard:

| Robot | Poster | Idea |
| --- | --- | --- |
| aerial | hover. | the X mixer: four motors, four knobs; one command and what each rotor does |
| aerial | tilt. | underactuated: thrust only points along body-z, so it has to lean to move sideways |
| aerial | endure. | flight time vs battery mass from momentum theory; it peaks at battery = 2 × frame |
| underwater | drift. | no GPS below the surface: dead reckoning error grows until it comes up for a fix |
| underwater | tether. | current drag bows the tether, and half of it lands on a robot that can't push back |
| underwater | whisper. | same 80 dB budget: radio dies in centimetres, light in metres, sound goes for kilometres |
| manipulator | singular. | manipulability ellipses over the workspace, flattening to lines at the edges |
| manipulator | grasp. | two-finger grasps and friction cones: one holds, one slips |
| manipulator | either. | IK gives two elbows (where two circles cross); the table picks one |
| legged | balance. | quadruped crawl: the body shifts into the triangle of the three feet still down |
| legged | stride. | biped LIPM: ZMP hops foot to foot, the CoM that produces it sways between |
| legged | gait. | walk, trot, pace, bound, gallop: same four legs, different timing |

**Localization** (`src/localization.py`, one folder per domain in `out/localization/`, contact sheet in
`out/localization/overview.png`). Four ways each to answer "where am I?":

| Domain | Poster | Idea |
| --- | --- | --- |
| ground | particles. | Monte Carlo localization in a corridor with three doors: anywhere → three guesses → one |
| ground | align. | ICP: a new lidar scan paired to its nearest map points and re-fit until they agree |
| ground | close. | pose graph: odometry misses the start by metres; one loop-closure edge spreads the error away |
| ground | banana. | heading uncertainty bends the odometry cloud into an arc; the Gaussian mean sits off it |
| aerial | fuse. | GPS + IMU Kalman filter: σ grows at 100 Hz, snaps back at 1 Hz; the IMU alone runs off as ½bt² |
| aerial | flow. | optical flow sees v / h: the same picture at 2 m and 6 m, so it needs the rangefinder |
| aerial | rtk. | carrier phase has 19 cm ticks and no numbers; a third satellite picks the one right crossing |
| aerial | spread. | same range error, three skies: dilution of precision from 1.4 to 6.8 |
| underwater | listen. | one ping, three hydrophones: each time difference of arrival is a hyperbola |
| underwater | beams. | DVL: four beams at 30°, each echo shifted in pitch by the speed along it |
| underwater | contour. | terrain-relative navigation: slide the measured depth profile over the chart until the hills line up |
| underwater | bend. | sound bends toward slow water (Munk profile), so travel time × 1500 isn't the straight-line range |

Palette: Cornflower Blue `#4531CC`, Teal Blue `#448882`, Lavender Blue `#8C8AFE`,
Rich Black `#0C0C0C`, Cream `#FCF3D1`, and their tints. Fonts: Poppins (titles),
Fira Code (code), Urbanist (diagram labels). The `edr.` mark sits in the corner triangle.

## Build

```bash
uv run --no-project --with fonttools --with brotli python src/posters.py     # out/svg/*.svg
uv run --no-project --with fonttools --with brotli python src/sensors.py     # out/svg/*.svg (sensors)
uv run --no-project --with fonttools --with brotli python src/drawio_art.py  # out/drawio/*.drawio + out/svg
uv run --no-project --with fonttools --with brotli python src/robots.py      # out/robots/<robot>/*.svg
uv run --no-project --with fonttools --with brotli python src/localization.py # out/localization/<domain>/*.svg
./src/render.sh                                                              # out/png/*.png (2160×2700)
./src/render.sh out/robots                                                   # a PNG beside every robot SVG
./src/render.sh out/localization                                             # a PNG beside every localization SVG
```

- SVGs are self-contained: fonts are subset and embedded.
- `.drawio` files open and edit in draw.io. To see the brand fonts there, install
  Poppins and Fira Code from `brand/fonts/` (Urbanist must be installed too).
- PNGs are rendered with headless Chrome; draw.io's CLI can't load fonts that aren't installed,
  so the draw.io pieces are exported to SVG, get the fonts injected, then rendered.

`brand/` holds copies of the fonts, icons and logo mark from Brand-Identity-Media.
