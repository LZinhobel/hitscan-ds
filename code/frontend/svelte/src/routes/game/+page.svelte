<script lang="ts">
  import { get, writable } from "svelte/store";
  import Header from "../../comps/Header.svelte";
  import { playerState } from "../../stores/playerStore.svelte";
  import Button from "../../comps/Button.svelte";
  import { onMount } from "svelte";
  import { rulesState } from "../../stores/rulesStore.svelte";
  import {io} from 'socket.io-client';

  interface Player {
    id: number;
    name: string;
  }

  let players: (Player | null)[] = [];
  let gameId: Number;
  let currentPlayer = $state(0);
  let shotsThisTurn = $state(0);
  let playerScoring: boolean[] = $state([false, false]);
  let playerPoints: number[] = $state([0, 0]);
  let playerInputs: string[] = ["", ""];
  let hasWon = writable(0);
  const socket = io("http://localhost:5000/");

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
1
    let game = await res.json();
    gameId = game.gameId;
    playerPoints = [game.player1Score, game.player2Score];
    console.log(game);
    console.log(gameId);
  });

  socket.on('dart_hit', (e) =>{
    subtractPoints(currentPlayer, e.score)
  })

  async function subtractPoints(playerIndex: number, score: number) {
    if (isNaN(score) || score > 60 || score < 0) {
      return;
    }

    let hitType = getHitType(score);

    if (rulesState.variant == "double-in" && !playerScoring[playerIndex]) {
      if (hitType != "double") {
        shotsThisTurn++;
        return;
      }
      playerScoring[playerIndex] = true;
    }

    if (rulesState.variant == "double-out") {
      let remainingPoints = playerPoints[playerIndex] - score;
      if (remainingPoints == 0 && hitType != "double") {
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
          score: score,
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
        currentPlayer = currentPlayer === 0 ? 1 : 0;
        shotsThisTurn = 0;
      }

      checkWinner();
    } catch (err) {
      console.error("Error posting score:", err);
    }
  }

  function getHitType(score: number) {
    if (score === 25) return "single";
    if (score === 50) return "double";

    for (let n = 1; n <= 20; n++) {
      if (score === n) return "single";
      if (score === 2 * n) return "double";
      if (score === 3 * n) return "triple";
    }
  }

  async function checkWinner() {
    let winnerId: number | null = null;

    if (playerPoints[0] == 0) {
      hasWon.set(1);
      winnerId = players[0]!.id;
    } else if (playerPoints[1] == 0) {
      hasWon.set(2);
      winnerId = players[1]!.id
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

      <div class="titleBox" id="ptsTitleBox"><p>Pts</p></div>
      <div class="titleBox" id="inputTitleBox"><p>Input</p></div>
      <div class="titleBox" id="ptsBox"><p>{playerPoints[0]}</p></div>
      <div class="titleBox inputBox" id="inputBox1">
        <input
          type="text"
          placeholder="Points here..."
          bind:value={playerInputs[0]}
          disabled={currentPlayer == 1 || $hasWon == 1 || $hasWon == 2}
          onkeydown={(event) => {
            if (event.key === "Enter") {
              subtractPoints(1, parseInt(playerInputs[0]));
            } else {
              return;
            }
          }}
        />
      </div>
    </div>
    <div class="pointsBox">
      <h2>{$playerState.players[1]?.name}</h2>

      <div class="titleBox" id="ptsTitleBox"><p>Pts</p></div>
      <div class="titleBox" id="inputTitleBox"><p>Input</p></div>
      <div class="titleBox" id="ptsBox"><p>{playerPoints[1]}</p></div>
      <div class="titleBox inputBox" id="inputBox2">
        <input
          type="text"
          placeholder="Points here..."
          bind:value={playerInputs[1]}
          disabled={currentPlayer == 0 || $hasWon == 1 || $hasWon == 2}
          onkeydown={(event) => {
            if (event.key === "Enter") {
              subtractPoints(2, parseInt(playerInputs[1]));
            } else {
              return;
            }
          }}
        />
      </div>
    </div>
  </div>
  <div id="boardView"></div>
</section>

<style>
  @import url("https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap");

  section {
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: center;
    flex: 0.6;
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
    font-size: 14px;
    color: #000;
  }

  input {
    width: 100%;
    font-family: "Roboto", sans-serif;
    background-color: #d9d9d9;
    border: none;
    box-sizing: border-box;
    color: #000;
    font-size: 14px;
    font-weight: 700;
  }

  input:focus {
    outline: none;
    border: 2px solid #dca1ba;
  }

  .titleBox {
    display: flex;
    justify-content: center;
    height: 80%;

    background-color: #d9d9d9;
  }

  #ptsTitleBox {
    grid-area: 1/4/1/4;
  }

  #inputTitleBox {
    grid-area: 1/6/1/6;
  }

  #ptsBox {
    height: 100%;
    grid-area: 3/4/3/4;
  }

  .inputBox {
    height: 100%;
    width: 100%;
    grid-area: 3/6/3/6;
  }

  #pointView {
    display: flex;
    flex-direction: column;
    height: 60%;
    width: 40%;
  }
  #boardView {
    width: 45%;
    height: 60%;
    margin-top: 10%;
    margin-left: 5%;
  }
  .pointsBox {
    background-color: rgba(134, 43, 82, 0.7);
    height: 40%;
    margin-bottom: 10%;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
    grid-template-rows: 1fr 1fr 1fr 1fr;
  }
</style>
