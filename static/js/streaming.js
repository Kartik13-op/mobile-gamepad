import { eventBus } from './utils.js';

/** Receives the optional desktop screen stream behind the controller. */
export class ScreenStream {
  constructor() {
    this.video = null;
    this.peer = null;
    this.mediaStream = null;
    this._tracks = new Map();
    this._audioResumeArmed = false;
    this.pollTimer = 0;
    this.starting = false;
  }

  init() {
    this.video = document.getElementById('screen-stream');
    // Safari only allows an unmuted MediaStream after a user gesture. Arm
    // this before negotiation so an early tap on the controller is not lost.
    this._armAudioResume();
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
      this.peer.addTransceiver('audio', { direction: 'recvonly' });
      this.peer.ontrack = (event) => {
        // Keep both tracks in one stream. The server timestamps them from one
        // clock, and sharing the stream prevents independent media drift.
        this._tracks.set(event.track.kind, event.track);
        // Always rebuild from both tracks. Some WebViews expose a different
        // one-track stream for each ontrack event.
        this.mediaStream = new MediaStream([...this._tracks.values()]);
        if (this.video) this.video.srcObject = this.mediaStream;
        if (event.track.kind === 'video') {
          this.video?.classList.add('visible');
          document.body.classList.add('streaming-active');
          this._setOverlay('DESKTOP STREAM');
        }
        this.video?.play().catch(() => this._armAudioResume());
        this._armAudioResume();
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
      // Non-trickle signaling still needs the LAN candidate, but should not
      // add seconds of startup delay.
      window.setTimeout(finish, 1000);
    });
  }

  _armAudioResume() {
    if (this._audioResumeArmed) return;
    this._audioResumeArmed = true;
    const resume = () => {
      if (this.video) {
        this.video.muted = false;
        this.video.defaultMuted = false;
        this.video.removeAttribute('muted');
      }
      this.video?.play().catch(() => {});
      if (this.video && !this.video.paused && !this.video.muted) {
        this._setOverlay('DESKTOP STREAM');
        window.removeEventListener('pointerdown', resume, true);
        window.removeEventListener('touchstart', resume, true);
        this._audioResumeArmed = false;
      }
    };
    window.addEventListener('pointerdown', resume, true);
    window.addEventListener('touchstart', resume, true);
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
    this._tracks.clear();
    this._audioResumeArmed = false;
    this.mediaStream?.getTracks().forEach((track) => track.stop());
    this.mediaStream = null;
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
