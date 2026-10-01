import { ws } from './websocket.js';
import { eventBus } from './utils.js';

const clamp = (value) => Math.max(-1, Math.min(1, value));
const wrapDegrees = (value) => ((value + 180) % 360 + 360) % 360 - 180;
const AXES = { x: 'beta', y: 'gamma', z: 'alpha' };

export class MotionController {
  constructor() {
    this._active = new Map();
    this._outputs = new Map();
    this._physicalSticks = new Set();
    this._lastToggle = 0;
    this._orientation = this._orientation.bind(this);
    this._motion = this._motion.bind(this);
  }

  init() {
    document.addEventListener('touchkeys:sensor-toggle', event => {
      this.toggle(event.detail);
    });
    eventBus.on('layout:rendered', () => {
      for (const el of [...this._active.keys()]) if (!document.body.contains(el)) this._active.delete(el);
    });
    eventBus.on('physical-stick:start', key => this._physicalSticks.add(key));
    eventBus.on('physical-stick:end', key => {
      this._physicalSticks.delete(key);
      this._resumeSensorOutput(key);
    });
  }

  async toggle(el) {
    if (performance.now() - this._lastToggle < 500) return;
    this._lastToggle = performance.now();
    if (this._active.has(el)) {
      this._active.delete(el);
      this._updateButton(el, false, 'tap to start');
      if (!this._active.size) {
        window.removeEventListener('deviceorientation', this._orientation);
        window.removeEventListener('devicemotion', this._motion);
      }
      this._sendZero(el);
      this._outputs.delete(el);
      return;
    }
    if (!window.isSecureContext) {
      this._updateButton(el, false, 'HTTPS NOT TRUSTED');
      return;
    }
    if (typeof DeviceOrientationEvent === 'undefined') {
      this._updateButton(el, false, 'NO SENSOR API');
      return;
    }
    if (typeof DeviceOrientationEvent.requestPermission === 'function') {
      try {
        if (await DeviceOrientationEvent.requestPermission() !== 'granted') {
          this._updateButton(el, false, 'PERMISSION DENIED');
          return;
        }
      } catch (_) {
        this._updateButton(el, false, 'PERMISSION ERROR');
        return;
      }
    }
    if (typeof DeviceMotionEvent !== 'undefined' && typeof DeviceMotionEvent.requestPermission === 'function') {
      try { await DeviceMotionEvent.requestPermission(); } catch (_) { /* orientation may still work */ }
    }
    this._active.set(el, { baseline: null, last: {}, smooth: {} });
    this._updateButton(el, true, 'sensor active');
    window.addEventListener('deviceorientation', this._orientation, { passive: true });
    window.addEventListener('devicemotion', this._motion, { passive: true });
  }

  _updateButton(el, active, status = '') {
    el.classList.toggle('active', active);
    const button = el.querySelector('.sensor-toggle');
    button?.setAttribute('aria-pressed', String(active));
    if (button) button.textContent = active ? 'ON' : 'ENABLE';
    const statusEl = el.querySelector('.sensor-status');
    if (statusEl && status) statusEl.textContent = status;
  }

  _config(el) {
    try { return JSON.parse(el.dataset.sensorConfig || '{}'); } catch (_) { return {}; }
  }

  _orientation(event) {
    for (const [el, state] of this._active) {
      if (!state.baseline) state.baseline = { alpha: event.alpha || 0, beta: event.beta || 0, gamma: event.gamma || 0 };
      this._emit(el, state, event, false);
    }
  }

  _motion(event) {
    if (!event.rotationRate) return;
    for (const [el, state] of this._active) this._emit(el, state, event.rotationRate, true);
  }

  _emit(el, state, event, velocity) {
    const config = this._config(el);
    this._currentElement = el;
    for (const axis of ['x', 'y', 'z']) {
      const setting = config[axis] || {};
      const target = setting.target;
      if (!target || target === 'none') continue;
      if ((setting.mode || 'orientation') === 'velocity' !== velocity) continue;
      const source = AXES[axis];
      let raw = Number(event[source] || 0);
      if (!velocity) raw = wrapDegrees(raw - (state.baseline?.[source] || 0));
      const sensitivity = Number(setting.sensitivity ?? 1);
      let value = clamp((raw / (velocity ? 180 : 45)) * sensitivity);
      if (setting.invert) value *= -1;
      const smoothing = clamp(Number(setting.smoothing ?? 0));
      const previous = state.smooth[axis] ?? 0;
      value = previous + (value - previous) * (1 - smoothing);
      state.smooth[axis] = value;
      const now = performance.now();
      if (now - (state.last[axis] || 0) < 16) continue;
      state.last[axis] = now;
      this._sendAxis(target, value);
    }
    this._currentElement = null;
  }

  _sendAxis(target, value) {
    if (target === 'mouse_x' || target === 'mouse_y') {
      ws.send({ type: 'mouse', action: 'move', dx: target === 'mouse_x' ? Math.round(value * 24) : 0, dy: target === 'mouse_y' ? Math.round(value * 24) : 0 });
      return;
    }
    const component = target.endsWith('_y') ? 'y' : 'x';
    const gamepadTarget = target.includes('left_stick') ? 'gamepad_ls' : target.includes('right_stick') ? 'gamepad_rs' : target === 'left_trigger' ? 'gamepad_lt' : 'gamepad_rt';
    const state = this._outputs.get(this._currentElement) || {};
    const output = state[gamepadTarget] || { x: 0, y: 0 };
    output[component] = value;
    state[gamepadTarget] = output;
    this._outputs.set(this._currentElement, state);
    if (this._physicalSticks.has(gamepadTarget)) return;
    ws.send({ type: 'analog', key: gamepadTarget, x: output.x, y: output.y });
  }

  _resumeSensorOutput(gamepadTarget) {
    if (this._physicalSticks.has(gamepadTarget)) return;
    for (const output of this._outputs.values()) {
      const value = output[gamepadTarget];
      if (value) ws.send({ type: 'analog', key: gamepadTarget, x: value.x, y: value.y });
    }
  }

  _sendZero(el) {
    const config = this._config(el);
    this._currentElement = el;
    for (const axis of ['x', 'y', 'z']) {
      const target = config[axis]?.target;
      if (target && target !== 'none') this._sendAxis(target, 0);
    }
    this._currentElement = null;
  }
}

export const motion = new MotionController();
