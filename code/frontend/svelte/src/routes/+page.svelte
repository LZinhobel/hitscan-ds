<script lang="ts">
	import Button from '../comps/Button.svelte';
</script>

<section>
	<h1>Hitscan</h1>

	<h2>Select a Ruleset:</h2>

	<div id="rulesets">
		<div class="ruleset">
			<input type="checkbox" id="301" name="301" checked />
			<label for="301">301</label>
		</div>
		<div class="ruleset">
			<input type="checkbox" id="501" name="501" disabled />
			<label for="501">501</label>
		</div>
		<div class="ruleset">
			<input type="checkbox" id="killer" name="killer" disabled />
			<label for="killer">Killer</label>
		</div>
	</div>

	<a href="/setup">
		<Button text="Next" />
	</a>
</section>

<style>
	@import url('https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap');

	section {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		flex: 0.6;
		background-color: #180a10;
		margin: 0;
		height: 100vh;
	}

	h1 {
		font-family: 'Nova Flat', system-ui;
		color: #f6edf1;
		font-size: 120px;
		letter-spacing: 30%;
	}

	h2 {
		font-family: 'Roboto', sans-serif;
		font-weight: 300;
		font-size: 64px;
		color: #f6edf1;
		margin-bottom: 7vh;
	}

	label {
		font-family: 'Roboto', sans-serif;
		font-weight: 400;
		font-size: 22px;
		grid-area: 2 / 2 / 2 / 4;
	}

	input {
		grid-area: 2 / 1 / 2 / 1;
		cursor: pointer;
	}

	#rulesets {
		width: 90%;
		height: 5vh;
		margin-left: 5%;
		display: flex;
		flex-direction: row;
		justify-content: space-between;
		margin-right: 5%;
		margin-bottom: 10vh;
	}

	.ruleset {
		background-color: #dca1ba;
		width: 20%;
		height: 100%;
		display: grid;
		grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1fr;
		grid-template-rows: 1fr 1fr 1fr;
	}
</style>
