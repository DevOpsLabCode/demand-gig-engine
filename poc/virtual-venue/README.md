# Virtual Venue POC

This is the first isolated proof of concept for the Open Concert Network / VibesMeet digital-twin venue idea.

## What this POC proves

1. A venue can be represented as an explorable browser-based 3D room.
2. A visitor can move through the room or jump directly to a virtual seat.
3. A real camera feed can be rendered on the virtual stage in real time.
4. A Gaussian-splat scene can be rendered in the browser.
5. A phone video or image set can be turned into a browser-deliverable `.sog` asset using an open reconstruction pipeline.

This is deliberately **not** the finished metaverse product. It is the smallest useful experiment that validates the technical chain before we add avatars, street reconstruction, ticketing, multiplayer rooms, spatial audio, live AWS IVS delivery, or venue self-service onboarding.

## Files

- `index.html` — synthetic club room, virtual seats, first-person movement and live-stage controls.
- `walk-controls.mjs` — WASD / arrow-key and mouse-look controller.
- `live-stage.mjs` — turns a webcam or local video into a PlayCanvas video texture on the stage screen.
- `main.mjs` — UI wiring, seat viewpoints and media-device handling.
- `splat.html` — standalone Gaussian-splat rendering proof. It currently uses PlayCanvas's public toy sample until the first venue scan is produced.
- `reconstruct.sh` — video/images → Nerfstudio/COLMAP → Splatfacto → PLY → PlayCanvas SOG.

## Run the browser POC

The browser will block module imports and camera access if the files are opened directly from disk. Serve the directory over HTTP.

```bash
cd poc/virtual-venue
python3 -m http.server 8080
```

Then open `http://localhost:8080/`.

### Controls

- `WASD` or arrow keys: move.
- Click the 3D scene: capture the pointer and use mouse look.
- `Esc`: release the pointer.
- Use the four seat buttons to jump to predetermined virtual viewpoints.
- **Use my camera as live stage**: grants camera/microphone access and puts that live browser camera on the stage screen.
- **Play a video file on stage**: uses a local video file as the stage source without uploading it.

For production the stage source will be an authenticated live stream, likely Amazon IVS or an equivalent low-latency service. The webcam flow exists only to prove the real-world-video → virtual-stage connection with zero infrastructure.

## Produce the first real venue twin

### Capture

For the first POC, capture one cooperative venue while it is empty.

Recommended capture pattern:

- Use normal perspective video or still photographs for the first test.
- Walk slowly around the perimeter and then through the center.
- Keep substantial visual overlap between neighboring views.
- Capture the stage, bar, entrances, walls, ceiling details, tables and seating from more than one angle.
- Avoid rapidly changing exposure, moving crowds and large featureless/reflective areas when possible.
- Do a second pass at a different camera height when practical.

The first target should be **one room**, not an entire street. Once this works reliably, the same pipeline can process block-sized capture segments and combine them into the Greenwich Village corridor.

### Reconstruction dependencies

The script expects:

- NVIDIA/CUDA-capable environment suitable for Nerfstudio Splatfacto training.
- Nerfstudio (`ns-process-data`, `ns-train`, `ns-export`).
- COLMAP, as used by Nerfstudio for ordinary image/video camera-pose estimation.
- PlayCanvas SplatTransform.

Install SplatTransform:

```bash
npm install -g @playcanvas/splat-transform
```

Consult current Nerfstudio installation documentation for the GPU environment rather than pinning CUDA/PyTorch versions in this POC.

### Run

Video:

```bash
bash ./reconstruct.sh ./capture/venue-walkthrough.mp4 ./work/venue-001
```

Still-image directory:

```bash
bash ./reconstruct.sh ./capture/photos ./work/venue-001
```

The last step produces:

```text
./work/venue-001/web/venue.sog
```

Copy the generated `venue.sog` beside `splat.html` and change:

```html
<pc-asset id="venue" src="https://developer.playcanvas.com/assets/toy-cat.sog"></pc-asset>
```

to:

```html
<pc-asset id="venue" src="./venue.sog"></pc-asset>
```

The `splat.html` transforms will almost certainly need position/rotation/scale adjustment for the first capture. That is expected in this POC. We should persist those transforms as venue metadata in the next iteration.

## POC acceptance criteria

The experiment is successful when all of the following can be demonstrated in one browser session:

- The visitor can enter and navigate a club-shaped 3D room.
- At least four virtual seat viewpoints work.
- A webcam or supplied video visibly plays on the virtual stage.
- A real captured room can be exported to `.sog` and opened in `splat.html`.
- The real-room splat can be aligned well enough that a stage position and one or more seat positions can be identified.
- No restricted third-party imagery is needed to produce the venue asset.

## Immediately after the first scan works

The second POC iteration should merge the two demos: render the real venue splat as the visual layer while retaining an invisible/simplified collision and interaction layer for walking, seats and stage anchors. Then add:

1. Venue metadata (`venue.json`) for spawn point, stage plane, seat transforms and rights provenance.
2. S3/CloudFront hosting for `.sog` assets.
3. An authenticated live-stream URL instead of webcam-only input.
4. A tiny backend model for `VenueTwin`, `TwinAsset`, `SeatAnchor` and `StageStream`.
5. Capture upload + asynchronous reconstruction jobs.
6. A provenance record for every capture and generated twin.

That hybrid is the real product architecture: **photoreal reality layer + game/interaction layer + live-media layer + commerce layer**.
