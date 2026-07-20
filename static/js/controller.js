import { eventBus } from './utils.js';
import { ws } from './websocket.js';

const ANALOG_DEAD_ZONE = 0.15;
const ANALOG_THROTTLE_MS = 16;
const ANALOG_CHANGE_THRESHOLD = 0.04;
const TRIGGER_MAX_DIST = 120;

export class GamepadController {
  constructor() {
    this._activeTouches = new Map();
    this._active = false;
    this._workspace = null;

    this._activeSticks = new Map();
    this._activeTriggers = new Map();

    // Workspace listeners
    this._onTouchStart = this._handleTouchStart.bind(this);
    // Document-level capture for reliable tracking outside bounds
    this._onTouchEnd = this._handleTouchEnd.bind(this);
    this._onTouchCancel = this._handleTouchEnd.bind(this);
    this._onTouchMove = this._handleTouchMove.bind(this);
    // Pointer fallback
    this._onPointerDown = this._onPointerDown.bind(this);
    this._onPointerUp = this._onPointerUp.bind(this);
    this._onPointerMove = this._onPointerMove.bind(this);
  }

  init() {
    this._workspace = document.getElementById('workspace');
  }

  activate() {
    if (this._active || !this._workspace) return;
    this._active = true;
    const opts = { passive: false };
    // Touch capture on document so out-of-bounds tracking works
    document.addEventListener('touchstart', this._onTouchStart, opts);
    document.addEventListener('touchend', this._onTouchEnd, opts);
    document.addEventListener('touchcancel', this._onTouchCancel, opts);
    document.addEventListener('touchmove', this._onTouchMove, opts);
    document.addEventListener('pointerdown', this._onPointerDown);
    document.addEventListener('pointerup', this._onPointerUp);
    document.addEventListener('pointermove', this._onPointerMove);
  }

  deactivate() {
    if (!this._active) return;
    this._active = false;
    document.removeEventListener('touchstart', this._onTouchStart);
    document.removeEventListener('touchend', this._onTouchEnd);
    document.removeEventListener('touchcancel', this._onTouchCancel);
    document.removeEventListener('touchmove', this._onTouchMove);
    document.removeEventListener('pointerdown', this._onPointerDown);
    document.removeEventListener('pointerup', this._onPointerUp);
    document.removeEventListener('pointermove', this._onPointerMove);
    this._releaseAll();
    this._resetSticks();
    this._resetTriggers();
  }

  // -----------------------------------------------------------------
  // Touch handling
  // -----------------------------------------------------------------

  _handleTouchStart(e) {
    // Only capture if initial touch is on a control
    if (!this._workspace?.contains(e.target)) return;
    e.preventDefault();
    for (const touch of e.changedTouches) {
      const el = this._findControl(touch.clientX, touch.clientY);
      if (!el) continue;

      const type = el.dataset.controlType;
      if (type === 'analog_stick') {
        this._startStick(touch.identifier, el, touch.clientX, touch.clientY);
      } else if (type === 'trigger') {
        this._startTrigger(touch.identifier, el, touch.clientX, touch.clientY);
      } else {
        this._pressButton(touch.identifier, el);
      }
    }
  }

  _handleTouchEnd(e) {
    e.preventDefault();
    for (const touch of e.changedTouches) {
      if (this._activeSticks.has(touch.identifier)) {
        this._endStick(touch.identifier);
        continue;
      }
      if (this._activeTriggers.has(touch.identifier)) {
        this._endTrigger(touch.identifier);
        continue;
      }
      const keybind = this._activeTouches.get(touch.identifier);
      if (keybind) {
        ws.send({ type: 'keyup', key: keybind });
        this._activeTouches.delete(touch.identifier);
      }
      const btn = this._findControl(touch.clientX, touch.clientY);
      if (btn) btn.classList.remove('pressed');
    }
    this._syncPressedState();
  }

  _handleTouchMove(e) {
    e.preventDefault();
    for (const touch of e.changedTouches) {
      if (this._activeSticks.has(touch.identifier)) {
        this._moveStick(touch.identifier, touch.clientX, touch.clientY);
        continue;
      }
      if (this._activeTriggers.has(touch.identifier)) {
        this._moveTrigger(touch.identifier, touch.clientX, touch.clientY);
        continue;
      }
      const currentKeybind = this._activeTouches.get(touch.identifier);
      const btn = this._findControl(touch.clientX, touch.clientY);
      const newKeybind = btn?.dataset.keybind || null;

      if (currentKeybind && newKeybind !== currentKeybind) {
        ws.send({ type: 'keyup', key: currentKeybind });
        this._activeTouches.delete(touch.identifier);
      }
      if (newKeybind && newKeybind !== currentKeybind) {
        this._activeTouches.set(touch.identifier, newKeybind);
        ws.send({ type: 'keydown', key: newKeybind });
        this._vibrate();
      }
    }
    this._syncPressedState();
  }

