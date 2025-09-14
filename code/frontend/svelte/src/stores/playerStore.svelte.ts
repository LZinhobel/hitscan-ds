
import { writable, get } from 'svelte/store';


interface playerState {
	players: (Player|null)[];
}

interface Player {
	id: number;
	name: string;
}

export const store = writable<playerState>({
	players: [null, null]
});


function getPlainPlayers(): (Player | null)[] {
  // get() reads the current store value
  const { players } = get(store);
  // clone to break reactivity / proxies
  return players.map(p => p ? { ...p } : null);
}

export const playerState = {
  subscribe: store.subscribe,
  update: store.update,
  set: store.set,
  getPlainPlayers
};