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

const stored = localStorage.getItem("calibration");
const initialValue: Calibration = stored
  ? JSON.parse(stored)
  : {
      rings: [],
      lines: {
        rotation: 0,
        offsetX: 0,
        offsetY: 0,
        scale: 1,
        stretchX: 1,
        stretchY: 1,
      },
    };


const calibrationStore = writable<Calibration>(initialValue);

calibrationStore.subscribe((value) => {
  localStorage.setItem("calibration", JSON.stringify(value));
});

export const setCalibration = (data: Calibration) => {
  calibrationStore.set(data);
};

export const resetCalibration = () => {
  calibrationStore.set(initialValue);
};

export default calibrationStore;
