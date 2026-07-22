import { eventBus } from './utils.js';
import { ui } from './ui.js';
import { ws } from './websocket.js';
import { layout } from './layout.js';
import { gamepadController } from './controller.js';
import { editor } from './editor.js';
import { settingsManager } from './settings.js';

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
    editor.init();
    settingsManager.init();

    document.getElementById('screen-gamepad')?.classList.remove('hidden');

    this._preventBrowserDefaults();
    this._setupWebSocketHandlers();
    this._setupActionListeners();
    this._setupKeyboardShortcuts();

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
      if (ui.mode === 'play') e.preventDefault();
    }, { passive: false });

    document.body.style.overscrollBehavior = 'none';
  }

  _setupWebSocketHandlers() {
    eventBus.on('ws:session', (msg) => {
      const gamepadScreen = document.getElementById('screen-gamepad');
      gamepadScreen?.classList.remove('hidden');
      const deviceName = navigator.userAgentData?.platform || navigator.platform || 'Mobile Controller';
      ws.send({ type: 'hello', deviceName });
      ui.setMode('play');
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

    eventBus.on('page:context', (data) => {
      ui.showContextMenu(data.el.getBoundingClientRect().left, window.innerHeight - 80, [
        {
          label: 'RENAME',
          action: () => {
            document.getElementById('rename-page-name').value = data.name;
            document.getElementById('form-rename-page').onsubmit = (e) => {
              e.preventDefault();
              const val = document.getElementById('rename-page-name').value.trim();
              if (val) {
                layout.renamePage(data.pageId, val);
                ui.hideModal('modal-rename-page');
              }
            };
            ui.showModal('modal-rename-page');
          },
        },
        {
          label: 'DELETE',
          danger: true,
          action: () => {
            document.getElementById('confirm-title').textContent = 'DELETE PAGE';
            document.getElementById('confirm-message').textContent = `Delete "${data.name}"?`;
            document.getElementById('confirm-yes').onclick = () => {
              layout.deletePage(data.pageId);
              ui.hideModal('modal-confirm');
            };
            ui.showModal('modal-confirm');
          },
        },
      ]);
    });

    document.querySelectorAll('#modal-confirm .modal-close, #confirm-no').forEach(el => {
      el.addEventListener('click', () => ui.hideModal('modal-confirm'));
    });
  }

  _setupActionListeners() {
    document.getElementById('btn-play')?.addEventListener('click', () => {
      if (ui.mode !== 'play') {
        editor.deactivate();
        ui.setMode('play');
        gamepadController.activate();
        ui.showToast('PLAY MODE');
      }
    });

    document.getElementById('btn-edit')?.addEventListener('click', () => {
      if (ui.mode !== 'edit') {
        gamepadController.deactivate();
        ui.setMode('edit');
        editor.activate();
        ui.showToast('EDIT MODE');
      }
    });

    document.getElementById('btn-undo')?.addEventListener('click', () => {
      layout.undo();
      ui.showToast('UNDO');
    });

    document.getElementById('btn-redo')?.addEventListener('click', () => {
      layout.redo();
      ui.showToast('REDO');
    });

    document.getElementById('btn-save')?.addEventListener('click', () => {
      layout.saveLayout();
    });

    document.getElementById('btn-add-control')?.addEventListener('click', () => {
      document.getElementById('add-control-type').value = 'button';
      this._populateKeybindDropdown('add-keybind');
      ui.showModal('modal-add-control');
    });

    document.getElementById('btn-add-analog')?.addEventListener('click', () => {
      document.getElementById('add-name').value = 'Analog';
      document.getElementById('add-control-type').value = 'analog_stick';
      document.getElementById('add-keybind').value = 'gamepad_ls';
      document.getElementById('add-width').value = '90';
      document.getElementById('add-height').value = '90';
      this._populateKeybindDropdown('add-keybind');
      document.getElementById('add-keybind').value = 'gamepad_ls';
      ui.showModal('modal-add-control');
    });

    document.getElementById('btn-add-trigger')?.addEventListener('click', () => {
      document.getElementById('add-name').value = 'Trigger';
      document.getElementById('add-control-type').value = 'trigger';
      document.getElementById('add-width').value = '80';
      document.getElementById('add-height').value = '48';
      this._populateKeybindDropdown('add-keybind');
      document.getElementById('add-keybind').value = 'gamepad_lt';
      ui.showModal('modal-add-control');
    });

    document.getElementById('form-add-control')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = document.getElementById('add-name').value || 'Control';
      const keybind = document.getElementById('add-keybind').value;
      const type = document.getElementById('add-control-type').value || 'button';
      const width = parseInt(document.getElementById('add-width').value, 10) || 60;
      const height = parseInt(document.getElementById('add-height').value, 10) || 60;
      const opacity = parseFloat(document.getElementById('add-opacity').value);
      const layer = parseInt(document.getElementById('add-layer').value, 10) || 0;

      layout.addControl({ name, keybind, type, width, height, opacity, layer });
      ui.hideModal('modal-add-control');
      document.getElementById('form-add-control').reset();
    });

    document.getElementById('btn-settings')?.addEventListener('click', () => {
      ui.showModal('modal-settings');
    });

    document.querySelectorAll('.modal-close, .modal-cancel').forEach(el => {
      el.addEventListener('click', () => ui.hideAllModals());
    });

    document.getElementById('prop-close')?.addEventListener('click', () => {
      ui.hidePropertiesPanel();
    });

    document.getElementById('btn-add-page')?.addEventListener('click', () => {
      document.getElementById('add-page-name').value = 'Page';
      ui.showModal('modal-add-page');
      setTimeout(() => document.getElementById('add-page-name')?.focus(), 150);
    });

    document.getElementById('form-add-page')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = document.getElementById('add-page-name').value.trim();
      if (name) {
        layout.addPage(name);
        ui.hideModal('modal-add-page');
      }
    });

    document.getElementById('btn-cog')?.addEventListener('click', () => {
      ui.toggleToolbar();
    });

    document.getElementById('btn-fullscreen')?.addEventListener('click', () => {
      this._toggleFullscreen();
    });

    document.getElementById('btn-export-layout')?.addEventListener('click', () => {
      layout.exportLayout();
    });

    document.getElementById('btn-import-layout')?.addEventListener('click', () => {
      document.getElementById('input-import-file').click();
    });

    document.getElementById('input-import-file')?.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (evt) => {
        try {
          layout.importLayout(JSON.parse(evt.target.result));
        } catch (err) {
          ui.showToast('INVALID FILE', 'error');
        }
      };
      reader.readAsText(file);
    });

    eventBus.on('mode:changed', (mode) => {
      document.querySelectorAll('.edit-only').forEach(el => {
        el.classList.toggle('hidden', mode !== 'edit');
      });
    });
  }

  _setupKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      const activeTag = document.activeElement?.tagName;
      const isInputFocused = ['INPUT', 'SELECT', 'TEXTAREA'].includes(activeTag);
      if (isInputFocused) return;

      const ctrl = e.ctrlKey || e.metaKey;
      if (ctrl && e.key.toLowerCase() === 's') {
        e.preventDefault();
        layout.saveLayout();
      } else if (ctrl && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        layout.undo();
      } else if (ctrl && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        layout.redo();
      } else if (ctrl && e.key.toLowerCase() === 'd') {
        e.preventDefault();
        if (ui.mode === 'edit') editor.duplicateSelected();
      } else if (e.key === 'Delete' && ui.mode === 'edit') {
        editor.deleteSelected();
      }
    });
  }

  _toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  }

  async _populateKeybindDropdown(selectId) {
    const select = document.getElementById(selectId);
    if (!select || select.children.length > 2) return;

    try {
      const res = await fetch('/api/keys');
      const data = await res.json();
      if (!data.keys) return;

      const fillSelect = (target) => {
        if (!target) return;
        target.innerHTML = '<option value="">None</option>';
        for (const key of data.keys) {
          const opt = document.createElement('option');
          opt.value = key;
          opt.textContent = key.toUpperCase();
          target.appendChild(opt);
        }
      };

      fillSelect(select);
      fillSelect(document.getElementById('prop-keybind'));
    } catch (err) {
      console.error('Failed to load keys:', err);
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const app = new App();
  app.init();
});
