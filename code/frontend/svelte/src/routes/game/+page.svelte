<script lang="ts">
	import { get, writable } from 'svelte/store';
	import Header from '../../comps/Header.svelte';
	import { inputState } from '../../stores/inputStore.svelte';
	import Button from '../../comps/Button.svelte';
	import { onMount } from 'svelte';

	interface Player {
		id: number;
		name: string;
	}

	let players: (Player|null)[] = [];
	let gameId: Number;
	let currentPlayer = $state(0);
	let playerPoints: number[] = $state([301, 301]);
	let playerInputs: string[] = ['', ''];
	let hasWon = writable(0);

	onMount(async () => {
		players = inputState.getPlainPlayers();
		console.log(players)
		const res = await fetch('http://localhost:8000/game/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				player1: players[0]?.id,
				player2: players[1]?.id,
				version: '301'
			})
		});

		let game = await res.json();
		console.log(game);
	});

	function subtractPoints(playerIndex: number) {
		if (
			isNaN(parseInt(playerInputs[playerIndex - 1])) ||
			parseInt(playerInputs[playerIndex - 1]) > 60
		) {
			return;
		} else {
			if (playerPoints[playerIndex - 1] - parseInt(playerInputs[playerIndex - 1]) < 0) {
				playerPoints[playerIndex - 1] = 0;
			} else {
				playerPoints[playerIndex - 1] -= parseInt(playerInputs[playerIndex - 1]);
			}
			playerInputs[playerIndex - 1] = '';
			currentPlayer = currentPlayer == 0 ? 1 : 0;
			checkWinner();
		}
	}

	function checkWinner() {
		if (playerPoints[0] == 0) {
			hasWon.set(1);
		} else if (playerPoints[1] == 0) {
			hasWon.set(2);
		} else {
			return;
		}
	}
</script>

<Header />
<section>
	<div id="pointView">
		{#if $hasWon == 0}
			<h1>{$inputState.players[currentPlayer]?.name}s Turn</h1>
		{:else if $hasWon == 1}
			<h1>{$inputState.players[$hasWon - 1]?.name} has Won</h1>
		{:else if $hasWon == 2}
			<h1>{$inputState.players[$hasWon - 1]?.name} has Won</h1>
		{/if}
		<div class="pointsBox">
			<h2>{$inputState.players[0]?.name}</h2>

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
						if (event.key === 'Enter') {
							subtractPoints(1);
						} else {
							return;
						}
					}}
				/>
			</div>
		</div>
		<div class="pointsBox">
			<h2>{$inputState.players[1]?.name}</h2>

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
						if (event.key === 'Enter') {
							subtractPoints(2);
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
	@import url('https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap');

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
		font-family: 'Roboto', sans-serif;
		color: #f6edf1;
		font-size: 50px;
		font-weight: 700;
	}

	h2 {
		font-family: 'Nova Flat', system-ui;
		color: #f6edf1;
		font-size: 36px;
		grid-area: 1/1/2/3;
		height: 100%;
		margin: 5%;
	}

	p {
		font-family: 'Roboto', sans-serif;
		font-weight: 700;
		font-size: 14px;
		color: #000;
	}

	input {
		width: 100%;
		font-family: 'Roboto', sans-serif;
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
