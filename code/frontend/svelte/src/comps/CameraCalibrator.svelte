<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { rulesState } from "../stores/rulesStore.svelte";
  import calibrationStore, {
    setCalibration,
  } from "../stores/calibrationStore.svelte";

  type Camera = { deviceId: string; label: string; stream?: MediaStream };

  let cameras: Camera[] = [];
  let selectedIndex: number | null = null;
  let videoElement: HTMLVideoElement | null = null;
  let canvasElement: HTMLCanvasElement | null = null;
  let ctx: CanvasRenderingContext2D | null = null;

  // TODO: Load saved Calibration from Backend, Just pick the selected frontend index fuck the inconsistency

  const NUM_RINGS = 6;
  let rings: Array<{
    x: number;
    y: number;
    radius: number;
    scaleX: number;
    scaleY: number;
  }> = [];
  let currentRing = 0;

  const NUM_SECTORS = 20;
  let lineRotation = 0;
  let lineOffsetX = 0;
  let lineOffsetY = 0;
  let lineScale = 1;
  let lineStretchX = 1;
  let lineStretchY = 1;
  let mode: "rings" | "lines" = "rings";

  async function requestPermission() {
    if (typeof navigator === "undefined") return;
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
    if (typeof navigator === "undefined") return;
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter(
      (d) => d.kind === "videoinput",
    );
    cameras = devices.map((d, i) => ({
      deviceId: d.deviceId,
      label: d.label || `Camera ${i + 1}`,
    }));
  }

  async function selectCamera(index: number) {
    if (typeof navigator === "undefined") return;
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

  // --- Initialize rings (inherit from previous) ---
  function initRings() {
    if (!videoElement) return;
    const w = videoElement.videoWidth;
    const h = videoElement.videoHeight;

    rings = [];
    for (let i = 0; i < NUM_RINGS; i++) {
      if (i === 0) {
        rings.push({ x: w / 2, y: h / 2, radius: 100, scaleX: 1, scaleY: 1 });
      } else {
        const prev = rings[i - 1];
        rings.push({
          x: prev.x,
          y: prev.y,
          radius: prev.radius * 0.85,
          scaleX: prev.scaleX,
          scaleY: prev.scaleY,
        });
      }
    }

    currentRing = 0;
    draw();
  }

  let MOVE_STEP = 1;
  let SCALE_STEP = 1;
  let STRETCH_STEP = 0.01;
  let ROTATE_STEP = 1;

  function draw() {
    if (!canvasElement || !ctx || !videoElement) return;

    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);

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
          2 * Math.PI,
        );
        ctx.strokeStyle =
          i === currentRing && mode === "rings" ? "lime" : "white";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    });

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

  // --- Keyboard input ---
  function handleKey(e: KeyboardEvent) {
    if (mode === "rings" && !rings[currentRing]) return;
    const r = rings[currentRing];
    let key = e.key;
    let fast = false;

    if (key === key.toUpperCase()) {
      key = key.toLowerCase();
      fast = true;
    }

    MOVE_STEP = fast ? 3 : 1;

    if (mode === "rings") {
      switch (key) {
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
        case "e":
        case "+":
        case "=":
          r.radius += SCALE_STEP;
          break;
        case "q":
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
        case "r":
          if (currentRing + 1 < NUM_RINGS) {
            const next = rings[currentRing + 1];
            next.x = r.x;
            next.y = r.y;
            next.scaleX = r.scaleX;
            next.scaleY = r.scaleY;
            currentRing++;
          } else {
            // When switching to line mode, inherit ring stretch
            const lastRing = rings[rings.length - 1];
            lineStretchX = lastRing.scaleX;
            lineStretchY = lastRing.scaleY;
            mode = "lines";
            console.log("Rings done, switching to lines (stretch inherited)");
          }
          break;
      }
    } else if (mode === "lines") {
      switch (key) {
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
        case "q":
          lineRotation -= ROTATE_STEP;
          break;
        case "e":
          lineRotation += ROTATE_STEP;
          break;
        case "+":
        case "=":
          lineScale += STRETCH_STEP;
          break;
        case "-":
          lineScale = Math.max(0.1, lineScale - STRETCH_STEP);
          break;
        case "r":
          exportCalibration();
          break;
      }
    }

    draw();
  }

  onMount(async () => {
    if (typeof window === "undefined") return;
    await requestPermission();
    await loadCameras();
    rulesState.isCalibrated = false;
    window.addEventListener("keydown", handleKey);
  });

  onDestroy(() => {
    if (typeof window === "undefined") return;
    window.removeEventListener("keydown", handleKey);
    cameras.forEach((c) => c.stream?.getTracks().forEach((t) => t.stop()));
  });

  $: if (canvasElement && !ctx) {
    ctx = canvasElement.getContext("2d");
    draw();
  }

  async function exportCalibration() {
    const data = {
      rings: rings.map((r) => ({
        x: r.x,
        y: r.y,
        radius: r.radius,
        scaleX: r.scaleX,
        scaleY: r.scaleY,
      })),
      lines: {
        rotation: lineRotation,
        offsetX: lineOffsetX,
        offsetY: lineOffsetY,
        scale: lineScale,
        stretchX: lineStretchX,
        stretchY: lineStretchY,
      },
    };

    setCalibration(data);
    console.log(data);


    const json = JSON.stringify(data, null, 2);
    rulesState.isCalibrated = true;

    const response = await fetch("http://127.0.0.1:5000/calibrate", {
      method: "POST",
      body: json,
    });

    console.log(response);
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

    <div id="controls">
      <p>W/A/S/D - Move Element</p>
      <p>Shift + W/A/S/D - Move Element Faster</p>
      <p>I/J/K/L - Stretch Element</p>
      <p>Q/E - Scale Ring/Rotate Lines</p>
      <p>+/- - Scale Lines</p>
      <p>R - Next Element</p>
    </div>
  </div>
</div>

<style>
  #compBody {
    height: 45vh;
    margin-bottom: 10vh;
  }

  #controls {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    width: 18vw;
    height: 48vh;
    margin-left: 3vw;
    background-color: rgba(220, 161, 186, 0.6);
    padding: 1vh 1vw;
  }

  p {
    color: #d6d6d6;
  }

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
    height: 6vh;
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
    height: 10%;
    max-height: 10vh;
    max-width: 10vw;
    margin-bottom: 5%;
    color: black;
    background: #db4888;
  }
  .camera-container video,
  .camera-container canvas {
    max-width: 800px;
    height: auto;
    display: block;
    object-fit: contain;
  }
</style>
