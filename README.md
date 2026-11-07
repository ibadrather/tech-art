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

**Minimal** (`src/minimal.py`, `out/minimal/`). The quiet siblings of the core set: one word, one drawing,
one line of code, two or three colours and a lot of empty paper.

| Poster | Idea |
| --- | --- |
| boot. | one command, three `[ ok ]` checks and a cursor on black |
| blink. | the hello world of hardware: one LED and the 500 ms square wave that drives it |
| zero. | every robot starts at the origin: an x arrow, a y arrow and a dot |
| loop. | sense, think, act: three dots on one circle, going round |
| step. | a stepper motor's 200 ticks a turn, 37 of them taken (66.6°) |
| grip. | a parallel gripper closing on a ball until contact |
| stop. | the emergency stop: a blue mushroom button in a cream ring |
| charge. | a battery with four cells of five, and the line that sends it home to the dock |
| go. | a start triangle, a goal target and one dotted line between |
| rotate. | a square turned by θ, its starting pose dashed behind, and the 2×2 matrix that did it |
| grid. | an 8 × 8 occupancy grid: dots are free, squares are not, one robot |
| think. | a tiny neural network, 3 → 4 → 2, and `relu(W @ x + b)` |
| debug. | code as grey bars, one highlighted line and its breakpoint |
| commit. | a branch leaves main, picks up three commits and merges home to HEAD |
| rest. | a robot asleep: closed eyes, an antenna and three rising z's |
| bye. | hello.'s other half: the diagonal flipped, `return 0;` and `exit(0)` |

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

**Robots** (`src/robots.py`, one folder per kind of robot in `out/robots/`). Each robot type gets three posters, each on something that makes it hard:

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

**Localization** (`src/localization.py`, one folder per domain in `out/localization/`). Four ways each to answer "where am I?":

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

**Drone** (`src/drone.py`, one folder per part of the drone in `out/drone/`). One small folding quad (sub-250 g, 4K camera on a 3-axis gimbal) taken apart.
Each poster carries an **issue / fix** pair under the title: the problem the design has to beat, and how.

| Part | Poster | Issue → fix |
| --- | --- | --- |
| airframe | anatomy. | a big drone's sensors, radios and camera in 249 g → fold the arms, put each sensor where the noise isn't |
| airframe | weigh. | 250 g is where the rules get stricter → 250 squares, one per gram: what each is spent on, 1 g spare |
| airframe | fold. | small props cost hover power (P ∝ 1/D), big props need a big frame → 6" props on arms that swing in, 8× smaller |
| airframe | wind. | wind blows it out at 20 m/s and lets it crawl home at 4 → lean into it (33° at 10.7 m/s), budget the trip back |
| camera | readout. | rows are read one at a time: pans lean, buzz wobbles → faster readout + the gimbal |
| camera | stops. | ~15 stops of scene, ~11.5 per read → dual-gain HDR merge, stored log |
| camera | shutter. | f/1.7 in sun: 1/5700 s, stuttering motion → ND filters back toward the 180° rule |
| camera | bin. | 1.2 µm pixels at dusk: SNR 3 → quad-Bayer 2×2 binning: 12 MP, SNR 6 (simulated photons) |
| gimbal | level. | the body tips ±30° to fly → a 1 kHz loop holds the camera within 0.2° (simulated) |
| gimbal | damp. | motor buzz at ~150 Hz → rubber isolators tuned to 25 Hz pass 4.5 % (transmissibility) |
| gimbal | lock. | middle axis at 90° lines up the outer and inner → keep roll small; motor speed ∝ 1/cos(roll) |
| gimbal | portrait. | a 9:16 crop keeps 32 % of a 16:9 frame → roll the camera 90° and keep all of it |
| link | budget. | −6 dB per doubling of distance → step the bitrate down: 1080p60 to 8 km, 720p to 25 km |
| link | fresnel. | trees under the line of sight still clip the radio's ellipse (−5.4 dB) → fly higher |
| link | hop. | 2.4 GHz is shared with everyone → listen, hop across channels and bands (3 lost slots vs 15) |
| link | lag. | every stage adds delay: 110 ms = 1.8 m at 16 m/s → slice the frame so stages overlap: 45 ms |
| navigate | bowl. | a compass 80° off turns position hold into a growing spiral → cross-check with GPS velocity |
| navigate | home. | GPS lands it ±1.5 m from takeoff, maybe in the lake → climb, fly back, land on the takeoff photo |
| navigate | reserve. | the battery to get home grows with distance → turn back where battery left meets battery needed |
| navigate | avoid. | stereo sees ~18 m, 16 m/s needs 23 m to stop → avoidance caps speed at 12.9 m/s |
| missions | orbit. | a circle in wind needs a different lean all the way round (3° to 35°) → steer it all from the subject point |
| missions | map. | one photo can't measure depth → lawnmower grid with 80 / 70 % overlap, 1.1 cm per pixel at 60 m |
| missions | follow. | the subject disappears behind trees → a constant-velocity Kalman filter predicts, doubt grows, snaps back |
| missions | pano. | a 71° × 56° lens, a 360° × 180° sphere → 21 frames in rings of yaw at four tilts, stitched |

