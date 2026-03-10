<script lang="ts">
  import { get } from "svelte/store";
  import Header from "../../comps/Header.svelte";
  import Button from "../../comps/Button.svelte";
  import { playerState } from "../../stores/playerStore.svelte";
  import { rulesState } from "../../stores/rulesStore.svelte";
  import calibrationStore from "../../stores/calibrationStore.svelte";
  import { onMount, onDestroy } from "svelte";
  import { io } from "socket.io-client";

  // ─── Types ───────────────────────────────────────────────────────────────────

  interface Player {
    id: number;
    name: string;
  }

  interface ShotRecord {
    playerIndex: number;
    score: number;
    hitType: "single" | "double" | "triple" | "miss";
    coords: { x: number; y: number };
    hitArrayIndex: number;
    scoreId: number | null;
  }

  // ─── State ───────────────────────────────────────────────────────────────────

  let players: (Player | null)[] = [];
  let gameId: number;

  let currentPlayer = $state(0);
  let shotsThisTurn = 0;
  let playerScoring = [false, false];
  let playerPoints = $state([0, 0]);

  let player1Hits = $state(["", "", ""]);
  let player2Hits = $state(["", "", ""]);

  $inspect(player1Hits)
  $inspect(player2Hits)
  
  let hasWon = $state(0);

  // ─── Canvas ──────────────────────────────────────────────────────────────────

  let canvas: HTMLCanvasElement | null = null;
  let ctx: CanvasRenderingContext2D | null = null;
  let dartboard: HTMLImageElement;
  let hitCords: Array<{ x: number; y: number }> = [];

  const outer = get(calibrationStore)?.rings[0];

  function mapToBoard(hitX: number, hitY: number) {
    if (!outer || !canvas) return { x: hitX, y: hitY };
    const scale = Math.min(canvas.width, canvas.height) / (2 * outer.radius);
    console.log("Drawing at", {
      x: canvas.width / 2 + (hitX - outer.x) * scale,
      y: canvas.height / 2 + (hitY - outer.y) * scale,
    });

    return {
      x: canvas.width / 2 + (hitX - outer.x) * scale,
      y: canvas.height / 2 + (hitY - outer.y) * scale,
    };
  }

  function drawHit(x: number, y: number) {
    const size = 8;
    ctx!.beginPath();
    ctx!.moveTo(x - size, y - size);
    ctx!.lineTo(x + size, y + size);
    ctx!.moveTo(x + size, y - size);
    ctx!.lineTo(x - size, y + size);
    ctx!.stroke();
  }

  function draw() {
    if (!ctx || !dartboard || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(dartboard, 0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "red";
    ctx.lineWidth = 2;
    for (const { x, y } of hitCords) {
      const mapped = mapToBoard(x, y);
      drawHit(mapped.x, mapped.y);
    }
  }

  function clearDartboard() {
    hitCords = [];
    if (!ctx || !canvas || !dartboard) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(dartboard, 0, 0, canvas.width, canvas.height);
  }

  // ─── Score parsing ───────────────────────────────────────────────────────────

  function parseSocketScore(rawScore: string): {
    hitType: "single" | "double" | "triple" | "miss";
    score: number;
  } {
    const match = rawScore.match(/^([SDT])(\d+)$/i);
    if (match) {
      const base = parseInt(match[2]);
      switch (match[1].toUpperCase()) {
        case "S":
          return { hitType: "single", score: base };
        case "D":
          return { hitType: "double", score: base * 2 };
        case "T":
          return { hitType: "triple", score: base * 3 };
      }
    }

    const numeric = parseInt(rawScore);
    if (isNaN(numeric) || numeric === 0) return { hitType: "miss", score: 0 };
    if (numeric === 50) return { hitType: "double", score: 50 };
    return { hitType: "single", score: numeric };
  }

  // ─── Hit display helpers ─────────────────────────────────────────────────────

  function setHit(playerIndex: number, index: number, value: string) {
    if (playerIndex === 0) {
      player1Hits[index] = value;
      player1Hits = player1Hits;
    } else {
      player2Hits[index] = value;
      player2Hits = player2Hits;
    }
  }

  function clearHits(playerIndex: number) {
    if (playerIndex === 0) player1Hits = ["", "", ""];
    else player2Hits = ["", "", ""];
  }

  // ─── Turn logic ──────────────────────────────────────────────────────────────

  function advanceTurn() {
    shotsThisTurn = 0;
    currentPlayer = (currentPlayer + 1) % 2;
  }

  function endTurnAfterBust(playerIndex: number) {
    shotsThisTurn = 0;
    currentPlayer = (playerIndex + 1) % 2;
  }

  // ─── Socket ──────────────────────────────────────────────────────────────────

  let socket: ReturnType<typeof io> | null = null;
  let shotHistory: ShotRecord[] = [];

  function handleDartHit(e: any) {
    try {
      if (shotsThisTurn === 0) {
        clearDartboard();
        if (currentPlayer === 0) {
          clearHits(0);
          clearHits(1);
        }
      }

      hitCords = [...hitCords, e.coords];
      draw();

      const { hitType, score } = parseSocketScore(e.score);

      shotHistory.push({
        playerIndex: currentPlayer,
        score,
        hitType,
        coords: e.coords,
        hitArrayIndex: shotsThisTurn,
        scoreId: null,
      });

      setHit(currentPlayer, shotsThisTurn, e.score);
      subtractPoints(currentPlayer, score, hitType);
    } catch (err) {
      console.error("handleDartHit error:", err);
    }
  }

  // ─── Scoring ─────────────────────────────────────────────────────────────────

  async function subtractPoints(
    playerIndex: number,
    score: number,
    hitType: "single" | "double" | "triple" | "miss",
  ) {
    if (isNaN(score) || score > 60 || score < 0) return;

    if (rulesState.variant === "double-in" && !playerScoring[playerIndex]) {
      if (hitType !== "double") {
        endTurnAfterBust(playerIndex);
        return;
      }
      playerScoring[playerIndex] = true;
    }

    const remaining = playerPoints[playerIndex] - score;

    if (
      rulesState.variant === "double-out" &&
      remaining === 0 &&
      hitType !== "double"
    ) {
      endTurnAfterBust(playerIndex);
      return;
    }

    if (remaining < 0) {
      endTurnAfterBust(playerIndex);
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/score/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player: players[playerIndex]?.id,
          game: gameId,
          score,
        }),
      });

      if (!res.ok) {
        console.error("Failed to post score", res.status, await res.text());
        return;
      }

      const updated = await res.json();
      playerPoints[playerIndex] = updated.score;
      shotHistory[shotHistory.length - 1].scoreId = updated.id;

      shotsThisTurn++;
      if (shotsThisTurn >= 3) advanceTurn();

      checkWinner();
    } catch (err) {
      console.error("Error posting score:", err);
    }
  }

  async function undoLastShot() {
    const last = shotHistory.pop();
    if (!last) return;

    hitCords = hitCords.filter((c) => c !== last.coords);
    draw();

    setHit(last.playerIndex, last.hitArrayIndex, "");

    if (last.scoreId !== null) {
      try {
        const res = await fetch(`http://localhost:8000/score/${last.scoreId}`, {
          method: "DELETE",
        });
        if (res.ok) {
          const updated = await res.json();
          playerPoints[0] = updated.player1Score;
          playerPoints[1] = updated.player2Score;
        } else {
          console.error("Failed to delete score", res.status);
        }
      } catch (err) {
        console.error("Error deleting score:", err);
      }
    }

    currentPlayer = last.playerIndex;
    shotsThisTurn = last.hitArrayIndex;

    hasWon = 0;
  }

  async function checkWinner() {
    const winnerIndex =
      playerPoints[0] === 0 ? 0 : playerPoints[1] === 0 ? 1 : -1;
    if (winnerIndex === -1) return;

    hasWon = winnerIndex + 1;

    try {
      await fetch("http://localhost:8000/games/setWinner", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gameId, winnerId: players[winnerIndex]!.id }),
      });
    } catch (err) {
      console.error("Error setting winner:", err);
    }

    fetch("http://localhost:5000/close_camera");
    socket?.off("dart_hit");
  }

  function restartGame() {}

  // ─── Lifecycle ───────────────────────────────────────────────────────────────

  onMount(async () => {
    socket = io("http://localhost:5000", {
      transports: ["websocket"],
      reconnection: true,
    });
    socket.on("dart_hit", handleDartHit);

    players = playerState.getPlainPlayers();

    try {
      const res = await fetch("http://localhost:8000/game/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player1: players[0]?.id,
          player2: players[1]?.id,
          version: rulesState.ruleset,
        }),
      });

      if (!res.ok) {
        console.error("Failed creating game", res.status, await res.text());
      } else {
        const game = await res.json();
        gameId = game.gameId;
        playerPoints = [game.player1Score, game.player2Score];
      }
    } catch (err) {
      console.error("Error creating game:", err);
    }

    const initCanvas = () => {
      if (!canvas || !dartboard) return;
      canvas.width = dartboard.width;
      canvas.height = dartboard.height;
      ctx = canvas.getContext("2d");
      draw();
    };

    dartboard.onload = initCanvas;
    if (dartboard?.complete) initCanvas();
  });

  onDestroy(() => {
    socket?.off("dart_hit", handleDartHit);
    socket?.disconnect();
    socket = null;
  });
