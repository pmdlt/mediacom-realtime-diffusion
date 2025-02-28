import { writable } from 'svelte/store';

export enum LCMLiveStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  WAIT = 'wait',
  SEND_FRAME = 'send_frame',
  TIMEOUT = 'timeout'
}

const initStatus: LCMLiveStatus = LCMLiveStatus.DISCONNECTED;

export const lcmLiveStatus = writable<LCMLiveStatus>(initStatus);

