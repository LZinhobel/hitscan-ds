<script lang="ts">
  import Button from "../comps/Button.svelte";
  import { rulesState } from "../stores/rulesStore.svelte";

  let selectedVariant = $state("standard");
  let checked301 = $state(true);
  let checked501 = $state(false);

  function setRules() {
    if (checked301) {
      rulesState.ruleset = "301";
      rulesState.variant = selectedVariant;
    } else {
      rulesState.ruleset = "501";
      rulesState.variant = selectedVariant;
    }
  }
</script>

<section>
  <h1>Hitscan</h1>

  <h2>Select a Ruleset:</h2>

  <div id="rulesets">
    <div class="ruleset toggle">
      <input
        type="checkbox"
        id="301"
        name="301"
        onclick={() => { checked501 = false; }}
        bind:checked={checked301}
      />
      <label class={checked301 ? "active" : ""} for="301">301</label>
    </div>

    <div class="ruleset toggle">
      <input
        type="checkbox"
        id="501"
        name="501"
        onclick={() => { checked301 = false; }}
        bind:checked={checked501}
      />
      <label class={checked501 ? "active" : ""} for="501">501</label>
    </div>

    <div class="ruleset selectWrap">
      <select name="variant" id="variant" bind:value={selectedVariant} class="styledSelect">
        <option value="standard">Standard</option>
        <option value="double-in">Double In</option>
        <option value="double-out">Double Out</option>
      </select>
    </div>
  </div>

  <div id="buttonRow">
    <a href="/stats">
      <Button text="Stats" />
    </a>
    <a onclick={() => setRules()} href="/setup">
      <Button text="Next" />
    </a>
  </div>
</section>

<style>
  @import url("https://fonts.googleapis.com/css2?family=Nova+Flat&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap");

  section {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    flex: 0.6;
    background-color: #000000;
    margin: 0;
    height: 100vh;
  }

  h1 {
    font-family: "Nova Flat", system-ui;
    color: #eeecec;
    font-size: 120px;
    letter-spacing: 30%;
  }

  h2 {
    font-family: "Roboto", sans-serif;
    font-weight: 300;
    font-size: 64px;
    color: #eeecec;
    margin-bottom: 7vh;
  }

  /* Ruleset row */
  #rulesets {
    width: 90%;
    height: 5vh;
    margin-left: 5%;
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;    /* center children vertically */
    margin-right: 5%;
    margin-bottom: 10vh;
    gap: 1rem;
  }

  /* base ruleset sizing so all three have exact same box */
  .ruleset {
    width: 20%;             /* same width for all three boxes */
    height: 100%;
    border-radius: 6px;
    display: flex;
    align-items: center;    /* center content vertically */
    justify-content: center;/* center content horizontally */
    box-sizing: border-box;
    overflow: hidden;
  }

  /* preserve earlier visual for the original cards */
  .ruleset.toggle {
    background-color: #733636;
    border: 2px solid #fff;
    cursor: pointer;
    position: relative;
    transition: transform 0.15s;
  }

  .ruleset.toggle:hover {
    transform: translateY(-2px);
  }

  /* Hide native checkbox input but keep it accessible to bindings */
  .ruleset.toggle input {
    opacity: 0;
    position: absolute;
    pointer-events: none;
  }

  /* Label styled like a button, fills the box */
  .ruleset.toggle label {
    font-family: "Roboto", sans-serif;
    font-weight: 500;
    color: #ececec;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    width: 100%;
    font-size: 26px;
    border-radius: 6px;
    transition: background-color 0.2s, color 0.2s;
    box-sizing: border-box;
    padding: 0 8px;
    text-align: center;
  }

  .ruleset.toggle label.active {
    background-color: #c35757;
    color: #180a10;
  }

  /* Variant container uses the exact same outer sizing and border as toggles */
  .selectWrap {
    background-color: #733636;
    border: 2px solid #c35757;
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;    /* center label and select horizontally */
    gap: 4px;
    box-sizing: border-box;
    padding: 4px 6px;       /* keep padding small so inner select fits */
  }

  .selectWrap label {
    font-family: "Roboto", sans-serif;
    font-weight: 500;
    color: #ececec;
    font-size: 16px;
    margin: 0;
    line-height: 1;
    text-align: center;
    user-select: none;
  }

  /* Make select never exceed parent width and visually match the button look */
  .styledSelect {
    -webkit-appearance: none;
    -moz-appearance: none;
    appearance: none;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    color:#ececec;
    text-align:center;
    font-size: 24px;
    background-color: #733636;
    font-family: "Roboto", sans-serif;
    border: none;
    padding: 6px 10px;
    border-radius: 4px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }



  #buttonRow {
    width: 60vw;
    display: flex;
    flex-direction: row;
    justify-content: space-evenly;
  }
</style>