**GPS** (`src/gps.py`, one folder per stage in `out/gps/`). From radio noise to a centimetre fix. The sky on them is
computed: GPS's 24-slot baseline (+7 spares), GLONASS, Galileo and BeiDou as Kepler orbits over 52.5° N.
Each poster carries an **issue / fix** pair under the title.

| Stage | Poster | Issue → fix |
| --- | --- | --- |
| sky | constellations. | one system's ~30 satellites leave a thin sky → fly four (109 sats, 31 above 10° right now), each drawn from its orbit |
| sky | skyplot. | from 52.5° N no GPS satellite crosses part of the northern sky (55° orbits) → site antennas with a clear south |
| sky | relativity. | orbit clocks gain 38.6 µs a day, 11.6 km of range → tune them slow on the ground: 10.22999999543 MHz |
| sky | wait. | the nav message is 50 bit/s: 18–48 s for orbits, 12.5 min for the almanac → hot start, or download it (A-GNSS) |
| signal | bands. | four systems share one slice of L-band → overlap the carriers (all multiples of 10.23 MHz), split them by code |
| signal | code. | every satellite on 1575.42 MHz, 20 dB under the noise → real 1023-chip Gold codes; correlate and one lag stands out |
| signal | doppler. | satellites move up to 929 m/s along your line of sight: ±4.9 kHz → search 21 Doppler bins × 1023 code phases |
| signal | iono. | the ionosphere delays code by metres, 2.8× more at 10° → it's 1/f²: L1 + L5 iono-free cancels it |
| fix | intersect. | a range gives a sphere, not a direction → two spheres give a circle, three give two points, four leave one |
| fix | four. | 1 µs of receiver clock error is 300 m on every range → solve x, y, z and b: Gauss–Newton from the Earth's centre |
| fix | geoid. | GPS height is above an ellipsoid; sea level wanders ±100 m around it → H = h − N with a geoid model |
| fix | dop. | every satellite is above you, so height is the weak axis → VDOP ≈ 1.5 × HDOP; all four systems pull DOP below 1 |
| error | errors. | six independent errors on each range, ionosphere biggest → they add as squares: 4.4 m, not 7.7 |
| error | multipath. | a wall 75 m away adds a copy 0.46 chip late → narrow correlator: 45 m of error becomes 7 m (error envelope) |
| error | canyon. | between 24 m buildings the sky is a strip: 3 GPS left, no fix → all four constellations: 10 in view, HDOP 1.8 |
| error | cep. | "accurate to 3 m" means nothing without the circle → CEP 50 %, DRMS ~65 %, R95, 2DRMS ~98 % on 2000 fixes |
| augment | dgps. | nearby receivers share most of the error → a base on a known point sends it: 4.4 m → 1.2 m, fading with distance |
| augment | sbas. | a DGPS base only helps nearby → reference stations fit a 5° ionosphere grid; a GEO satellite broadcasts it on L1 |
| augment | snap. | the float RTK answer wanders at decimetres → ratio test passes, integers fixed, the error snaps to 1.2 cm (simulated) |
| augment | ladder. | how close, and how long can you wait? → standalone to static survey: each rung costs a band, a base, a fee, or time |

**IMU** (`src/imu.py`, one folder per theme in `out/imu/`). What's inside an inertial measurement unit, what a better
one costs, why it drifts, and how to live with it. Each poster carries an **issue / fix** pair under the title.

