import { eventBus } from './utils.js';
import { ui } from './ui.js';
import { ws } from './websocket.js';
import { layout } from './layout.js';
import { gamepadController } from './controller.js';

class App {
  constructor() {
    this._initialized = false;
  }

  async init() {
    if (this._initialized) return;
    this._initialized = true;

    ui.init();
    layout.init();
    gamepadController.init();

    document.getElementById('screen-gamepad')?.classList.remove('hidden');

    this._preventBrowserDefaults();
    this._setupWebSocketHandlers();
    this._setupCogButton();
    ws.connect();
  }

  _preventBrowserDefaults() {
    const isEditableTarget = (target) => {
      const el = target?.closest?.('input, textarea, select, button, [contenteditable="true"]');
      return Boolean(el);
    };

    document.addEventListener('contextmenu', (e) => {
      if (isEditableTarget(e.target)) return;
      e.preventDefault();
    }, { capture: true });

    document.addEventListener('gesturestart', (e) => e.preventDefault(), { passive: false });
    document.addEventListener('gesturechange', (e) => e.preventDefault(), { passive: false });
    document.addEventListener('gestureend', (e) => e.preventDefault(), { passive: false });

    document.addEventListener('touchmove', (e) => {
      if (isEditableTarget(e.target)) return;
      e.preventDefault();
    }, { passive: false });

    document.body.style.overscrollBehavior = 'none';
  }

  _setupWebSocketHandlers() {
    eventBus.on('ws:session', (msg) => {
      const gamepadScreen = document.getElementById('screen-gamepad');
      gamepadScreen?.classList.remove('hidden');
      const deviceName = navigator.userAgentData?.platform || navigator.platform || 'Mobile Controller';
      ws.send({ type: 'hello', deviceName });
      ui._setDeviceName(msg.deviceName || msg.clientId || 'Phone');
      ui._setDeviceStatus(Boolean(msg.isActive));
      gamepadController.activate();
      ui.showToast(msg.isActive ? 'ACTIVE CONTROLLER' : 'CONNECTED - WAITING');
    });

    eventBus.on('ws:device_updated', (msg) => {
      ui._setDeviceName(msg.deviceName || msg.clientId || 'Phone');
      ui._setDeviceStatus(Boolean(msg.isActive));
    });

    eventBus.on('ws:disconnected', () => {
      gamepadController.deactivate();
      ui.showToast('DISCONNECTED', 'error');
    });

    eventBus.on('ws:controller_changed', (msg) => {
      ui.showToast(`Now controlling: ${msg.deviceName || msg.activeClientId}`, 'info');
    });

    eventBus.on('ws:controller_activated', () => {
      ui._setDeviceStatus(true);
      ui.showToast('ACTIVE CONTROLLER', 'success');
    });

    eventBus.on('ws:save_result', (msg) => {
      ui.showToast(msg.success ? 'SAVED' : 'SAVE FAILED', msg.success ? 'success' : 'error');
    });

    eventBus.on('ws:export_layout', (msg) => {
      const dataStr = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(msg.data, null, 2))}`;
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute('href', dataStr);
      downloadAnchor.setAttribute('download', 'gamepad_layout.json');
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      ui.showToast('EXPORTED', 'success');
    });

    eventBus.on('ws:error', (msg) => {
      ui.showToast(msg.message || 'ERROR', 'error');
    });
  }

  _setupCogButton() {
    const btn = document.getElementById('btn-cog');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const toolbar = document.querySelector('.toolbar');
      const pageTabs = document.getElementById('page-tabs');
      if (toolbar) toolbar.classList.toggle('hidden');
      if (pageTabs) pageTabs.classList.toggle('hidden');
    });
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const app = new App();
  app.init();
});
