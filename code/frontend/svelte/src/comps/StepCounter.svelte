<script>
	let { currentStep } = $props();
	let totalSteps = 3;
</script>

<div class="stepper">
	{#each Array(totalSteps), i (i)}
		<div class="step {parseInt(currentStep) > i ? 'active' : ''}">
			{i + 1}
		</div>

		{#if i < totalSteps - 1}
			<div class="line {parseInt(currentStep) > i + 1 ? 'active' : ''}"></div>
		{/if}
	{/each}
</div>

<style>
	@import url('https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap');

	.stepper {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 25%;
	}

	.step {
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: 'Nova Flat', system-ui;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		border: 2px solid #ccc;
		background-color: #2a002b;
		color: white;
		font-weight: bold;
		transition: all 0.3s;
	}

	.step.active {
		background-color: #b4457c;
		border-color: #b4457c;
	}

	.line {
		flex-grow: 1;
		height: 8px;

		background-color: #ccc;
		margin: 0;
	}

	.line.active {
		background-color: #b4457c;
	}
</style>
