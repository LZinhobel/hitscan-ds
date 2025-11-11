import { writable } from "svelte/store";

export type Ring = {
  x: number;
  y: number;
  radius: number;
  scaleX: number;
  scaleY: number;
};

export type Lines = {
  rotation: number;
  offsetX: number;
  offsetY: number;
  scale: number;
  stretchX: number;
  stretchY: number;
};

export type Calibration = {
  rings: Ring[];
  lines: Lines;
};

// Check environment (SSR vs browser)
const isBrowser = typeof window !== "undefined" && typeof localStorage !== "undefined";

function loadInitial(): Calibration {
  if (isBrowser) {
    const stored = localStorage.getItem("calibration");
    if (stored) return JSON.parse(stored);
  }
  return {
    rings: [],
    lines: {
      rotation: 0,
      offsetX: 0,
      offsetY: 0,
      scale: 1,
      stretchX: 1,
      stretchY: 1
    }
  };
}

const calibrationStore = writable<Calibration>(loadInitial());

// Persist only in browser
if (isBrowser) {
  calibrationStore.subscribe((value) => {
    localStorage.setItem("calibration", JSON.stringify(value));
  });
}

export const setCalibration = (data: Calibration) => calibrationStore.set(data);
export const resetCalibration = () => calibrationStore.set(loadInitial());

export default calibrationStore;