  // -----------------------------------------------------------------
  // Analog Stick
  // -----------------------------------------------------------------

  _startStick(touchId, el, cx, cy) {
    const rect = el.getBoundingClientRect();
    const inner = el.querySelector('.analog-inner');
    if (!inner) return;

    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const maxDist = Math.min(rect.width, rect.height) / 2 - inner.offsetWidth / 2;

    inner.classList.add('active');

    this._activeSticks.set(touchId, {
      el,
      inner,
      centerX,
      centerY,
      maxDist,
      lastSentX: 0,
      lastSentY: 0,
      lastSendTime: 0,
    });

    this._updateStickPosition(touchId, cx, cy);
  }

  _moveStick(touchId, cx, cy) {
    const stick = this._activeSticks.get(touchId);
    if (!stick) return;
    this._updateStickPosition(touchId, cx, cy);
  }

  _updateStickPosition(touchId, cx, cy) {
    const stick = this._activeSticks.get(touchId);
    if (!stick) return;

    const dx = cx - stick.centerX;
    const dy = cy - stick.centerY;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const maxDist = stick.maxDist;

    let nx, ny;
    if (dist > maxDist) {
      nx = (dx / dist) * maxDist;
      ny = (dy / dist) * maxDist;
    } else {
      nx = dx;
      ny = dy;
    }

    stick.inner.style.transform = `translate(${nx}px, ${ny}px)`;

    const rawX = dist > 0 ? nx / maxDist : 0;
    const rawY = dist > 0 ? ny / maxDist : 0;

    let finalX = 0, finalY = 0;
    const magnitude = Math.sqrt(rawX * rawX + rawY * rawY);
    if (magnitude > ANALOG_DEAD_ZONE) {
      const scaled = (magnitude - ANALOG_DEAD_ZONE) / (1 - ANALOG_DEAD_ZONE);
      const factor = scaled / magnitude;
      finalX = rawX * factor;
      finalY = rawY * factor;
    }

    const now = performance.now();
    if (now - stick.lastSendTime < ANALOG_THROTTLE_MS) return;
    stick.lastSendTime = now;

    if (Math.abs(finalX - stick.lastSentX) < ANALOG_CHANGE_THRESHOLD &&
        Math.abs(finalY - stick.lastSentY) < ANALOG_CHANGE_THRESHOLD) return;

    stick.lastSentX = finalX;
    stick.lastSentY = finalY;

    ws.send({
      type: 'analog',
      key: stick.el.dataset.keybind || 'ls',
      x: Math.round(finalX * 1000) / 1000,
      y: Math.round(finalY * 1000) / 1000,
    });
  }

  _endStick(touchId) {
    const stick = this._activeSticks.get(touchId);
    if (!stick) return;

    stick.inner.classList.remove('active');
    stick.inner.style.transform = 'translate(0px, 0px)';

    if (stick.lastSentX !== 0 || stick.lastSentY !== 0) {
      ws.send({ type: 'analog', key: stick.el.dataset.keybind || 'ls', x: 0, y: 0 });
    }

    this._activeSticks.delete(touchId);
  }

  _resetSticks() {
    this._workspace?.querySelectorAll('.analog-inner').forEach(el => {
      el.classList.remove('active');
      el.style.transform = 'translate(0px, 0px)';
    });
    this._activeSticks.clear();
  }

  // -----------------------------------------------------------------
  // Analog Trigger
  // -----------------------------------------------------------------

  _startTrigger(touchId, el, cx, cy) {
    const keybind = el.dataset.keybind;
    if (!keybind) return;

    el.classList.add('pressed');
    ws.send({ type: 'keydown', key: keybind });

    this._activeTriggers.set(touchId, {
      el,
      keybind,
      startX: cx,
      startY: cy,
      lastSentValue: 0,
      lastSendTime: 0,
    });

    this._sendTriggerValue(touchId, 0);
  }

  _moveTrigger(touchId, cx, cy) {
    const trig = this._activeTriggers.get(touchId);
    if (!trig) return;

    const dist = Math.sqrt(
      (cx - trig.startX) ** 2 + (cy - trig.startY) ** 2
    );
    const value = Math.min(dist / TRIGGER_MAX_DIST, 1.0);

    this._sendTriggerValue(touchId, value);
  }

