<script lang="ts">
  import { onMount } from "svelte";
  import Header from "../../comps/Header.svelte";
  import StepCounter from "../../comps/StepCounter.svelte";
  import Button from "../../comps/Button.svelte";
  import { playerState } from "../../stores/playerStore.svelte";

  interface Player {
    id: number;
    name: string;
  }

  //TODO Sanitize Inputs

  let searchTerm1 = $state("");
  let searchTerm2 = $state("");
  let dropdown1visible = $state(false);
  let dropdown2visible = $state(false);
  let allPlayers: Player[] = $state([]);
  
  let bothSelected = $derived(
    $playerState.players[0] !== null && $playerState.players[1] !== null
  );

  $inspect($playerState.players);

  let filteredPlayers1 = $derived(
    allPlayers.filter((p) =>
      p.name.toLowerCase().includes(searchTerm1.toLowerCase())
    )
  );

  let filteredPlayers2 = $derived(
    allPlayers.filter((p) =>
      p.name.toLowerCase().includes(searchTerm2.toLowerCase())
    )
  );

  onMount(async () => {
    const res = await fetch("http://localhost:8000/player/");
    allPlayers = await res.json();
  });

  function selectPlayer(index: number, player: Player) {
    if (index == 0) {
      searchTerm1 = player.name;
    } else {
      searchTerm2 = player.name;
    }
    playerState.update((state) => {
      state.players[index] = player;
      return state;
    });
  }

  async function createPlayer(name: string, index: number) {
    if (allPlayers.find((p) => p.name == name)) {
      return;
    } else {
      const res = await fetch("http://localhost:8000/player/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const newPlayer: Player = await res.json();
      selectPlayer(index, newPlayer);
    }
  }
</script>

<Header />
<section>
  <StepCounter currentStep="1" />

  <h2>Enter Player Names:</h2>

  <div id="inputs">
    <div class="player-input">
      <input
        type="text"
        id="p1Input"
        value={searchTerm1}
        oninput={(e) => (searchTerm1 = e.target!.value)}
        onfocus={() => (dropdown1visible = true)}
        onblur={() => (dropdown1visible = false)}
        required
        placeholder="Player 1..."
      />
      {#if dropdown1visible}
        <div class="dropdown">
          {#if filteredPlayers1.length}
            {#each filteredPlayers1 as p}
              <a
                href="#"
                class="dropdown-item"
                onkeydown={(e) => {
                  if (e.key == "Enter") {
                    selectPlayer(1, p);
                  }
                }}
                onmousedown={() => selectPlayer(0, p)}
              >
                {p.name}
              </a>
            {/each}
          {:else if searchTerm1}
            <a
              href="#"
              class="dropdown-item"
              onkeydown={(e) => {
                if (e.key == "Enter") {
                  createPlayer(searchTerm1, 0);
                }
              }}
              onmousedown={() => createPlayer(searchTerm1, 0)}
            >
              ➕ Create "{searchTerm1}"
            </a>
          {/if}
        </div>
      {/if}
    </div>

    <div class="player-input">
      <input
        type="text"
        id="p2Input"
        value={searchTerm2}
        oninput={(e) => (searchTerm2 = e.target!.value)}
        onfocus={() => (dropdown2visible = true)}
        onblur={() => (dropdown2visible = false)}
        required
        placeholder="Player 2..."
      />
      {#if dropdown2visible}
        <div class="dropdown">
          {#if filteredPlayers2.length}
            {#each filteredPlayers2 as p}
              <a
                href="#"
                class="dropdown-item"
                onkeydown={(e) => {
                  if (e.key == "Enter") {
                    selectPlayer(1, p);
                  }
                }}
                onmousedown={() => selectPlayer(1, p)}
              >
                {p.name}
              </a>
            {/each}
          {:else if searchTerm2}
            <a
              href="#"
              class="dropdown-item"
              onkeydown={(e) => {
                if (e.key == "Enter") {
                  createPlayer(searchTerm2, 1);
                }
              }}
              onmousedown={() => createPlayer(searchTerm2, 1)}
            >
              ➕ Create "{searchTerm2}"
            </a>
          {/if}
        </div>
      {/if}
    </div>
  </div>

  <a
    href={bothSelected ? "/setup/camera" : "#"}
    onclick={() => {
      if (!bothSelected) {
        if ($playerState.players[0] == null && $playerState.players[1] == null) {
          document.getElementById("p1Input")!.style.border = `3px solid #f00`;
          document.getElementById("p2Input")!.style.border = `3px solid #f00`;
        } else if ($playerState.players[0] == null) {
          document.getElementById('p2Input')!.style.border = "3px solid #fff";
          document.getElementById("p1Input")!.style.border = `3px solid #f00`;
        } else if ($playerState.players[1] == null){
          document.getElementById('p1Ipnut')!.style.border = "3px solid #fff";
          document.getElementById("p2Input")!.style.border = `3px solid #f00`;
        }
      }
    }}
  >
    <Button text="Next" />
  </a>
</section>

<style>
  @import url("https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap");

  section {
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: #000;
    padding-top: 20vh;
    height: 80vh;
    overflow: hidden;
  }
  h2 {
    font-family: "Roboto", sans-serif;
    font-weight: 300;
    font-size: 64px;
    color: #cecece;
    margin-bottom: 3vh;
  }
  #inputs {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    gap: 10vw;
    width: 60%;
  }
  input {
    background-color: #733636;
    border-radius: 16px;
    border: 3px solid #fff;
    height: 5vh;
    width: 15vw;
    font-size: 25px;
    color: #fff;
    font-family: "Roboto", sans-serif;
  }
  input:focus {
    border: 3px solid #c35757;
    outline: none;
  }
  a {
    margin-top: 10vh;
  }

  #inputs {
    display: flex;
    flex-direction: row;
    gap: 10vw;
  }
  .player-input {
    position: relative;
    width: 15vw;
  }

  .dropdown {
    position: absolute;
    background: white;
    border-radius: 6px;
    width: 100%;
    max-height: 200px;
    overflow-y: auto;
    z-index: 10;
    display: flex;
    flex-direction: column;
    margin-left: 2%;
  }

  .dropdown-item {
    margin-top: 0;
    padding: 8px;
    text-decoration: none;
    color: black;
    cursor: pointer;
  }

  .dropdown-item:hover {
    background: #eee;
  }
</style>
