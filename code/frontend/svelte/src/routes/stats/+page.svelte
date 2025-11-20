<script lang="ts">
  import { onMount } from "svelte";
  import Header from "../../comps/Header.svelte";
  import Button from "../../comps/Button.svelte";
  import Chart from "chart.js/auto";

  interface Player {
    id: number;
    name: string;
  }

  interface Score {
    id: number;
    score: number;
    game_id: number;
    player_id: number;
  }

  let selectedPlayer = $state("0");
  let allPlayers: Player[] = $state([]);

  let mostCommonScore = $state(0);
  let hitPercentage = $state(0.0);
  let dartsThrown = $state(0);
  let totalScore = $state(0);
  let winPercentage = $state(0.0);

  onMount(async () => {
    const res = await fetch("http://localhost:8000/player/");
    allPlayers = await res.json();
  });

  async function loadStats(index: Number) {
    const scoresRes = await fetch(`http://localhost:8000/score/${index}`);
    let scores: Score[] = await scoresRes.json();
    mostCommonScore = 0;
    hitPercentage = 0.0;
    dartsThrown = 0;
    totalScore = 0;
    winPercentage = 0.0;

    const percentageRes = await fetch(
      `http://localhost:8000/game/winPercentage/${index}`
    );
    winPercentage = parseFloat(await percentageRes.text());

    if (!scores.length) return;

    dartsThrown = scores.length;

    let scoreCounts: Record<number, number> = {};
    for (let s of scores) {
      scoreCounts[s.score] = (scoreCounts[s.score] || 0) + 1;
    }

    let nonZeroScores = scores.filter((s) => s.score > 0);
    let hits = nonZeroScores.length;

    hitPercentage = parseFloat(((hits / scores.length) * 100).toFixed(2));

    let nonZeroCounts = Object.entries(scoreCounts).filter(
      ([score]) => Number(score) > 0
    );

    mostCommonScore = parseInt(
      nonZeroCounts.sort((a, b) => Number(b[1]) - Number(a[1]))[0][0]
    );

    for (let i = 0; i < scores.length; i++) {
      totalScore += scores[i].score;
    }

    let sortedCounts = Object.entries(scoreCounts).filter(([score]) => Number(score) > 0).sort((a,b) => Number(b[1]) - Number(a[1])).slice(0,10); 

    // Extract labels & values
    let labels = sortedCounts.map(([score]) => score);
    let data = sortedCounts.map(([_, count]) => count);

    const existingChart = Chart.getChart("shots");
    if (existingChart) existingChart.destroy();

    new Chart(document.getElementById("shots") as HTMLCanvasElement, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{ data: data, backgroundColor: "#733636" }],
      },
      options: {
        plugins: {
          legend: {
            display: false,
          }
        },
      },
    });
  }

  async function resetStats() {
    const res = await fetch(
      `http://localhost:8000/score/reset/${selectedPlayer}`,
      {
        method: "DELETE",
      }
    );
    console.log(res);
    selectedPlayer = "0";
    mostCommonScore = 0;
    hitPercentage = 0.0;
    dartsThrown = 0;
    totalScore = 0;
    winPercentage = 0.0;
  }
</script>

<Header />
<section>
  <a href="/">
    <img src="/arrow-left.svg" />
  </a>
  <select bind:value={selectedPlayer}>
    <option selected hidden value="0">Select Player</option>
    {#each allPlayers as p}
      <option
        value={p.id}
        onclick={() => {
          loadStats(p.id);
        }}>{p.name}</option
      >
    {/each}
  </select>

  {#if selectedPlayer != "0"}
    <div id="row">
      <div id="stats">
        <div class="statText">
          <h2 class="accent">Most Common Hit:</h2>
          <h2>{mostCommonScore}</h2>
        </div>
        <div class="statText">
          <h2 class="accent">Hit Percentage:</h2>
          <h2>{hitPercentage}</h2>
        </div>
        <div class="statText">
          <h2 class="accent">Darts Thrown:</h2>
          <h2>{dartsThrown}</h2>
        </div>
        <div class="statText">
          <h2 class="accent">Total Score:</h2>
          <h2>{totalScore}</h2>
        </div>
        {#if winPercentage != 0.0}
          <div class="statText">
            <h2 class="accent">Win Percentage:</h2>
            <h2>{winPercentage}</h2>
          </div>
        {/if}
      </div>
      <div id="shotsDiv">
        <canvas id="shots"></canvas>
      </div>
    </div>
    <div id="button" onclick={() => resetStats()}>
      <Button text="Reset" />
    </div>
  {/if}
</section>

<style>
  @import url("https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap");

  section {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    background-color: #000;
    padding-top: 3vh;
    height: 87vh;
    overflow: hidden;
  }

  select {
    margin-left: 5vw;
    width: 20vw;
    height: 5vh;
    background-color: #000;
    color: #fff;
    font-size: 25px;
    border: none;
    border-bottom: 4px solid #fff;
    outline: none;
    cursor: pointer;
  }

  img {
    position: absolute;
    height: 3.5vw;
    width: 4vw;
    margin-left: 0.5vw;
    color: white;
  }

  #row {
    display: flex;
    flex-direction: row;
    margin-top: 5vh;
    height: 60vh;
    margin-left: 5vw;
  }

  #stats {
    width: 20vw;
    display: flex;
    flex-direction: column;
  }

  #shotsDiv {
    margin-left: 20vw;
    height: 70vh;
    width: 35vw;
  }

  .statText {
    display: flex;
    flex-direction: row;
  }

  h2 {
    font-family: "Roboto", sans-serif;
    font-weight: 300;
    font-size: 30px;
    color: #cecece;
    margin-bottom: 3vh;
  }

  .accent {
    font-weight: 600;
    color: #c35757;
    margin-right: 10px;
  }

  #button {
    display: flex;
    width: 100vw;
    justify-content: center;
  }
</style>