  _sendTriggerValue(touchId, value) {
    const trig = this._activeTriggers.get(touchId);
    if (!trig) return;

    const now = performance.now();
    if (now - trig.lastSendTime < ANALOG_THROTTLE_MS) return;
    trig.lastSendTime = now;

    const snapped = Math.round(value * 100) / 100;
    if (snapped === trig.lastSentValue) return;
    trig.lastSentValue = snapped;

    ws.send({
      type: 'analog',
      key: trig.keybind,
      x: snapped,
      y: 0,
    });
  }

  _endTrigger(touchId) {
    const trig = this._activeTriggers.get(touchId);
    if (!trig) return;

    ws.send({ type: 'keyup', key: trig.keybind });
    if (trig.lastSentValue !== 0) {
      ws.send({ type: 'analog', key: trig.keybind, x: 0, y: 0 });
    }

    trig.el.classList.remove('pressed');
    this._activeTriggers.delete(touchId);
  }

  _resetTriggers() {
    for (const [id, trig] of this._activeTriggers) {
      ws.send({ type: 'keyup', key: trig.keybind });
      ws.send({ type: 'analog', key: trig.keybind, x: 0, y: 0 });
      trig.el.classList.remove('pressed');
    }
    this._activeTriggers.clear();
  }

  // -----------------------------------------------------------------
  // Pointer fallback (desktop)
  // -----------------------------------------------------------------

  _onPointerDown(e) {
    if (e.pointerType === 'touch') return;
    if (!this._workspace?.contains(e.target)) return;
    const el = this._findControl(e.clientX, e.clientY);
    if (!el) return;

    const type = el.dataset.controlType;
    if (type === 'analog_stick') {
      this._startStick(-1, el, e.clientX, e.clientY);
    } else if (type === 'trigger') {
      this._startTrigger(-1, el, e.clientX, e.clientY);
    } else {
      const keybind = el.dataset.keybind;
      if (!keybind) return;
      this._activeTouches.set(-1, keybind);
      el.classList.add('pressed');
      ws.send({ type: 'keydown', key: keybind });
    }
  }

  _onPointerUp(e) {
    if (e.pointerType === 'touch') return;
    if (this._activeSticks.has(-1)) {
      this._endStick(-1);
      return;
    }
    if (this._activeTriggers.has(-1)) {
      this._endTrigger(-1);
      return;
    }
    const keybind = this._activeTouches.get(-1);
    if (keybind) {
      ws.send({ type: 'keyup', key: keybind });
      this._activeTouches.delete(-1);
    }
    this._syncPressedState();
  }

  _onPointerMove(e) {
    if (e.pointerType === 'touch') return;
    if (this._activeSticks.has(-1)) {
      this._moveStick(-1, e.clientX, e.clientY);
    } else if (this._activeTriggers.has(-1)) {
      this._moveTrigger(-1, e.clientX, e.clientY);
    }
  }

  // -----------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------

  _pressButton(touchId, el) {
    const keybind = el.dataset.keybind;
    if (!keybind) return;
    this._activeTouches.set(touchId, keybind);
    el.classList.add('pressed');
    ws.send({ type: 'keydown', key: keybind });
    this._vibrate();
  }

  _findControl(x, y) {
    const els = document.elementsFromPoint(x, y);
    for (const el of els) {
      if (el.classList.contains('ctrl-btn')) return el;
      if (el.classList.contains('ctrl-trigger')) return el;
      if (el.classList.contains('ctrl-analog')) return el;
      if (el.closest('.ctrl-btn')) return el.closest('.ctrl-btn');
      if (el.closest('.ctrl-trigger')) return el.closest('.ctrl-trigger');
      if (el.closest('.ctrl-analog')) return el.closest('.ctrl-analog');
    }
    return null;
  }

  _syncPressedState() {
    if (!this._workspace) return;
    const activeKeybinds = new Set(this._activeTouches.values());
    for (const trig of this._activeTriggers.values()) {
      activeKeybinds.add(trig.keybind);
    }
    this._workspace.querySelectorAll('.ctrl-btn, .ctrl-trigger').forEach(el => {
      const kb = el.dataset.keybind;
      el.classList.toggle('pressed', activeKeybinds.has(kb));
    });
  }

  _releaseAll() {
    for (const keybind of this._activeTouches.values()) {
      ws.send({ type: 'keyup', key: keybind });
    }
    this._activeTouches.clear();
    if (this._workspace) {
      this._workspace.querySelectorAll('.ctrl-btn.pressed, .ctrl-trigger.pressed').forEach(el => {
        el.classList.remove('pressed');
      });
    }
  }

  _vibrate() {
    if (navigator.vibrate) {
      navigator.vibrate(10);
    }
  }
}

export const gamepadController = new GamepadController();
