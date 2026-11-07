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

**Vision** (`src/vision.py`, one folder per theme in `out/vision/`). The first things to know about cameras
and computer vision, kept as quiet as the minimal set: one word, one drawing, one formula.

| Theme | Poster | Idea |
| --- | --- | --- |
| camera | pinhole. | a box with a hole: rays cross and land upside down, x = f·X/Z |
| camera | lens. | three rays from one point meet again behind a thin lens: 1/f = 1/u + 1/v |
| camera | zoom. | one 36 mm sensor behind 24 mm and 85 mm lenses: 74° vs 24° field of view |
| camera | intrinsic. | the camera matrix K: origin top-left, principal point (cx, cy), fx and fy in pixels |
| camera | distort. | a straight grid pulled into a barrel by x(1 + k1·r² + k2·r⁴) |
| camera | fisheye. | where a ray at θ lands: pinhole f·tan θ runs off to infinity, fisheye f·θ stays on the sensor |
| shutter | rolling. | rows read one after another: a moving bar leans, exposures staircase in time |
| shutter | global. | every row exposed at the same instant: the bar stays straight |
| shutter | expose. | f/1.4 at 1/1000 to f/8 at 1/30: half the aperture area, twice the time, same light |
| shutter | blur. | a dot at 12 000 px/s smears 12, 48 and 200 px at 1/1000, 1/250 and 1/60 s |
| geometry | ray. | back-projection: one pixel is a ray, every depth along it lands on the same pixel |
| geometry | size. | twice as far, half as tall: know the size H, measure h, get Z = f·H/h |
| geometry | pose. | the camera t away from the world origin, turned by R: X_cam = R·X_world + t |
| geometry | disparity. | two cameras a baseline apart see one point shifted by d: Z = f·B/d |
| geometry | vanish. | rails and a line of poles, projected: parallel lines all end at one point on the horizon |
| geometry | homography. | a checkerboard seen at an angle, straightened by one 3×3 matrix fitted to its 4 corners |
| geometry | epipolar. | a pixel in the left view is a ray; the right camera sees that ray as a line: x2ᵀ F x1 = 0 |
| image | pixel. | an image is a grid of numbers: a dark disc, its edge pixels part-covered |
| image | bayer. | the RGGB colour filter mosaic: one colour per pixel, half of them green |
| image | edge. | slide [-1, 0, +1] along a row of pixels: the output spikes where the brightness jumps |