| Theme | Poster | Issue → fix |
| --- | --- | --- |
| sense | proof. | a chip can't feel force, and 1 g moves a 2 µg mass 15.5 nm → comb fingers either side: (C1 − C2)/(C1 + C2) is linear in a |
| sense | coriolis. | no room for a spinning wheel on a chip → vibrate a mass at 20 kHz; rotation pushes it sideways, 2.7 nm at 100 °/s |
| sense | sagnac. | a vibrating mass can't hold 0.01 °/h → light both ways round 1 km of fibre: the Earth's spin is 99 µrad of phase |
| grade | grades. | gyro bias and price both span six orders of magnitude → consumer to strategic, and which grades can find north alone |
| grade | coast. | with no fix, error grows as t² then t³ → the grade buys time: 10 m in 26 s for a phone, 4 min for an airliner (Schuler-bounded) |
| grade | allan. | one noise number can't describe a gyro → Allan deviation of 2 h at rest: ARW on the −½ slope, bias instability at the floor |
| drift | integrate. | a phone on a table, 2 mg of bias, integrated twice: 36 m in a minute → learn the bias at rest; noise alone leaves ±0.6 m |
| drift | leak. | a 1° tilt error leaves 0.17 m/s² of gravity behind → get attitude right first: 0.057° of tilt costs as much as 1 mg of bias |
| drift | warm. | bias moves 1.5 °/s across −20…70 °C → chamber sweep, cubic fit, subtract live; the hysteresis loop is what's left |
| fuse | bias. | gyro bias integrates into an angle that walks away → a Kalman filter with the bias in the state learns it from the accelerometer |
| fuse | yaw. | gravity pins roll and pitch, not heading → a magnetometer (gated against steel) or GPS course; gyro alone drifts 30° in 10 min |
| fuse | stance. | a shoe IMU integrated twice is 34 m off after a 72 m walk → zero-velocity update every footfall: 0.23 m |
| use | tumble. | biased, scaled 1–2 % off, axes not square → rest it on six faces; gravity is known, solve 12 parameters from 18 numbers |
| use | mount. | 15 cm off-centre on a robot spinning at 3 rad/s reads 1.35 m/s² → mount at the centre or subtract ω×(ω×r) + α×r |
| use | alias. | 190 Hz motor buzz sampled at 200 Hz becomes a 10 Hz wobble → sample at 1 kHz, low-pass in the chip, decimate: −30 dB |

Palette: Cornflower Blue `#4531CC`, Teal Blue `#448882`, Lavender Blue `#8C8AFE`,
Rich Black `#0C0C0C`, Cream `#FCF3D1`, and their tints. Fonts: Poppins (titles),
Fira Code (code), Urbanist (diagram labels). The `edr.` mark sits in the corner triangle.

## Layout

```
out/<series>/[<group>/]<name>.svg   + .png beside it (2160×2700); overview.png = contact sheet
    core/                           posters.py + drawio_art.py (also the .drawio sources)
    minimal/                        minimal.py
    sensors/                        sensors.py
    robots/<robot>/                 robots.py
    localization/<domain>/          localization.py
    drone/<part>/                   drone.py
    gps/<stage>/                    gps.py
    imu/<theme>/                    imu.py
gallery/                            static browser for everything in out/
```

## Gallery

```bash
make gallery     # rescan out/ -> gallery/posters.js + thumbnails (run after adding posters)
make run         # serve the repo, then open http://localhost:8000/gallery/
```

A shop-style browser for everything in `out/`: search, a collection tree (series → group) with
counts, active-filter chips, breadcrumbs, sort and tile size. Each poster opens in a detail view
with downloads (SVG / PNG), its file path, and more from the same group. Everything is in the URL
(e.g. `#in=drone/camera,robots&q=lidar&p=drone/camera/readout`), so views are linkable and
back / forward work. Keys: `/` search, ← / → browse, F fullscreen, Esc close.
Descriptions come from the tables above; thumbnails (`gallery/thumbs/`, git-ignored) are built
with macOS `sips` — without them the gallery falls back to the full PNGs.

## Build

```bash
uv run --no-project --with fonttools --with brotli python src/posters.py      # out/core/*.svg
uv run --no-project --with fonttools --with brotli python src/sensors.py      # out/sensors/*.svg
uv run --no-project --with fonttools --with brotli python src/drawio_art.py   # out/core/*.drawio + .svg
uv run --no-project --with fonttools --with brotli python src/minimal.py      # out/minimal/*.svg
uv run --no-project --with fonttools --with brotli python src/robots.py       # out/robots/<robot>/*.svg
uv run --no-project --with fonttools --with brotli python src/localization.py # out/localization/<domain>/*.svg
uv run --no-project --with fonttools --with brotli python src/drone.py        # out/drone/<part>/*.svg
uv run --no-project --with fonttools --with brotli python src/gps.py          # out/gps/<stage>/*.svg
uv run --no-project --with fonttools --with brotli python src/imu.py          # out/imu/<theme>/*.svg
./src/render.sh                                                               # a PNG beside every SVG in out/
./src/render.sh out/drone                                                     # only under out/drone
python3 src/gallery.py                                                        # refresh the gallery
```

- SVGs are self-contained: fonts are subset and embedded.
- `.drawio` files open and edit in draw.io. To see the brand fonts there, install
  Poppins and Fira Code from `brand/fonts/` (Urbanist must be installed too).
- PNGs are rendered with headless Chrome; draw.io's CLI can't load fonts that aren't installed,
  so the draw.io pieces are exported to SVG, get the fonts injected, then rendered.

`brand/` holds copies of the fonts, icons and logo mark from Brand-Identity-Media.
