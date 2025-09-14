<script lang="ts">
	let { children } = $props();
</script>

{@render children()}

<style>
	* {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
		overflow: hidden;
	}
</style>
