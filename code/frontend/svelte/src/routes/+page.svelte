<script lang="ts">
	import Button from '../comps/Button.svelte';
  	import { rulesState } from '../stores/rulesStore.svelte';
	
	let selectedVariant = $state('standard')
	let checked301 = $state(true);
	let checked501 = $state(false)

	function setRules(){
		if(checked301){
			rulesState.ruleset = '301';
			rulesState.variant = selectedVariant;
		}else{
			rulesState.ruleset = '501';
			rulesState.variant = selectedVariant;
		}
	}
	
</script>

<section>
	<h1>Hitscan</h1>

	<h2>Select a Ruleset:</h2>

	<div id="rulesets">
		<div class="ruleset">
			<input type="checkbox" id="301" name="301" onclick={() => {checked501 = false}} bind:checked={checked301}/>
			<label for="301">301</label>
		</div>
		<div class="ruleset">
			<input type="checkbox" id="501" name="501" onclick={() => {checked301 = false}} bind:checked={checked501}/>
			<label for="501">501</label>
		</div>
		<div class="ruleset">
			<label id="variantLabel" for="Variant">Variant</label>
			<select name="variant" id="variant" bind:value={selectedVariant}>
				<option value="standard">Standard</option>
				<option value="double-in">Double In</option>
				<option value="double-out">Double Out</option>
			</select>
		</div>
	</div>

	<a onclick={() => setRules()} href="/setup">
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

	#variantLabel{
		margin-left: 10%;
		grid-area: 2 / 1 / 2 / 1;
	}

	input {
		grid-area: 2 / 1 / 2 / 1;
		cursor: pointer;
	}

	select{
		width:300%;
		background-color:#fff;
		border: 2px solid black;
		border-radius: 4px;
		grid-area: 2 / 3 / 2 / 4;
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
