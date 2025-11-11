<script lang="ts">
	let { text } = $props();
</script>

<button> {text}</button>

<style>
	button {
		width: 15vw;
		height: 7vh;
		background-color: #733636;
		color: #f6edf1;
		font-size: 40px;
		font-weight: 300;
		letter-spacing: 3px;
		font-family: 'Roboto', sans-serif;
		border-radius: 15px;
		border: none;
		cursor: pointer;
		box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
	}
</style>
