<script lang="ts">
	import { onMount } from 'svelte';
	import Header from '../../comps/Header.svelte';
	import StepCounter from '../../comps/StepCounter.svelte';
	import Button from '../../comps/Button.svelte';
	import { playerState } from '../../stores/playerStore.svelte';

	interface Player {
		id: number;
		name: string;
	}

  //TODO Sanitize Inputs, Duplicate Protection, Enter to Select, make sure both selected

	let searchTerm1 = $state('');
	let searchTerm2 = $state('');
	let dropdown1visible = $state(false);
	let dropdown2visible = $state(false);
	let allPlayers: Player[] = $state([]);
	let selectedPlayers: (Player | null)[] = $state([null, null]);
 
  $inspect(searchTerm1)

	let filteredPlayers1 = $derived(
		allPlayers.filter((p) => p.name.toLowerCase().includes(searchTerm1.toLowerCase()))
	);

	let filteredPlayers2 = $derived(
		allPlayers.filter((p) => p.name.toLowerCase().includes(searchTerm2.toLowerCase()))
	);

	onMount(async () => {
		const res = await fetch('http://localhost:8000/player/');
		allPlayers = await res.json();
	});

	function selectPlayer(index: number, player: Player) {
    if(index == 0){
      searchTerm1 = player.name
    }else{
      searchTerm2 = player.name
    }
		playerState.update((state) => {
			state.players[index] = player;
			return state;
		});
	}

	async function createPlayer(name: string, index: number) {

		const res = await fetch('http://localhost:8000/player/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name })
		});
		const newPlayer: Player = await res.json();
		selectPlayer(index, newPlayer);
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
      value={searchTerm1}
      oninput={(e) => (searchTerm1 = e.target.value)}
      onfocus={() => (dropdown1visible = true)}
      onblur={() => (dropdown1visible = false)}
      placeholder="Player 1..."
    />
    {#if dropdown1visible}
      <div class="dropdown">
        {#if filteredPlayers1.length}
          {#each filteredPlayers1 as p}
            <a
              href="#"
              class="dropdown-item"
              onmousedown={() => selectPlayer(0, p)}
            >
              {p.name}
            </a>
          {/each}
        {:else if searchTerm1}
          <a
            href="#"
            class="dropdown-item"
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
      value={searchTerm2}
      oninput={(e) => (searchTerm2 = e.target.value)}
      onfocus={() => (dropdown2visible = true)}
      onblur={() => (dropdown2visible = false)}
      placeholder="Player 2..."
    />
    {#if dropdown2visible}
      <div class="dropdown">
        {#if filteredPlayers2.length}
          {#each filteredPlayers2 as p}
            <a
              href="#"
              class="dropdown-item"
              onmousedown={() => selectPlayer(1, p)}
            >
              {p.name}
            </a>
          {/each}
        {:else if searchTerm2}
          <a
            href="#"
            class="dropdown-item"
            onmousedown={() => createPlayer(searchTerm2, 1)}
          >
            ➕ Create "{searchTerm2}"
          </a>
        {/if}
      </div>
    {/if}
  </div>
</div>


	<a href="/game">
		<Button text="Play" />
	</a>
</section>

<style>
	@import url('https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap');

	section {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		background-color: #180a10;
		margin: 0;
		height: 100vh;
		overflow: hidden;
	}
	h2 {
		font-family: 'Roboto', sans-serif;
		font-weight: 300;
		font-size: 64px;
		color: #f6edf1;
		margin-bottom: 7vh;
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
		background-color: rgba(220, 161, 186, 0.4);
		border-radius: 16px;
		border: 3px solid #fff;
		height: 5vh;
		width: 15vw;
		font-size: 25px;
		color: #fff;
		font-family: 'Roboto', sans-serif;
	}
	input:focus {
		border: 3px solid #dca1ba;
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
  margin-left:2%;
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
