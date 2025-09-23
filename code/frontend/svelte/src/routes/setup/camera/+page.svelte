<script lang="ts">
  import { onMount } from "svelte";
  import Header from "../../../comps/Header.svelte";
  import StepCounter from "../../../comps/StepCounter.svelte";
  import Button from "../../../comps/Button.svelte";
  import CameraCalibrator from "../../../comps/CameraCalibrator.svelte";
  import { rulesState } from "../../../stores/rulesStore.svelte";

  onMount(async () => {});
</script>

<Header />
<section>
  <StepCounter currentStep="2" />

  <h2>Setup Camera:</h2>

  <CameraCalibrator></CameraCalibrator>

  {#if rulesState.isCalibrated}
  <a href="/game">
    <Button text="Play"/>
  </a>
  {/if}
</section>

<style>
  @import url("https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap");

  section {
    display: flex;
    flex-direction: column;
    align-items: center;
    background-color: #180a10;
    padding-top: 3vh;
    height: 87vh;
    overflow: hidden;
  }
  
  h2 {
    font-family: "Roboto", sans-serif;
    font-weight: 300;
    font-size: 64px;
    color: #f6edf1;
    margin-bottom: 3vh;
  }
</style>
