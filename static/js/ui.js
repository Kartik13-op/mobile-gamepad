import { eventBus } from './utils.js';

export class UIManager {
  constructor() {}

  init() {
    eventBus.on('ws:connected', () => this._setConnected(true));
    eventBus.on('ws:disconnected', () => {
      this._setConnected(false);
      this._hideDeviceName();
    });
    eventBus.on('ws:latency', (ms) => this._setLatency(ms));
    eventBus.on('ws:session', (msg) => this._setDeviceName(msg.deviceName));
    eventBus.on('ws:device_updated', (msg) => this._setDeviceName(msg.deviceName));
  }

  _setConnected(connected) {
    const badge = document.getElementById('connection-badge');
    if (!badge) return;
    badge.classList.toggle('disconnected', !connected);
    const text = badge.querySelector('.connection-text');
    if (text) text.textContent = connected ? 'ON' : 'OFF';
  }

  _setDeviceName(deviceName) {
    const info = document.getElementById('device-info');
    const display = document.getElementById('device-name-display');
    const status = document.getElementById('device-status');
    if (!info || !display) return;
    display.textContent = deviceName || 'Unknown Device';
    info.classList.remove('hidden');
    if (status) {
      status.className = 'device-status active';
      status.title = 'Active Controller';
    }
  }

  _setDeviceStatus(isActive) {
    const status = document.getElementById('device-status');
    if (!status) return;
    if (isActive) {
      status.className = 'device-status active';
      status.title = 'Active Controller';
    } else {
      status.className = 'device-status waiting';
      status.title = 'Waiting for Active Controller';
    }
  }

  _hideDeviceName() {
    const info = document.getElementById('device-info');
    if (info) info.classList.add('hidden');
  }

  _setLatency(ms) {
    const el = document.getElementById('latency-value');
    if (el) el.textContent = `${Math.round(ms)}ms`;
  }

  showToast(message, type = 'info', durationMs = 2500) {
    const container = document.getElementById('toast-container');
    if (!container) {
      const c = document.createElement('div');
      c.id = 'toast-container';
      c.className = 'toast-container';
      c.style.cssText = 'position:fixed;bottom:70px;left:50%;transform:translateX(-50%);z-index:2000;display:flex;flex-direction:column-reverse;align-items:center;gap:6px;pointer-events:none;';
      document.body.appendChild(c);
    }
    const c = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    c.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('leaving');
      toast.addEventListener('transitionend', () => toast.remove());
    }, durationMs);
  }
}

export const ui = new UIManager();
