<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { rulesState } from "../stores/rulesStore.svelte";
  import calibrationStore, {
    setCalibration,
  } from "../stores/calibrationStore.svelte";
  import { get } from "svelte/store";

  type Camera = { deviceId: string; label: string; stream?: MediaStream };

  let cameras: Camera[] = [];
  let selectedIndex: number | null = null;
  let videoElement: HTMLVideoElement | null = null;
  let canvasElement: HTMLCanvasElement | null = null;
  let ctx: CanvasRenderingContext2D | null = null;
  let stream: MediaStream | null = null;
  let isLoaded = false;
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

  let MOVE_STEP = 1;
  let SCALE_STEP = 1;
  let STRETCH_STEP = 0.01;
  let ROTATE_STEP = 1;

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
      (d) => d.kind === "videoinput"
    );
    cameras = devices.map((d, i) => ({
      deviceId: d.deviceId,
      label: d.label || `Camera ${i + 1}`,
    }));
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      stream = null;
    }
    if (videoElement) {
      videoElement.srcObject = null;
    }
  }

  async function selectCamera(index: number) {
    if (typeof navigator === "undefined") return;

    if (stream) stopCamera();

    selectedIndex = index;
    const cam = cameras[selectedIndex];

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: cam.deviceId } },
      });
      cam.stream = stream;

      if (videoElement && stream) {
        videoElement.srcObject = stream;
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

  function initRings() {
    if (!videoElement) return;
    const w = videoElement.videoWidth;
    const h = videoElement.videoHeight;

    const stored = get(calibrationStore);

    if (stored?.rings?.length === NUM_RINGS) {
      rings = stored.rings.map((r) => ({ ...r }));
      lineRotation = stored.lines.rotation;
      lineOffsetX = stored.lines.offsetX;
      lineOffsetY = stored.lines.offsetY;
      lineScale = stored.lines.scale;
      lineStretchX = stored.lines.stretchX;
      lineStretchY = stored.lines.stretchY;

      currentRing = 0;
      mode = "rings";
      isLoaded = true;
      draw();
      return;
    }

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
    mode = "rings";
    draw();
  }

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
          2 * Math.PI
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
            if (!isLoaded) {
              next.x = r.x;
              next.y = r.y;
              next.scaleX = r.scaleX;
              next.scaleY = r.scaleY;
            }
            currentRing++;
          } else {
            const last = rings[rings.length - 1];
            lineStretchX = last.scaleX;
            lineStretchY = last.scaleY;
            mode = "lines";
          }
          break;
      }
    } else {
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

  async function exportCalibration() {
    stopCamera();
    const data = {
      rings: rings.map((r) => ({ ...r })),
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
    rulesState.isCalibrated = true;
    console.log("Calibration saved", data);
    await fetch("http://127.0.0.1:5000/calibrate", {
      method: "POST",
      body: JSON.stringify(data),
    });

    if (videoElement) videoElement.style.display = "none";
    if (canvasElement) canvasElement.style.display = "none";
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
    stopCamera();
  });

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
          on:click={() => selectCamera(i)}
        >
          {cam.label}
        </button>
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
      <p>W/A/S/D Move</p>
      <p>Shift increases speed</p>
      <p>I/J/K/L Stretch</p>
      <p>Q/E Scale Ring / Rotate Lines</p>
      <p>+/- Scale Lines</p>
      <p>R Next / Save Calibration</p>
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
    background-color: #733636;
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
    background: #733636;
    color: #fff;
    height: 6vh;
    margin-right: 10%;
    margin-bottom: 3vh;
  }
  .camera-buttons button:hover {
    background: #c35757;
  }
  .camera-buttons button.selected {
    height: 10%;
    max-height: 10vh;
    max-width: 10vw;
    margin-bottom: 5%;
    color: black;
    background: #cdaaaa;
  }
  #row {
    display: flex;
    flex-direction: row;
  }
  .camera-container video,
  .camera-container canvas {
    max-width: 800px;
    height: auto;
    display: block;
    object-fit: contain;
  }
</style>
