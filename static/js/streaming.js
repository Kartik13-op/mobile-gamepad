import { eventBus } from './utils.js';

/** Receives the optional desktop screen stream behind the controller. */
export class ScreenStream {
  constructor() {
    this.video = null;
    this.peer = null;
    this.pollTimer = 0;
    this.starting = false;
  }

  init() {
    this.video = document.getElementById('screen-stream');
    this.poll();
    this.pollTimer = window.setInterval(() => this.poll(), 4000);
    eventBus.on('ws:disconnected', () => this.stop());
  }

  async poll() {
    if (this.starting) return;
    try {
      const response = await fetch('/api/stream/status', { cache: 'no-store' });
      const state = await response.json();
      if (state.active && !this.peer) {
        this._setOverlay('CONNECTING');
        await this.start();
      }
      if (!state.active && this.peer) this.stop();
    } catch (_) {
      // The mobile server can be stopped from the monitor; keep controls usable.
      this.stop('STREAM UNAVAILABLE');
    }
  }

  async start() {
    if (!this.video || this.peer || this.starting) return;
    this.starting = true;
    try {
      this.peer = new RTCPeerConnection();
      this.peer.addTransceiver('video', { direction: 'recvonly' });
      this.peer.ontrack = (event) => {
        // Some WebView builds omit event.streams even though the track is valid.
        // Build a stream from the track so playback is reliable there too.
        this.video.srcObject = event.streams?.[0] || new MediaStream([event.track]);
        this.video.classList.add('visible');
        document.body.classList.add('streaming-active');
        this._setOverlay('DESKTOP STREAM');
        this.video.play().catch(() => {});
      };
      this.video.onplaying = () => this.video.classList.add('visible');
      this.peer.onconnectionstatechange = () => {
        if (['failed', 'closed', 'disconnected'].includes(this.peer?.connectionState)) this.stop();
      };
      const offer = await this.peer.createOffer();
      await this.peer.setLocalDescription(offer);
      // Send the completed ICE offer. Without this wait, the answer can be
      // created before a usable LAN candidate exists, leaving a black video.
      await this._waitForIceGathering();
      const response = await fetch('/api/webrtc/offer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sdp: this.peer.localDescription.sdp, type: this.peer.localDescription.type }),
      });
      if (!response.ok) throw new Error('WebRTC offer rejected');
      const answer = await response.json();
      await this.peer.setRemoteDescription(answer);
    } catch (error) {
      console.warn('TouchKeys stream negotiation failed', error);
      this.stop('STREAM ERROR');
    } finally {
      this.starting = false;
    }
  }

  _waitForIceGathering() {
    if (!this.peer || this.peer.iceGatheringState === 'complete') return Promise.resolve();
    return new Promise((resolve) => {
      const peer = this.peer;
      const finish = () => {
        peer.removeEventListener('icegatheringstatechange', finish);
        resolve();
      };
      peer.addEventListener('icegatheringstatechange', finish);
      window.setTimeout(finish, 2500);
    });
  }

  _setOverlay(label) {
    const overlay = document.getElementById('stream-overlay');
    const text = document.getElementById('stream-overlay-label');
    if (text) text.textContent = label;
    overlay?.classList.remove('hidden');
  }

  stop(label = '') {
    if (this.peer) {
      this.peer.ontrack = null;
      this.peer.close();
      this.peer = null;
    }
    if (this.video) {
      this.video.pause();
      this.video.srcObject = null;
      this.video.classList.remove('visible');
    }
    document.body.classList.remove('streaming-active');
    if (label) this._setOverlay(label);
    else document.getElementById('stream-overlay')?.classList.add('hidden');
  }
}

export const screenStream = new ScreenStream();
