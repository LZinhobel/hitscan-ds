<script lang="ts">
  import { get, writable } from "svelte/store";
  import Header from "../../comps/Header.svelte";
  import { playerState } from "../../stores/playerStore.svelte";
  import Button from "../../comps/Button.svelte";
  import { onMount } from "svelte";
  import { rulesState } from "../../stores/rulesStore.svelte";
  import { io } from "socket.io-client";
  import calibrationStore from "../../stores/calibrationStore.svelte";

  interface Player {
    id: number;
    name: string;
  }

  // TODO: Double check mapping Function, Display last 3 hits on player box, research more to put in there ?

  let players: (Player | null)[] = [];
  let gameId: Number;
  let currentPlayer = $state(0);

  let shotsThisTurn = $state(0);
  let playerScoring: boolean[] = $state([false, false]);
  let playerPoints: number[] = $state([0, 0]);

  let hasWon = writable(0);

  let player1Hits: String[] = $state(["", "", ""]);
  
  
  let player2Hits: String[] = $state(["", "", ""]);

  const socket = io("http://localhost:5000/");

  let canvas: HTMLCanvasElement|null = $state(null)
  let ctx: CanvasRenderingContext2D | null = null;
  let dartboard: HTMLImageElement;
  const calibration = get(calibrationStore);
  const outer = calibration.rings[0];

  let hitCords: Array<{ x: number; y: number }> = $state([]);

  onMount(async () => {
    players = playerState.getPlainPlayers();
    console.log(players);
    const res = await fetch("http://localhost:8000/game/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        player1: players[0]?.id,
        player2: players[1]?.id,
        version: rulesState.ruleset,
      }),
    });
    1;
    let game = await res.json();
    gameId = game.gameId;
    playerPoints = [game.player1Score, game.player2Score];
    console.log(game);

    ctx = canvas.getContext("2d");
    canvas.width = dartboard.width;
    canvas.height = dartboard.height;

    setTimeout(() => {
      draw();
    }, 500);
  });

  socket.on("dart_hit", (e) => {
    if (currentPlayer === 0) {
      player1Hits[shotsThisTurn] = e.score;
    } else {
      player2Hits[shotsThisTurn] = e.score;
    }

    const { hitType, score } = parseSocketScore(e.score);
    hitCords.push(e.coords);
    draw();
    subtractPoints(currentPlayer, score, hitType);
  });

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
        // Handle bull, double bull, and misses
        const numeric = parseInt(rawScore);
        if (numeric === 0) {
          hitType = "miss";
          score = 0;
        } else if (numeric === 25) {
          hitType = "single";
          score = 25;
        } else if (numeric === 50) {
          hitType = "double";
          score = 50;
        }
      }
    }

    return { hitType, score };
  }

  function clearDartboard() {
    hitCords = [];
    ctx!.clearRect(0, 0, canvas.width, canvas.height);
    ctx!.drawImage(dartboard, 0, 0, canvas.width, canvas.height);
  }

  function draw() {
    if (!ctx || !dartboard) return;
    clearDartboard();

    ctx.strokeStyle = "red";
    ctx.lineWidth = 2;

    hitCords.forEach(({ x, y }) => {
      const { x: mappedX, y: mappedY } = mapToBoard(x, y);
      drawHit(mappedX, mappedY);
    });
  }

  function mapToBoard(hitX: number, hitY: number) {
    const scaleX = canvas.width / (outer.radius * 2 * outer.scaleX);
    const scaleY = canvas.height / (outer.radius * 2 * outer.scaleY);

    const offsetX = outer.x - outer.radius;
    const offsetY = outer.y - outer.radius;

    const mappedX = (hitX - offsetX) * scaleX;
    const mappedY = (hitY - offsetY) * scaleY;
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

    if (rulesState.variant === "double-in" && !playerScoring[playerIndex]) {
      if (hitType !== "double") {
        shotsThisTurn++;
        return;
      }
      playerScoring[playerIndex] = true;
    }

    if (rulesState.variant === "double-out") {
      const remainingPoints = playerPoints[playerIndex] - score;
      if (remainingPoints === 0 && hitType !== "double") {
        shotsThisTurn++;
        return;
      }
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
        console.error("Failed to update score");
        return;
      }

      const updatedScore = await res.json();
      playerPoints[playerIndex] = updatedScore.score;

      shotsThisTurn++;

      if (shotsThisTurn >= 3) {
        clearDartboard();
        if (currentPlayer === 0) {
          currentPlayer = 1;
        } else if(currentPlayer === 1){
          currentPlayer = 0;
          player1Hits = ["", "", ""];
          player2Hits = ["", "", ""];
        }
        shotsThisTurn = 0;
      }

      checkWinner();
    } catch (err) {
      console.error("Error posting score:", err);
    }
  }

  async function checkWinner() {
    let winnerId: number | null = null;

    if (playerPoints[0] == 0) {
      hasWon.set(1);
      winnerId = players[0]!.id;
    } else if (playerPoints[1] == 0) {
      hasWon.set(2);
      winnerId = players[1]!.id;
    }

    if (winnerId) {
      try {
        const res = await fetch("http://localhost:8000/games/setWinner", {
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
</script>

<Header />
<section>
  <div id="pointView">
    {#if $hasWon == 0}
      <h1>{$playerState.players[currentPlayer]?.name}s Turn</h1>
    {:else if $hasWon == 1}
      <h1>{$playerState.players[$hasWon - 1]?.name} has Won</h1>
    {:else if $hasWon == 2}
      <h1>{$playerState.players[$hasWon - 1]?.name} has Won</h1>
    {/if}
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
    background-color: #180a10;
    margin: 0;
    height: 100vh;
    overflow: hidden;
  }

  h1 {
    font-family: "Roboto", sans-serif;
    color: #f6edf1;
    font-size: 50px;
    font-weight: 700;
  }

  h2 {
    font-family: "Nova Flat", system-ui;
    color: #f6edf1;
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
    background-color: rgba(134, 43, 82, 0.7);
    height: 30%;
    margin-bottom: 10%;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
    grid-template-rows: 1fr 1fr 1fr 1fr;
  }
</style>