**Photogrammetry** (`src/photogrammetry.py`, one folder per pipeline step in `out/photogrammetry/`). Drone photos to a
map, one concept per poster, in the order of the steps in [photogrammetry](https://github.com/ibadrather/photogrammetry):
ingest → select → extract → sfm → georef → dense → dsm → ortho. Numbers come from its Brighton Beach sample run
(18 photos, DJI Phantom 3, 45 m up) unless a poster says simulated.

| Step | Poster | Idea |
| --- | --- | --- |
| ingest | join. | the frame table: images and manifest joined one to one; `set(images) ^ set(manifest)` lists every mismatch |
| ingest | manifest. | the flight from above before anything runs: one GeoJSON Point per photo, `null` for a GPS dropout |
| ingest | early. | fail fast: a bad dataset stops at step 1 in a second, with all three problems listed at once |
| select | footprint. | similar triangles: a nadir frame at 45 m sees W = H·s/f = 43 m of ground |
| select | overlap. | keep a frame once its overlap with the last kept one drops to 80 %: 1 − d/W |
| select | gsd. | one pixel's rays fan out to one cell on the ground: H·sw/(f·iw) = 1.9 cm |
| select | thin. | 46 s of video is 1380 frames and 951 510 pairs; 80 % overlap keeps 31 and 465 |
| extract | gop. | video stores few whole frames; decoding frame by frame repeats work (36 decodes), one FFmpeg pass doesn't (16) |
| extract | jpeg. | one 8 × 8 block through the DCT: quality 95 keeps 56 coefficients, quality 25 keeps 13, fine detail first to go |
| extract | shrink. | longest side 1920 px: 4.3× fewer pixels to match, and the focal length scales with them |
| sfm | keypoint. | SIFT blobs at every scale, a circle and an orientation each; the sea gives none |
| sfm | descriptor. | a 16 × 16 patch's gradients binned into 4 × 4 cells of 8 directions: 128 numbers |
| sfm | ratio. | Lowe's ratio test: a rock corner passes at d1/d2 = 0.40, a repeated window fails at 0.94 |
| sfm | pairs. | exhaustive, sequential or spatial: 120, 42 or 36 pairs for the same 16 photos |
| sfm | ransac. | fit two random points, count who agrees, keep the best: 11 tries for a line, 272 for an F-matrix |
| sfm | islands. | the view graph: a textureless band cuts the matches and the flight becomes two models |
| sfm | grow. | incremental mapping: start from two images, add the next by PnP, points coloured by the step that made them |
| sfm | track. | one point followed through six photos, its track length; Brighton's mean is 4.1 |
| sfm | reproject. | the one constraint: a 3D point projected through a camera must land where it was observed |
| sfm | bundle. | bundle adjustment: 6 cameras, 15 points, 52 rays, one least-squares problem |
| sfm | robust. | squared error lets a 5 px outlier cost 25; log(1 + r²) caps it at 3.3 |
| sfm | gauge. | the same model shifted, turned and scaled explains the images equally well: 7 numbers left open |
| sfm | focal. | f in pixels: 3.61 / 6.17 × 4000 = 2340, refined by bundle adjustment to 2795 (+19.4 %) |
| sfm | invert. | world-to-camera (R, t) or camera-to-world (Rᵀ, C = −Rᵀt): one pose, the classic bug |
| sfm | dome. | flat ground, camera straight down: a bowl metres off at the edges, with a perfect reprojection error |
| sfm | priors. | loose: images decide the shape, then a 7-number fit; tight: GNSS weighted inside bundle adjustment |
| georef | helmert. | the sfm camera centres scaled, turned and shifted onto the GNSS: y = s·R·x + t |
| georef | residual. | reading the residuals: random noise, a time offset along track that flips each strip, a doming bowl |
| georef | offset. | residuals see the noise (0.44 m), not a common GNSS bias (3.6 m) that moves the whole model |
| georef | hinge. | cameras on one straight line: every roll about the line fits, so the fit stops |
| georef | enu. | local east-north-up: flat metres tangent to the Earth at 46.84° N, where a degree of longitude is 76 km |
| georef | utm. | 60 zones of 6°: −91.99° is zone 15, and the scale factor dips to 0.9996 on its centre line |
| georef | datum. | three zeros for height: the takeoff point, the geoid, the ellipsoid (N = −29 m) |
| georef | float. | float32 at a northing of 5 188 000 m steps by 0.5 m: 5188000.3 becomes 5188000.5 |
| dense | undistort. | the sfm lens field over a 4000 × 2250 frame: resample to a pinhole so a patch warps by one homography |
| dense | views. | view selection: 8 neighbours at a useful angle, not ~0° (no depth), not ≫ 40° (unlike patches) |
| dense | depth. | candidate depths along one ray land on the epipolar line; the best NCC is the surface |
| dense | ncc. | a darker copy of a patch scores NCC 1.00, another spot 0.12, though SSD prefers the wrong one |
| dense | propagate. | PatchMatch on a roof: random depths, then neighbours' good guesses spread in one or three sweeps |
| dense | baseline. | σZ = Z²/(f·B)·σd: the same ray error, a long thin depth spread for a short baseline, a tight one for a long |
| dense | agree. | fusion: four depth maps agree and a point is kept; two agree and it's dropped |
| dense | mirror. | water mirrors the shore, so the match lands as far below the surface as the post is tall |
| dsm | median. | a cross-section cut into cells; one outlier moves max all the way, mean a fifth, median not at all |
| dsm | spacing. | the same points gridded at 0.5, 1, 1.5 and 3 × the point spacing, and how many cells each hits |
| dsm | spike. | a cell more than 1 m from all but one neighbour is noise: a spike goes, a roof corner stays |
| dsm | fill. | holes filled by area, not distance: small gaps between points filled, a sand patch and the sea left empty |
| dsm | corner. | pixel-is-area: the origin is the top-left corner, a cell's centre half a cell in |
| dsm | ndsm. | DSM is the top of everything, DTM the bare ground, nDSM = DSM − DTM how tall things are |
| dsm | nmad. | against a reference: remove the median offset, then NMAD, which heavy tails can't pull like RMSE |
| ortho | backward. | run the camera backwards: for each map pixel, a height from the DSM, a projection, a colour |
| ortho | lean. | relief displacement: a camera sees from one point, so a tower's top lands further out and hides the ground |
| ortho | slant. | Δxy = Δz·tan θ: a 10 cm height error moves a colour 1.6 cm at 9°, 7 cm at 35° |
| ortho | ghost. | occlusion: the z-buffer says the wall is nearer, so the ground behind it doesn't get the wall's colour |
| ortho | seams. | each pixel from the most nadir photo: on flat ground, a Voronoi diagram, its edges the seamlines |
| ortho | gain. | auto exposure undone: one gain per photo fitted on the overlaps, 0.63 to 1.48 |
| ortho | blend. | multi-band blending: coarse bands cross the seam over a wide zone, fine bands over a pixel |
| ortho | true. | one building three ways: rectified on a plane, classic on bare ground, true on the DSM with occlusion |

**Still** (`src/still.py`, `out/still/`). Computer vision and photogrammetry at their barest, the minimal
set's rules kept: one word, one drawing, one line of code, from the light coming in to the mesh coming out.

| Poster | Idea |
| --- | --- |
| iris. | a six-blade aperture: the hole is the black paper showing through |
| frame. | a viewfinder: four corners, a centre cross and one dot on a third |
| gray. | R, G and B as bar widths 0.299, 0.587, 0.114, and the one gray bar they make |
| hist. | a two-humped histogram and the Otsu threshold computed in its valley |
| binary. | a ramp of twelve grays, and the same ramp after one threshold |
| smooth. | the 5 × 5 Gaussian kernel as dots, each dot's area its weight |
| sharp. | the same disc out of focus and in focus |
| harris. | a sliding window: flat changes nothing, an edge one way, a corner every way |
| pyramid. | an image pyramid: five levels, each half the size of the last |
| match. | two pictures of one scene, the same points joined across, one bad match |
| checker. | a calibration board at an angle and its 7 × 5 inner corners |
| box. | a detection: one ball, one box, one score |
| segment. | segmentation: every pixel on a grid answers yes or no |
| around. | walk round the object: 24 cameras, one every 15° |
| down. | a nadir photo: one camera straight down, the footprint it sees |
| stitch. | two photos that share a strip, laid over each other |
| cross. | two cameras, two pixel rays, one point where they meet |
| cloud. | a torus of points, nearer ones bigger and brighter: no surface yet |
| mesh. | the points joined into triangles: a bump in a sheet, one face filled |

**Lattice** (`src/lattice.py`, `out/lattice/`). build.'s method as a series: a triangular lattice over the paper,
and a stack of shapes (first match wins) that decides the colour of each triangle's centroid. Nothing else is drawn.

| Poster | Idea |
| --- | --- |
| hi. | a humanoid waving: one arm down, one up, motion arcs by the hand |
| scan. | a one-eyed robot's lidar fan: the wall lights up only inside the beam |
| rover. | six wheels on a rocker-bogie, a mast camera and a high-gain dish, on sand |
| quad. | a quadcopter from above: four rotor discs, each blade at its own angle |
| weld. | an industrial arm at work, a spark of triangles where the torch meets the seam |
| pup. | a robot dog side on: near legs in ink, far legs in grey, knees in teal |
| dive. | an underwater robot with its own light, bubbles rising off the stern |
| sweep. | a robot vacuum inside the Archimedean spiral it cleans along, older passes fading |
| hexa. | a hexapod in a tripod gait: three feet down in ink, three swinging in light |
| crawl. | a tracked robot with a camera mast and a gripper arm |
| launch. | a rocket lifting off a pad of smoke, on black |
| lander. | a lunar lander on grey ground, Earth over the horizon |
| heart. | the heart curve (x² + y² − 1)³ − x²y³ ≤ 0, a heartbeat line running through it |
| owl. | a robot owl on a branch: two lens eyes, ear tufts and a chevron belly |
| chip. | a microcontroller: a die, 24 pins and traces out to vias |
| gear. | two meshing spur gears, 12 teeth turning 8, the teeth a clamped cosine |
| glitch. | a robot face with some lattice rows read late: shifted, with a colour fringe |
| pals. | a tall robot holding the hand of a small round one, a heart between them |
| bloom. | a robot head used as a flower pot, its eyes turned up at what grew |
| astro. | a robot in a space helmet, a ringed planet behind |

**Epic** (`src/epic.py`, `out/epic/`). The opposite of the minimal set: one simulation run out to the edges of the
paper, thousands of marks, every one computed by the line of code printed under it.

| Poster | Idea |
| --- | --- |
| chaos. | the Lorenz attractor: 48 000 RK4 steps of three equations, a path that never repeats |
| explore. | RRT*: 5000 random samples grow a tree through a slalom of walls; rewiring pulls one route straight |
| field. | a potential field: 160 starts on the border pulled to one goal, pushed off nine obstacles |
| swarm. | boids: 160 agents scattered at random find each other with three local rules and fly as one |
| descend. | momentum gradient descent on a three-valley loss: 72 starts, each coloured by the valley it ends in |

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
    vision/<theme>/                 vision.py
    photogrammetry/<step>/          photogrammetry.py
    still/                          still.py
    lattice/                        lattice.py
    epic/                           epic.py
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
uv run --no-project --with fonttools --with brotli python src/vision.py       # out/vision/<theme>/*.svg
uv run --no-project --with fonttools --with brotli python src/photogrammetry.py  # out/photogrammetry/<step>/*.svg
uv run --no-project --with fonttools --with brotli python src/still.py        # out/still/*.svg
uv run --no-project --with fonttools --with brotli python src/lattice.py      # out/lattice/*.svg
uv run --no-project --with fonttools --with brotli python src/epic.py         # out/epic/*.svg
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
