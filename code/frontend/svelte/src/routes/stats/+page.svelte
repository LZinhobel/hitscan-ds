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
  let winPercentage= $state(0.0);

  onMount(async () => {
    const res = await fetch("http://localhost:8000/player/");
    allPlayers = await res.json();
  });

  async function loadStats(index: Number) {
    const scoresRes = await fetch(`http://localhost:8000/score/${index}`);
    let scores: Score[] = await scoresRes.json();

    const percentageRes = await fetch(`http://localhost:8000/game/winPercentage/${index}`)
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

    for(let i = 0; i < scores.length; i++){
      totalScore += scores[i].score;
    }
    

    let labels = Object.keys(scoreCounts);
    let data = Object.values(scoreCounts);

    const existingChart = Chart.getChart("shots");
    if (existingChart) existingChart.destroy();

    new Chart(document.getElementById("shots") as HTMLCanvasElement, {
      type: "pie",
      data: {
        labels: labels,
        datasets: [{ data: data }],
      },
      options: {
        plugins: {
          legend: {
            display: false,
          },
        },
      },
    });
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
        <h2>Most Common Hit: {mostCommonScore}</h2>
        <h2>Hit Percentage: {hitPercentage}%</h2>
        <h2>Darts Thrown: {dartsThrown}</h2>
        <h2>Total Score: {totalScore}</h2>
        {#if winPercentage != 0.0}
          <h2>Win Percentage: {winPercentage}%</h2>
        {/if}
        
      </div>
      <div id="shotsDiv">
        <canvas id="shots"></canvas>
      </div>
    </div>
  {/if}
</section>

<style>
  @import url("https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap");

  section {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    background-color: #180a10;
    padding-top: 3vh;
    height: 87vh;
    overflow: hidden;
  }

  select {
    margin-left: 5vw;
    width: 20vw;
    height: 5vh;
    background-color: #180a10;
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

  h2 {
    font-family: "Roboto", sans-serif;
    font-weight: 300;
    font-size: 30px;
    color: #f6edf1;
    margin-bottom: 3vh;
  }
</style>
