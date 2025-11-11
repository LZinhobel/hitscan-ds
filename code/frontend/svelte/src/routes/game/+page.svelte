<script lang="ts">
  import { get, writable } from "svelte/store";
  import Header from "../../comps/Header.svelte";
  import { playerState } from "../../stores/playerStore.svelte";
  import Button from "../../comps/Button.svelte";
  import { onMount, onDestroy } from "svelte";
  import { rulesState } from "../../stores/rulesStore.svelte";
  import { io } from "socket.io-client";
  import calibrationStore from "../../stores/calibrationStore.svelte";

  interface Player {
    id: number;
    name: string;
  }

  let players: (Player | null)[] = [];
  let gameId: number;

  let currentPlayer = 0;
  let shotsThisTurn = 0;
  let playerScoring = [false, false];
  let playerPoints = [0, 0];

  let player1Hits = ["", "", ""];
  let player2Hits = ["", "", ""];

  let hasWon = writable(0);

  let socket: ReturnType<typeof io> | null = null;

  let canvas: HTMLCanvasElement | null = null;
  let ctx: CanvasRenderingContext2D | null = null;
  let dartboard: HTMLImageElement;

   let outer = null;
   $: outer = get(calibrationStore)?.rings?.[0];

  let hitCords: Array<{ x: number; y: number }> = [];

let shotHistory: Array<{
  playerIndex: number;
  score: number;
  hitType: "single" | "double" | "triple" | "miss";
  coords: { x: number; y: number };
  hitArrayIndex: number;
  applied: boolean; // true if points were subtracted
}> = [];


function undoLastShot() {
  const lastShot = shotHistory.pop();
  if (!lastShot) return;

  const { playerIndex, score, coords, hitArrayIndex, applied } = lastShot;

  // Remove coords
  hitCords = hitCords.filter((c) => c !== coords);
  draw();

  // Clear hit from player hits array
  if (playerIndex === 0) {
    const copy = [...player1Hits];
    copy[hitArrayIndex] = "";
    player1Hits = copy;
  } else {
    const copy = [...player2Hits];
    copy[hitArrayIndex] = "";
    player2Hits = copy;
  }

  // Only restore points if shot was applied
  if (applied) {
    playerPoints[playerIndex] += score;
  }

  // Adjust turn and shot counter
  if (shotsThisTurn === 0) {
    currentPlayer = playerIndex;
    shotsThisTurn = 2;
  } else {
    shotsThisTurn--;
  }

  hasWon.set(0); // reset winner if undo happened
}


  function parseSocketScore(rawScore: string): {
    hitType: "single" | "double" | "triple" | "miss";
    score: number;
  } {
    let hitType: "single" | "double" | "triple" | "miss" = "miss";
    let score = 0;

    if (typeof rawScore === "string") {
      const match = rawScore.match(/^([SDT])(\d+)$/i);
      if (match) {
        const [, letter, numStr] = match;
        const base = parseInt(numStr);
        switch (letter.toUpperCase()) {
          case "S":
            hitType = "single";
            score = base;
            break;
          case "D":
            hitType = "double";
            score = 2 * base;
            break;
          case "T":
            hitType = "triple";
            score = 3 * base;
            break;
        }
      } else {
        const numeric = parseInt(rawScore);
        if (Number.isNaN(numeric)) {
          hitType = "miss";
          score = 0;
        } else if (numeric === 0) {
          hitType = "miss";
          score = 0;
        } else if (numeric === 25) {
          hitType = "single";
          score = 25;
        } else if (numeric === 50) {
          hitType = "double";
          score = 50;
        } else {
          // fallback treat numeric as single
          hitType = "single";
          score = numeric;
        }
      }
    }

    return { hitType, score };
  }

  function clearDartboard() {
    hitCords = [];
    if (!ctx || !canvas || !dartboard) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(dartboard, 0, 0, canvas.width, canvas.height);
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


function mapToBoard(hitX: number, hitY: number) {
  if (!outer || !canvas) return { x: hitX, y: hitY };

  const cx = outer.x;
  const cy = outer.y;

  // canvas center in pixels
  const canvasCx = canvas.width / 2;
  const canvasCy = canvas.height / 2;

  // scale: ratio of canvas radius to calibration radius
  const scale = Math.min(canvas.width, canvas.height) / (2 * outer.radius);

  const mappedX = canvasCx + (hitX - cx) * scale;
  const mappedY = canvasCy + (hitY - cy) * scale;

  return { x: mappedX, y: mappedY };
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

  async function subtractPoints(
  playerIndex: number,
  score: number,
  hitType: "single" | "double" | "triple" | "miss"
) {
  if (isNaN(score) || score > 60 || score < 0) return;

  let remainingPoints = playerPoints[playerIndex] - score;

  // Handle double-in variant
  if (rulesState.variant === "double-in" && !playerScoring[playerIndex]) {
    if (hitType !== "double") {
      shotsThisTurn++;
      shotHistory[shotHistory.length - 1].applied = false;
      return;
    }
    playerScoring[playerIndex] = true;
  }

  // Handle double-out variant and busts
  if (rulesState.variant === "double-out" && remainingPoints === 0 && hitType !== "double") {
    shotsThisTurn++;
    shotHistory[shotHistory.length - 1].applied = false;
    return;
  }

  if (remainingPoints < 0) {
    // Bust: ignore shot
    shotsThisTurn++;
    shotHistory[shotHistory.length - 1].applied = false;
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
      console.error("Failed to update score", res.status, await res.text());
      shotHistory[shotHistory.length - 1].applied = false;
      return;
    }

    const updatedScore = await res.json();
    playerPoints[playerIndex] = updatedScore.score;
    shotHistory[shotHistory.length - 1].applied = true;

    shotsThisTurn++;
    if (shotsThisTurn >= 3) {
      clearDartboard();
      shotsThisTurn = 0;
      currentPlayer = (currentPlayer + 1) % 2;

      if (currentPlayer === 0) player1Hits = ["", "", ""];
      else player2Hits = ["", "", ""];
    }

    checkWinner();
  } catch (err) {
    console.error("Error posting score:", err);
    shotHistory[shotHistory.length - 1].applied = false;
  }
}


  async function checkWinner() {
    let winnerId: number | null = null;

    if (playerPoints[0] === 0) {
      hasWon.set(1);
      winnerId = players[0]!.id;
    } else if (playerPoints[1] === 0) {
      hasWon.set(2);
      winnerId = players[1]!.id;
    }

    if (winnerId) {
      try {
        await fetch("http://localhost:8000/games/setWinner", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            gameId: gameId,
            winnerId: winnerId,
          }),
        });
      } catch (err) {
        console.error("Error setting winner:", err);
      }
    }
  }
