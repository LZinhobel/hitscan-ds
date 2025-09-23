<script lang="ts">
  import { onMount, onDestroy } from "svelte";

  type Camera = { deviceId: string; label: string; stream?: MediaStream };

  let cameras: Camera[] = [];
  let selectedIndex: number | null = null;
  let videoElement: HTMLVideoElement | null = null;
  let canvasElement: HTMLCanvasElement | null = null;
  let ctx: CanvasRenderingContext2D | null = null;

  // Dartboard calibration
  const NUM_RINGS = 6;
  let rings: Array<{
    x: number;
    y: number;
    radius: number;
    scaleX: number;
    scaleY: number;
  }> = [];
  let currentRing = 0;

  // Sector lines
  const NUM_SECTORS = 20;
  let lineRotation = 0;
  let lineOffsetX = 0;
  let lineOffsetY = 0;
  let lineScale = 1;
  let lineStretchX = 1;
  let lineStretchY = 1;
  let mode: "rings" | "lines" = "rings";

  // --- Camera functions (browser-only) ---
  async function requestPermission() {
    if (typeof navigator === "undefined") return; // ✅ guard
    try {
      const tempStream = await navigator.mediaDevices.getUserMedia({
        video: true,
      });
      tempStream.getTracks().forEach((t) => t.stop());
    } catch {
      console.warn("Permission denied");
    }
  }

  async function loadCameras() {
    if (typeof navigator === "undefined") return; // ✅ guard
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter(
      (d) => d.kind === "videoinput"
    );
    cameras = devices.map((d, i) => ({
      deviceId: d.deviceId,
      label: d.label || `Camera ${i + 1}`,
    }));
  }

  async function selectCamera(index: number) {
    if (typeof navigator === "undefined") return; // ✅ guard

    // Stop previous camera
    if (selectedIndex !== null && cameras[selectedIndex]?.stream) {
      cameras[selectedIndex].stream!.getTracks().forEach((t) => t.stop());
    }

    selectedIndex = index;
    const cam = cameras[selectedIndex];
    try {
      cam.stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: cam.deviceId } },
      });
      if (videoElement && cam.stream) {
        videoElement.srcObject = cam.stream;
        videoElement.onloadedmetadata = () => {
          videoElement!.play();
          initRings();
        };
      }
    } catch (err) {
      console.error(err);
      alert(`Cannot open ${cam.label}`);
      selectedIndex = null;
    }
  }

  // --- Initialize rings in center ---
  function initRings() {
    if (!videoElement) return;
    const w = videoElement.videoWidth;
    const h = videoElement.videoHeight;
    rings = Array(NUM_RINGS)
      .fill(0)
      .map((_, i) => ({
        x: w / 2,
        y: h / 2,
        radius: 100 * (1 - i * 0.15),
        scaleX: 1,
        scaleY: 1,
      }));
    currentRing = 0;
    draw();
  }

  // --- Draw everything ---
  const MOVE_STEP = 1;
  const SCALE_STEP = 1;
  const STRETCH_STEP = 0.01;
  const ROTATE_STEP = 1;

  function draw() {
    if (!canvasElement || !ctx || !videoElement) return;

    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);

    // Draw rings
    rings.forEach((r, i) => {
      if (i <= currentRing) {
        ctx.beginPath();
        ctx.ellipse(
          r.x,
          r.y,
          r.radius * r.scaleX,
          r.radius * r.scaleY,
          0,
          0,
          2 * Math.PI
        );
        ctx.strokeStyle =
          i === currentRing && mode === "rings" ? "lime" : "white";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });

    // Draw sector lines only in line mode
    if (mode === "lines") {
      const outer = rings[0];
      const radius =
        outer.radius * Math.max(outer.scaleX, outer.scaleY) * lineScale;
      for (let i = 0; i < NUM_SECTORS; i++) {
        const angle =
          (((i * 360) / NUM_SECTORS + lineRotation) * Math.PI) / 180;
        const x =
          outer.x + radius * Math.cos(angle) * lineStretchX + lineOffsetX;
        const y =
          outer.y + radius * Math.sin(angle) * lineStretchY + lineOffsetY;
        ctx.beginPath();
        ctx.moveTo(outer.x + lineOffsetX, outer.y + lineOffsetY);
        ctx.lineTo(x, y);
        ctx.strokeStyle = i === 0 ? "red" : "blue";
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }
  }

  function handleKey(e: KeyboardEvent) {
    if (!rings[currentRing]) return;
    const r = rings[currentRing];

    if (mode === "rings") {
      switch (e.key) {
        case "w":
          r.y -= MOVE_STEP;
          break;
        case "s":
          r.y += MOVE_STEP;
          break;
        case "a":
          r.x -= MOVE_STEP;
          break;
        case "d":
          r.x += MOVE_STEP;
          break;
        case "+":
        case "=":
          r.radius += SCALE_STEP;
          break;
        case "-":
          r.radius = Math.max(10, r.radius - SCALE_STEP);
          break;
        case "i":
          r.scaleY += STRETCH_STEP;
          break;
        case "k":
          r.scaleY = Math.max(0.1, r.scaleY - STRETCH_STEP);
          break;
        case "j":
          r.scaleX = Math.max(0.1, r.scaleX - STRETCH_STEP);
          break;
        case "l":
          r.scaleX += STRETCH_STEP;
          break;
        case "n":
          currentRing++;
          if (currentRing >= NUM_RINGS) {
            console.log("Calibration done:", rings, "Line config:", {
              lineRotation,
              lineOffsetX,
              lineOffsetY,
              lineScale,
              lineStretchX,
              lineStretchY,
            });
            currentRing = NUM_RINGS - 1;
            mode = "lines";
          }
          break;
      }
    } else if (mode === "lines") {
      switch (e.key) {
        case "a":
          lineOffsetX -= MOVE_STEP;
          break;
        case "d":
          lineOffsetX += MOVE_STEP;
          break;
        case "w":
          lineOffsetY -= MOVE_STEP;
          break;
        case "s":
          lineOffsetY += MOVE_STEP;
          break;
        case "i":
          lineStretchY += STRETCH_STEP;
          break;
        case "k":
          lineStretchY = Math.max(0.1, lineStretchY - STRETCH_STEP);
          break;
        case "j":
          lineStretchX = Math.max(0.1, lineStretchX - STRETCH_STEP);
          break;
        case "l":
          lineStretchX += STRETCH_STEP;
          break;
        case "r":
          lineRotation -= ROTATE_STEP;
          break;
        case "t":
          lineRotation += ROTATE_STEP;
          break;
        case "+":
        case "=":
          lineScale += STRETCH_STEP;
          break;
        case "-":
          lineScale = Math.max(0.1, lineScale - STRETCH_STEP);
          break;
        case "n":
          console.log("Calibration finished:", rings, {
            lineRotation,
            lineOffsetX,
            lineOffsetY,
            lineScale,
            lineStretchX,
            lineStretchY,
          });
          break;
      }
    }

    draw();
  }

  // --- Lifecycle ---
  onMount(async () => {
    if (typeof window === "undefined") return;
    await requestPermission();
    await loadCameras();
    window.addEventListener("keydown", handleKey);
  });

  onDestroy(() => {
    if (typeof window === "undefined") return;
    window.removeEventListener("keydown", handleKey);
    cameras.forEach((c) => c.stream?.getTracks().forEach((t) => t.stop()));
  });

  // --- Reactive ctx initialization ---
  $: if (canvasElement && !ctx) {
    ctx = canvasElement.getContext("2d");
    draw();
  }
</script>

<div id="compBody">
  <div id="row">
    <div class="camera-buttons">
      {#each cameras as cam, i (cam.deviceId)}
        <button
          type="button"
          class:selected={i === selectedIndex}
          on:click={() => selectCamera(i)}>{cam.label}</button
        >
      {/each}
    </div>

    <div class="camera-container" style="position:relative;">
      {#if selectedIndex !== null}
        <video autoplay playsinline muted bind:this={videoElement}></video>
        <canvas
          bind:this={canvasElement}
          style="position:absolute;top:0;left:0;width:100%;height:100%;"
        ></canvas>
      {/if}
    </div>
  </div>
</div>

<style>
  .camera-buttons {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    flex-wrap: wrap;
  }
  .camera-buttons button {
    cursor: pointer;
    border-radius: 6px;
    border: 2px solid #000;
    background: #862b52;
    color: #fff;
    height: 100%;
    margin-right: 10%;
    margin-bottom: 3vh;
  }
  #row {
    display: flex;
    flex-direction: row;
    margin: none;
  }
  .camera-buttons button:hover {
    background: #af376b;
  }
  .camera-buttons button.selected {
    height: 15%;
    margin-bottom: 5%;
    color: black;
    background: #db4888;
  }
  .camera-container video,
  .camera-container canvas {
    max-width: 800px;
    height: auto;
    display: block;
  }
  h2,
  h3 {
    color: white;
    text-align: center;
    font-family: "Roboto", sans-serif;
  }

  h2 {
    font-size: 30px;
  }

  h3 {
    font-size: 20px;
  }

  #compBody{
    height:45vh;
    margin-bottom:5vh;
  }
</style>
