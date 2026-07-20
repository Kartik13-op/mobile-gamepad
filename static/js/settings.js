import { eventBus } from './utils.js';
import { ws } from './websocket.js';
import { ui } from './ui.js';

export class SettingsManager {
  constructor() {
    this._settings = {};
  }

  init() {
    eventBus.on('ws:settings', (msg) => {
      this._settings = msg.data;
      this._apply();
      this._syncPanel();
    });

    this._wirePanel();
  }

  get settings() { return this._settings; }

  _apply() {
    const s = this._settings;
    const root = document.documentElement;

    if (s.gridSize) {
      root.style.setProperty('--grid-size', `${s.gridSize}px`);
    }

    const grid = document.getElementById('workspace-grid');
    if (grid && ui.mode === 'edit') {
      grid.classList.toggle('visible', s.showGrid !== false);
    }
  }

  _syncPanel() {
    const s = this._settings;
    this._setToggle('set-snap', s.snapToGrid);
    this._setToggle('set-grid', s.showGrid);
    this._setToggle('set-haptic', s.hapticFeedback);
    this._setToggle('set-autosave', s.autoSave);

    const gridInput = document.getElementById('set-grid-size');
    if (gridInput) gridInput.value = s.gridSize || 20;
  }

  _wirePanel() {
    const toggles = [
      { id: 'set-snap', key: 'snapToGrid' },
      { id: 'set-grid', key: 'showGrid' },
      { id: 'set-haptic', key: 'hapticFeedback' },
      { id: 'set-autosave', key: 'autoSave' },
    ];

    for (const { id, key } of toggles) {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('change', () => {
          this._settings[key] = el.checked;
          this._save();
          this._apply();
        });
      }
    }

    const gridSizeInput = document.getElementById('set-grid-size');
    if (gridSizeInput) {
      gridSizeInput.addEventListener('input', () => {
        const val = parseInt(gridSizeInput.value) || 20;
        this._settings.gridSize = val;
        this._save();
        this._apply();
      });
    }
  }

  _save() {
    ws.send({ type: 'save_settings', data: this._settings });
  }

  _setToggle(id, value) {
    const el = document.getElementById(id);
    if (el) el.checked = value !== false;
  }
}

export const settingsManager = new SettingsManager();