</script>

<Header />
<section>
  {#if hasWon !== 0}
    <div id="overlay">
      <div id="winBox">
        <h1>{$playerState.players[hasWon - 1]?.name} has Won</h1>
        <div id="buttonRow">
          <a href="/"><Button text="Home" /></a>
          <a onclick={() => restartGame()}><Button text="Restart" /></a>
        </div>
      </div>
    </div>
  {/if}

  <div id="pointView">
    <h1>
      {hasWon !== 0
        ? `${$playerState.players[hasWon - 1]?.name} has Won`
        : `${$playerState.players[currentPlayer]?.name}'s Turn`}
    </h1>

    <div id="boardControls">
      <button onclick={undoLastShot} disabled={hasWon !== 0}
        >Undo Last Shot</button
      >
    </div>

    {#each [{ hits: player1Hits, index: 0 }, { hits: player2Hits, index: 1 }] as { hits, index }}
      <div class="pointsBox">
        <h2>{$playerState.players[index]?.name}</h2>
        <div class="hitsBox">
          {#each hits as hit}
            <div class="hit">
              {#if hit === "0"}
                <p style="color:red">X</p>
              {:else if hit !== ""}
                <p>{hit}</p>
              {/if}
            </div>
          {/each}
        </div>
        <div class="titleBox" id="ptsBox"><p>{playerPoints[index]}</p></div>
      </div>
    {/each}
  </div>

  <div id="boardView">
    <img bind:this={dartboard} src="/dartboard.png" alt="dartboard" hidden />
    <canvas bind:this={canvas}></canvas>
  </div>
</section>

<style>
  @import url("https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap");

  section {
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: center;
    background-color: #000;
    margin: 0;
    height: 100vh;
    overflow: hidden;
  }

  h1 {
    font-family: "Roboto", sans-serif;
    color: #eeecec;
    font-size: 50px;
    font-weight: 700;
  }

  h2 {
    font-family: "Nova Flat", system-ui;
    color: #eeecec;
    font-size: 36px;
    grid-area: 1/1/2/3;
    height: 100%;
    margin: 5%;
  }

  p {
    font-family: "Roboto", sans-serif;
    font-weight: 700;
    vertical-align: center;
    margin: 0;
    font-size: 50px;
    color: #000;
  }

  .hitsBox {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    grid-area: 2/2/3/5;
  }

  .hit {
    height: 60%;
    width: 30%;
    justify-content: center;
    vertical-align: middle;
    background-color: #d9d9d9;
    border-radius: 8px;
  }

  .hit p {
    text-align: center;
    font-family: "Roboto", sans-serif;
    color: black;
    font-size: 40px;
    margin: 0;
  }

  .titleBox {
    display: flex;
    justify-content: center;
    height: 4vh;
    border-radius: 8px;
    background-color: #d9d9d9;
  }

  #ptsBox {
    height: 100%;
    width: 100%;
    padding-top: 40%;
    margin-right: 50%;
    grid-area: 2/6/3/7;
  }

  #pointView {
    display: flex;
    flex-direction: column;
    height: 80%;
    width: 40%;
  }

  #boardView {
    position: relative;
    width: 40%;
    height: 60%;
    margin-left: 10%;
  }

  canvas {
    width: 100%;
    height: 100%;
    position: absolute;
  }

  img {
    position: absolute;
  }

  .pointsBox {
    background-color: #733636;
    height: 30%;
    margin-bottom: 10%;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
    grid-template-rows: 1fr 1fr 1fr 1fr;
  }

  #boardControls {
    margin-top: 10px;
    text-align: center;
  }

  #boardControls button {
    padding: 10px 20px;
    font-size: 16px;
    font-weight: bold;
    border-radius: 6px;
    background-color: #733636;
    color: #fff;
    border: none;
    cursor: pointer;
    margin-bottom: 3vh;
  }

  #boardControls button:hover {
    background-color: #c35757;
  }

  #overlay {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(6px);
    background-color: rgba(0, 0, 0, 0.4);
    z-index: 10;
  }

  #winBox {
    text-align: center;
    display: flex;
    flex-direction: column;
    width: 60vw;
    height: 40vh;
    background-color: #000000;
    border-radius: 10px;
    border: 2px solid #fff;
  }

  #buttonRow {
    display: flex;
    flex-direction: row;
    justify-content: space-evenly;
    margin-top: 10vh;
  }
</style>
