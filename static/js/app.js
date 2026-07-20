import { eventBus } from './utils.js';
import { ws } from './websocket.js';
import { ui } from './ui.js';
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

    this._preventBrowserDefaults();
    this._setupWebSocketHandlers();
    this._setupActionListeners();
    this._setupKeyboardShortcuts();

    ws.connect();

    ui.setMode('play');
    gamepadController.activate();
  }

  _preventBrowserDefaults() {
    document.addEventListener('contextmenu', (e) => {
      e.preventDefault();
    }, { capture: true });

    document.addEventListener('gesturestart', (e) => e.preventDefault(), { passive: false });
    document.addEventListener('gesturechange', (e) => e.preventDefault(), { passive: false });
    document.addEventListener('gestureend', (e) => e.preventDefault(), { passive: false });

    document.addEventListener('touchmove', (e) => {
      if (ui.mode === 'play') {
        e.preventDefault();
      }
    }, { passive: false });

    document.body.style.overscrollBehavior = 'none';
  }

  _setupWebSocketHandlers() {
    eventBus.on('ws:connected', () => {
      ui.showToast('CONNECTED', 'success');
    });

    eventBus.on('ws:disconnected', () => {
      ui.showToast('DISCONNECTED', 'error');
    });

    eventBus.on('ws:save_result', (msg) => {
      ui.showToast(msg.success ? 'SAVED' : 'SAVE FAILED', msg.success ? 'success' : 'error');
    });

    eventBus.on('ws:export_layout', (msg) => {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(msg.data, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `gamepad_layout.json`);
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
            const newName = prompt('New name:', data.name);
            if (newName && newName.trim() !== '') {
              layout.renamePage(data.pageId, newName.trim());
            }
          }
        },
        {
          label: 'DELETE',
          danger: true,
          action: () => {
            if (confirm(`Delete "${data.name}"?`)) {
              layout.deletePage(data.pageId);
            }
          }
        }
      ]);
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
      this._populateKeybindDropdown('add-keybind');
      ui.showModal('modal-add-control');
    });

    document.getElementById('form-add-control')?.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = document.getElementById('add-name').value || 'Control';
      const keybind = document.getElementById('add-keybind').value;
      const type = document.getElementById('add-control-type').value || 'button';
      const width = parseInt(document.getElementById('add-width').value) || 60;
      const height = parseInt(document.getElementById('add-height').value) || 60;
      const opacity = parseFloat(document.getElementById('add-opacity').value);
      const layer = parseInt(document.getElementById('add-layer').value) || 0;

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
      const name = prompt('Page name:', 'Page');
      if (name && name.trim() !== '') {
        layout.addPage(name.trim());
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
          const data = JSON.parse(evt.target.result);
          layout.importLayout(data);
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
      const isInputFocused = ['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName);
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
      } else if (e.key === 'Delete') {
        if (ui.mode === 'edit') editor.deleteSelected();
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
      if (data.keys) {
        select.innerHTML = '<option value="">None</option>';
        for (const key of data.keys) {
          const opt = document.createElement('option');
          opt.value = key;
          opt.textContent = key.toUpperCase();
          select.appendChild(opt);
        }
        const propSelect = document.getElementById('prop-keybind');
        if (propSelect) {
          propSelect.innerHTML = '<option value="">None</option>';
          for (const key of data.keys) {
            const opt = document.createElement('option');
            opt.value = key;
            opt.textContent = key.toUpperCase();
            propSelect.appendChild(opt);
          }
        }
      }
    } catch (err) {
      console.error('Failed to load keys:', err);
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const app = new App();
  app.init();
});
