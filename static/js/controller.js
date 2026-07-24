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
    this._touchpadStates = new Map();
    this._touchpadOffsets = new Map();
    this._lastTouchAt = 0;

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
    this._resetTouchpads();
  }

  // -----------------------------------------------------------------
  // Touch handling
  // -----------------------------------------------------------------

  _handleTouchStart(e) {
    if (!this._workspace?.contains(e.target)) return;
    this._lastTouchAt = performance.now();
    e.preventDefault();
    for (const touch of e.changedTouches) {
      const el = this._findControl(touch.clientX, touch.clientY);
      if (!el) continue;

      const type = el.dataset.controlType;
      if (type === 'analog_stick') {
        this._startStick(touch.identifier, el, touch.clientX, touch.clientY);
      } else if (type === 'trigger') {
        this._startTrigger(touch.identifier, el, touch.clientX, touch.clientY);
      } else if (type === 'touchpad') {
        this._startTouchpad(touch.identifier, el, touch.clientX, touch.clientY);
      } else {
        this._pressButton(touch.identifier, el);
      }
    }
  }

  _handleTouchEnd(e) {
    this._lastTouchAt = performance.now();
    let hasTracked = false;
    for (const touch of e.changedTouches) {
      if (this._activeSticks.has(touch.identifier) ||
          this._activeTriggers.has(touch.identifier) ||
          this._touchpadStates.has(touch.identifier) ||
          this._activeTouches.has(touch.identifier)) {
        hasTracked = true;
        break;
      }
    }
    if (hasTracked) e.preventDefault();
    for (const touch of e.changedTouches) {
      if (this._activeSticks.has(touch.identifier)) {
        this._endStick(touch.identifier);
        continue;
      }
      if (this._activeTriggers.has(touch.identifier)) {
        this._endTrigger(touch.identifier);
        continue;
      }
      if (this._touchpadStates.has(touch.identifier)) {
        this._endTouchpad(touch.identifier);
        continue;
      }
      const touchState = this._activeTouches.get(touch.identifier);
      if (touchState) {
        ws.send({ type: 'keyup', key: touchState.keybind });
        this._activeTouches.delete(touch.identifier);
        touchState.el?.classList.remove('pressed');
      }
    }
    this._syncPressedState();
  }

  _handleTouchMove(e) {
    this._lastTouchAt = performance.now();
    let hasTracked = false;
    for (const touch of e.changedTouches) {
      if (this._activeSticks.has(touch.identifier) ||
          this._activeTriggers.has(touch.identifier) ||
          this._touchpadStates.has(touch.identifier) ||
          this._activeTouches.has(touch.identifier)) {
        hasTracked = true;
        break;
      }
    }
    if (hasTracked) e.preventDefault();
    for (const touch of e.changedTouches) {
      if (this._activeSticks.has(touch.identifier)) {
        this._moveStick(touch.identifier, touch.clientX, touch.clientY);
        continue;
      }
      if (this._activeTriggers.has(touch.identifier)) {
        this._moveTrigger(touch.identifier, touch.clientX, touch.clientY);
        continue;
      }
      if (this._touchpadStates.has(touch.identifier)) {
        this._moveTouchpad(touch.identifier, touch.clientX, touch.clientY);
        continue;
      }
      const currentTouch = this._activeTouches.get(touch.identifier);
      const currentKeybind = currentTouch?.keybind || null;
      const btn = this._findControl(touch.clientX, touch.clientY);
      const newKeybind = btn?.dataset.keybind || null;

      if (currentKeybind && newKeybind !== currentKeybind) {
        ws.send({ type: 'keyup', key: currentKeybind });
        this._activeTouches.delete(touch.identifier);
        currentTouch.el?.classList.remove('pressed');
      }
      if (newKeybind && newKeybind !== currentKeybind) {
        this._activeTouches.set(touch.identifier, { keybind: newKeybind, el: btn });
        btn.classList.add('pressed');
        ws.send({ type: 'keydown', key: newKeybind });
        this._vibrate();
      }
    }
    this._syncPressedState();
  }

  // -----------------------------------------------------------------
  // Analog Stick (Dynamic Center)
  // -----------------------------------------------------------------

  _startStick(touchId, el, cx, cy) {
    const rect = el.getBoundingClientRect();
    const maxDist = Math.min(rect.width, rect.height) / 2 * 0.85;

    // Create dynamic ring centred on touch point
    const ring = document.createElement('div');
    ring.className = 'analog-ring visible';
    ring.style.width = `${maxDist * 2}px`;
    ring.style.height = `${maxDist * 2}px`;
    ring.style.left = `${cx - rect.left - maxDist}px`;
    ring.style.top = `${cy - rect.top - maxDist}px`;
    el.querySelector('.analog-outer').appendChild(ring);

    // Create dynamic dot at touch point
    const dot = document.createElement('div');
    dot.className = 'analog-dot visible';
    dot.style.left = `${cx - rect.left}px`;
    dot.style.top = `${cy - rect.top}px`;
    el.querySelector('.analog-outer').appendChild(dot);

    this._activeSticks.set(touchId, {
      el,
      ring,
      dot,
      centerX: cx,
      centerY: cy,
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

    // Position dot relative to the element, offset from initial touch point
    const elRect = stick.el.getBoundingClientRect();
    stick.dot.style.left = `${stick.centerX - elRect.left + nx}px`;
    stick.dot.style.top = `${stick.centerY - elRect.top + ny}px`;

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

    // Add touchpad offset (additive) if this stick has one
    const tpOffset = this._touchpadOffsets.get(stick.el.dataset.keybind);
    if (tpOffset) {
      finalX = Math.max(-1, Math.min(1, finalX + tpOffset.x));
      finalY = Math.max(-1, Math.min(1, finalY + tpOffset.y));
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

    // Remove dynamic elements
    stick.ring?.remove();
    stick.dot?.remove();

    if (stick.lastSentX !== 0 || stick.lastSentY !== 0) {
      ws.send({ type: 'analog', key: stick.el.dataset.keybind || 'ls', x: 0, y: 0 });
    }

    this._activeSticks.delete(touchId);
  }

  _resetSticks() {
    this._workspace?.querySelectorAll('.analog-ring, .analog-dot').forEach(el => el.remove());
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

  _resetTouchpads() {
    for (const [id, tp] of this._touchpadStates) {
      if (tp.decayTimer) { clearTimeout(tp.decayTimer); tp.decayTimer = null; }
      tp.el.classList.remove('active');
      ws.send({ type: 'analog', key: tp.keybind, x: 0, y: 0 });
    }
    this._touchpadOffsets.clear();
    this._touchpadStates.clear();
  }

  // -----------------------------------------------------------------
  // Touchpad (additive mouse-like aim)
  // -----------------------------------------------------------------

  _startTouchpad(touchId, el, cx, cy) {
    const keybind = el.dataset.keybind;
    if (!keybind) return;
    this._touchpadStates.set(touchId, {
      el, keybind,
      sensitivity: parseFloat(el.dataset.sensitivity) || 1,
      lastX: cx, lastY: cy,
      lastTime: performance.now(),
      lastSentX: 0, lastSentY: 0, lastSendTime: 0,
      decayTimer: null,
    });
    this._touchpadOffsets.set(keybind, { x: 0, y: 0 });
    el.classList.add('active');
    this._sendTouchpad(touchId, 0, 0);
    this._resendStick(keybind);
  }

  _moveTouchpad(touchId, cx, cy) {
    const tp = this._touchpadStates.get(touchId);
    if (!tp) return;
    const now = performance.now();
    const dt = Math.max(1, now - tp.lastTime);
    const vx = (cx - tp.lastX) / dt;
    const vy = (cy - tp.lastY) / dt;
    const scale = 0.5;
    let outX = vx * scale * tp.sensitivity;
    let outY = vy * scale * tp.sensitivity;
    // Acceleration curve: faster drags get proportionally more output
    outX = outX * (1 + Math.abs(outX) * 2);
    outY = outY * (1 + Math.abs(outY) * 2);
    outX = Math.max(-1, Math.min(1, outX));
    outY = Math.max(-1, Math.min(1, outY));
    tp.lastX = cx;
    tp.lastY = cy;
    tp.lastTime = now;
    // Schedule decay to 0 if the finger stops moving
    if (tp.decayTimer) clearTimeout(tp.decayTimer);
    tp.decayTimer = setTimeout(() => {
      this._touchpadOffsets.set(tp.keybind, { x: 0, y: 0 });
      this._sendTouchpad(touchId, 0, 0);
      tp.decayTimer = null;
    }, 40);
    this._touchpadOffsets.set(tp.keybind, { x: outX, y: outY });
    this._sendTouchpad(touchId, outX, outY);
  }

  _endTouchpad(touchId) {
    const tp = this._touchpadStates.get(touchId);
    if (!tp) return;
    if (tp.decayTimer) { clearTimeout(tp.decayTimer); tp.decayTimer = null; }
    tp.el.classList.remove('active');
    this._touchpadOffsets.delete(tp.keybind);
    this._touchpadStates.delete(touchId);
    // If no active stick touch for this keybind, send zero
    const hasStick = Array.from(this._activeSticks.values())
      .some(s => s.el.dataset.keybind === tp.keybind);
    if (!hasStick) {
      ws.send({ type: 'analog', key: tp.keybind, x: 0, y: 0 });
    } else {
      this._resendStick(tp.keybind);
    }
  }

  _sendTouchpad(touchId, x, y) {
    const tp = this._touchpadStates.get(touchId);
    if (!tp) return;
    const now = performance.now();
    if (now - tp.lastSendTime < ANALOG_THROTTLE_MS) return;
    tp.lastSendTime = now;
    const rx = Math.round(x * 1000) / 1000;
    const ry = Math.round(y * 1000) / 1000;
    if (rx === tp.lastSentX && ry === tp.lastSentY) return;
    tp.lastSentX = rx;
    tp.lastSentY = ry;
    // Check if the mapped stick is also active — if so, let the stick send the combined value
    const hasActiveStick = Array.from(this._activeSticks.values())
      .some(s => s.el.dataset.keybind === tp.keybind);
    if (hasActiveStick) {
      // The stick's _updateStickPosition will include touchpad offset — force a re-send
      this._resendStick(tp.keybind);
    } else {
      // Touchpad alone — send directly
      ws.send({ type: 'analog', key: tp.keybind, x: rx, y: ry });
    }
  }

  _resendStick(keybind) {
    for (const [tid, stick] of this._activeSticks) {
      if (stick.el.dataset.keybind === keybind) {
        const elRect = stick.el.getBoundingClientRect();
        const dotLeft = parseFloat(stick.dot.style.left);
        const dotTop = parseFloat(stick.dot.style.top);
        const curCx = stick.centerX + (dotLeft - (stick.centerX - elRect.left));
        const curCy = stick.centerY + (dotTop - (stick.centerY - elRect.top));
        this._updateStickPosition(tid, curCx, curCy);
      }
    }
  }

  // -----------------------------------------------------------------
  // Pointer fallback (desktop)
  // -----------------------------------------------------------------

  _onPointerDown(e) {
    if (e.pointerType === 'touch') return;
    if (performance.now() - this._lastTouchAt < 700) return;
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
      this._activeTouches.set(-1, { keybind, el });
      el.classList.add('pressed');
      ws.send({ type: 'keydown', key: keybind });
    }
  }

  _onPointerUp(e) {
    if (e.pointerType === 'touch') return;
    if (performance.now() - this._lastTouchAt < 700) return;
    if (this._activeSticks.has(-1)) {
      this._endStick(-1);
      return;
    }
    if (this._activeTriggers.has(-1)) {
      this._endTrigger(-1);
      return;
    }
    const touchState = this._activeTouches.get(-1);
    if (touchState) {
      ws.send({ type: 'keyup', key: touchState.keybind });
      this._activeTouches.delete(-1);
      touchState.el?.classList.remove('pressed');
    }
    this._syncPressedState();
  }

  _onPointerMove(e) {
    if (e.pointerType === 'touch') return;
    if (performance.now() - this._lastTouchAt < 700) return;
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
    if (this._activeTouches.has(touchId)) return;
    this._activeTouches.set(touchId, { keybind, el });
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
      if (el.classList.contains('ctrl-touchpad')) return el;
      if (el.closest('.ctrl-btn')) return el.closest('.ctrl-btn');
      if (el.closest('.ctrl-trigger')) return el.closest('.ctrl-trigger');
      if (el.closest('.ctrl-analog')) return el.closest('.ctrl-analog');
      if (el.closest('.ctrl-touchpad')) return el.closest('.ctrl-touchpad');
    }
    return null;
  }

  _syncPressedState() {
    if (!this._workspace) return;
    const activeKeybinds = new Set(
      Array.from(this._activeTouches.values(), touch => touch.keybind)
    );
    for (const trig of this._activeTriggers.values()) {
      activeKeybinds.add(trig.keybind);
    }
    this._workspace.querySelectorAll('.ctrl-btn, .ctrl-trigger').forEach(el => {
      const kb = el.dataset.keybind;
      el.classList.toggle('pressed', activeKeybinds.has(kb));
    });
  }

  _releaseAll() {
    for (const touchState of this._activeTouches.values()) {
      ws.send({ type: 'keyup', key: touchState.keybind });
      touchState.el?.classList.remove('pressed');
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
