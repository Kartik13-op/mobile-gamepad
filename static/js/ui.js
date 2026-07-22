import { eventBus } from './utils.js';

export class UIManager {
  constructor() {
    this._mode = 'play';
  }

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

  get mode() { return this._mode; }

  setMode(mode) {
    this._mode = mode;
    const playBtn = document.getElementById('btn-play');
    const editBtn = document.getElementById('btn-edit');
    if (playBtn) playBtn.classList.toggle('active', mode === 'play');
    if (editBtn) editBtn.classList.toggle('active', mode === 'edit');

    const workspace = document.getElementById('workspace');
    if (workspace) {
      workspace.classList.toggle('play-mode', mode === 'play');
      workspace.classList.toggle('edit-mode', mode === 'edit');
    }

    const grid = document.getElementById('workspace-grid');
    if (grid) grid.classList.toggle('visible', mode === 'edit');

    eventBus.emit('mode:changed', mode);
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
    
    // Will be updated via controller_changed event
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

  showModal(id) {
    const el = document.getElementById(id);
    if (el) {
      el.classList.add('open');
      const input = el.querySelector('input, select, textarea');
      if (input) setTimeout(() => input.focus(), 100);
    }
  }

  hideModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('open');
  }

  hideAllModals() {
    document.querySelectorAll('.modal-overlay.open').forEach((el) => {
      el.classList.remove('open');
    });
  }

  showToast(message, type = 'info', durationMs = 2500) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('leaving');
      toast.addEventListener('transitionend', () => toast.remove());
    }, durationMs);
  }

  showPropertiesPanel() {
    const panel = document.getElementById('properties-panel');
    if (panel) panel.classList.add('open');
  }

  hidePropertiesPanel() {
    const panel = document.getElementById('properties-panel');
    if (panel) panel.classList.remove('open');
  }

  showContextMenu(x, y, items) {
    this.hideContextMenu();
    const menu = document.getElementById('ctx-menu');
    if (!menu) return;

    menu.innerHTML = '';
    for (const item of items) {
      if (item === 'divider') {
        const div = document.createElement('div');
        div.className = 'ctx-divider';
        menu.appendChild(div);
        continue;
      }
      const btn = document.createElement('button');
      btn.className = `ctx-item${item.danger ? ' danger' : ''}`;
      btn.textContent = item.label;
      btn.addEventListener('click', () => {
        item.action();
        this.hideContextMenu();
      });
      menu.appendChild(btn);
    }

    const vw = window.innerWidth;
    const vh = window.innerHeight;
    menu.style.left = `${Math.min(x, vw - 160)}px`;
    menu.style.top = `${Math.min(y, vh - items.length * 32 - 12)}px`;
    menu.classList.add('open');

    const close = () => {
      this.hideContextMenu();
      document.removeEventListener('pointerdown', close);
    };
    setTimeout(() => document.addEventListener('pointerdown', close), 10);
  }

  hideContextMenu() {
    const menu = document.getElementById('ctx-menu');
    if (menu) menu.classList.remove('open');
  }

  toggleToolbar() {
    const toolbar = document.querySelector('.toolbar');
    const pageTabs = document.getElementById('page-tabs');
    if (toolbar) toolbar.classList.toggle('hidden');
    if (pageTabs) pageTabs.classList.toggle('hidden');
  }
}

export const ui = new UIManager();