function handleDartHit(e: any) {
  try {
    console.log("dart_hit received:", e);

    // Add coords reactively
    hitCords = [...hitCords, e.coords].slice(-3);
    draw();

    // Determine current player hits array
    const hitArray = currentPlayer === 0 ? player1Hits : player2Hits;
    const copy = [...hitArray];
    copy[shotsThisTurn] = e.score;
    if (currentPlayer === 0) player1Hits = copy;
    else player2Hits = copy;

    const { hitType, score } = parseSocketScore(e.score);

    // Save to history for undo
    shotHistory.push({
      playerIndex: currentPlayer,
      score,
      hitType,
      coords: e.coords,
      hitArrayIndex: shotsThisTurn,
    });

    subtractPoints(currentPlayer, score, hitType);
  } catch (err) {
    console.error("handleDartHit error:", err);
  }
}

  onMount(async () => {
    // create socket here so it's not created multiple times by hot-reload/navigation
    socket = io("http://localhost:5000", {
      transports: ["websocket"],
      reconnection: true,
    });

    // ensure single listener (remove any previous)
    socket.off("dart_hit");
    socket.on("dart_hit", handleDartHit);

    // create game
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

    // canvas/dartboard setup (wait for image)
    dartboard.onload = () => {
      if (!canvas || !dartboard) return;
      canvas.width = dartboard.width;
      canvas.height = dartboard.height;
      ctx = canvas.getContext("2d");
      draw();
    };

    // if image already loaded (cache), ensure onload triggered
    if (dartboard && dartboard.complete) {
      canvas.width = dartboard.width;
      canvas.height = dartboard.height;
      ctx = canvas.getContext("2d");
      draw();
    }

  });

  onDestroy(() => {
    if (socket) {
      socket.off("dart_hit", handleDartHit);
      socket.disconnect();
      socket = null;
    }
  });
</script>

<Header />
<section>
  <div id="pointView">
    {#if $hasWon == 0}
      <h1>{$playerState.players[currentPlayer]?.name}s Turn</h1>
    {:else}
      <h1>{$playerState.players[$hasWon - 1]?.name} has Won</h1>
    {/if}
    <div id="boardControls">
  <button on:click={undoLastShot}>Undo Last Shot</button>
</div>


    <div class="pointsBox">
      <h2>{$playerState.players[0]?.name}</h2>
      <div class="hitsBox">
        {#each player1Hits as hit}
          <div class="hit">
            {#if hit == ""}
            {:else if hit == '0'}
              <p style="color:red">X</p>
            {:else}
              <p>{hit}</p>
            {/if}
          </div>
        {/each}
      </div>
      <div class="titleBox" id="ptsBox"><p>{playerPoints[0]}</p></div>
    </div>

    <div class="pointsBox">
      <h2>{$playerState.players[1]?.name}</h2>
      <div class="hitsBox">
        {#each player2Hits as hit}
          <div class="hit">
            {#if hit == ""}
            {:else if hit == '0'}
              <p style="color:red">X</p>
            {:else}
              <p>{hit}</p>
            {/if}
          </div>
        {/each}
      </div>
      <div class="titleBox" id="ptsBox"><p>{playerPoints[1]}</p></div>
    </div>
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
    vertical-align:center;
    margin:0;
    font-size:50px;
    color: #000;
  }

  .hitsBox{
    display: flex;
    flex-direction: row;
    justify-content:space-between;
    grid-area: 2/2/3/5;
  }

  .hit{
    height:60%;
    width:30%;
    justify-content:center;
    vertical-align:middle;
    background-color: #d9d9d9;
    border-radius: 8px;
  }

  .hit p{
    text-align:center;
    font-family: "Roboto", sans-serif;
    color:black;
    font-size:40px;
    margin: 0;
  }

  .titleBox {
    display: flex;
    justify-content: center;
    height: 4vh;
    border-radius:8px;
    background-color: #d9d9d9;
  }

  #ptsBox {
    height: 100%;
    width: 100%;
    padding-top:40%;
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

</style>