import { eventBus, clamp, snapToGrid as snap, debounce } from './utils.js';
import { layout } from './layout.js';
import { ui } from './ui.js';

export class EditorManager {
  constructor() {
    this._active = false;
    this._workspace = null;
    this._selectedId = null;

    this._dragging = false;
    this._dragId = null;
    this._dragStartX = 0;
    this._dragStartY = 0;
    this._dragOffsetX = 0;
    this._dragOffsetY = 0;

    this._resizing = false;
    this._resizeDir = null;
    this._resizeStartX = 0;
    this._resizeStartY = 0;
    this._resizeOrigRect = null;

    this._snapEnabled = true;
    this._gridSize = 20;

    this._onPointerDown = this._handlePointerDown.bind(this);
    this._onPointerMove = this._handlePointerMove.bind(this);
    this._onPointerUp = this._handlePointerUp.bind(this);

    this._debouncedSyncProperties = debounce(() => this._syncPropertiesPanel(), 50);
  }

  init() {
    this._workspace = document.getElementById('workspace');

    eventBus.on('ws:settings', (msg) => {
      this._snapEnabled = msg.data.snapToGrid !== false;
      this._gridSize = msg.data.gridSize || 20;
    });

    this._wirePropertiesPanel();
  }

  activate() {
    if (this._active || !this._workspace) return;
    this._active = true;

    this._workspace.querySelectorAll('.ctrl-btn, .ctrl-analog, .ctrl-trigger').forEach(el => {
      el.classList.add('edit-mode');
    });

    this._renderUnsub = eventBus.on('layout:rendered', () => {
      if (this._active) {
        this._workspace.querySelectorAll('.ctrl-btn, .ctrl-analog, .ctrl-trigger').forEach(el => {
          el.classList.add('edit-mode');
        });
        if (this._selectedId) {
          const el = this._workspace.querySelector(`[data-id="${this._selectedId}"]`);
          if (el) {
            el.classList.add('selected');
          } else {
            this._selectedId = null;
            ui.hidePropertiesPanel();
          }
        }
      }
    });

    document.addEventListener('pointerdown', this._onPointerDown);
    document.addEventListener('pointermove', this._onPointerMove);
    document.addEventListener('pointerup', this._onPointerUp);
  }

  deactivate() {
    if (!this._active) return;
    this._active = false;

    if (this._renderUnsub) this._renderUnsub();

    document.removeEventListener('pointerdown', this._onPointerDown);
    document.removeEventListener('pointermove', this._onPointerMove);
    document.removeEventListener('pointerup', this._onPointerUp);

    this._deselect();
    ui.hidePropertiesPanel();

    if (this._workspace) {
      this._workspace.querySelectorAll('.ctrl-btn, .ctrl-analog, .ctrl-trigger').forEach(el => {
        el.classList.remove('edit-mode', 'selected');
      });
    }
  }

  get selectedId() { return this._selectedId; }

  deleteSelected() {
    if (this._selectedId) {
      layout.deleteControl(this._selectedId);
      this._deselect();
      ui.hidePropertiesPanel();
    }
  }

  duplicateSelected() {
    if (this._selectedId) {
      layout.duplicateControl(this._selectedId);
    }
  }

  // -----------------------------------------------------------------
  // Pointer handlers
  // -----------------------------------------------------------------

  _handlePointerDown(e) {
    if (!this._active) return;

    const handleEl = e.target.closest?.('.resize-handle');
    if (handleEl) {
      e.preventDefault();
      e.stopPropagation();
      this._startResize(handleEl, e);
      return;
    }

    const ctrlEl = e.target.closest?.('.ctrl-btn, .ctrl-analog, .ctrl-trigger');
    if (ctrlEl && this._workspace?.contains(ctrlEl)) {
      e.preventDefault();
      this._select(ctrlEl.dataset.id);
      this._startDrag(ctrlEl, e);
      return;
    }

    if (this._workspace?.contains(e.target) || e.target === this._workspace) {
      this._deselect();
      ui.hidePropertiesPanel();
    }
  }

  _handlePointerMove(e) {
    if (this._dragging) {
      e.preventDefault();
      this._onDragMove(e);
    } else if (this._resizing) {
      e.preventDefault();
      this._onResizeMove(e);
    }
  }

  _handlePointerUp(e) {
    if (this._dragging) {
      this._endDrag();
    } else if (this._resizing) {
      this._endResize();
    }
  }

  // -----------------------------------------------------------------
  // Selection
  // -----------------------------------------------------------------

  _select(id) {
    this._deselect();
    this._selectedId = id;
    const el = this._workspace?.querySelector(`[data-id="${id}"]`);
    if (el) el.classList.add('selected');
    this._syncPropertiesPanel();
    ui.showPropertiesPanel();
    eventBus.emit('editor:selected', id);
  }

  _deselect() {
    if (this._selectedId) {
      const el = this._workspace?.querySelector(`[data-id="${this._selectedId}"]`);
      if (el) el.classList.remove('selected');
    }
    this._selectedId = null;
    eventBus.emit('editor:deselected');
  }

  // -----------------------------------------------------------------
  // Drag
  // -----------------------------------------------------------------

  _startDrag(el, e) {
    this._dragging = true;
    this._dragId = el.dataset.id;
    const rect = el.getBoundingClientRect();
    this._dragOffsetX = e.clientX - rect.left;
    this._dragOffsetY = e.clientY - rect.top;
  }

  _onDragMove(e) {
    if (!this._dragId || !this._workspace) return;
    const wsRect = this._workspace.getBoundingClientRect();
    let x = e.clientX - wsRect.left - this._dragOffsetX;
    let y = e.clientY - wsRect.top - this._dragOffsetY;

    if (this._snapEnabled) {
      x = snap(x, this._gridSize);
      y = snap(y, this._gridSize);
    }

    const el = this._workspace.querySelector(`[data-id="${this._dragId}"]`);
    if (!el) return;
    const w = el.offsetWidth;
    const h = el.offsetHeight;
    x = clamp(x, 0, wsRect.width - w);
    y = clamp(y, 0, wsRect.height - h);

    el.style.left = `${x}px`;
    el.style.top = `${y}px`;

    const ctrl = layout.activeControls.find(c => c.id === this._dragId);
    if (ctrl) {
      ctrl.x = x;
      ctrl.y = y;
    }

    this._debouncedSyncProperties();
  }

  _endDrag() {
    if (this._dragId) {
      const ctrl = layout.activeControls.find(c => c.id === this._dragId);
      if (ctrl) {
        layout.updateControl(this._dragId, { x: ctrl.x, y: ctrl.y });
      }
    }
    this._dragging = false;
    this._dragId = null;
  }

  // -----------------------------------------------------------------
  // Resize
  // -----------------------------------------------------------------

  _startResize(handleEl, e) {
    const ctrlEl = handleEl.closest('.ctrl-btn, .ctrl-analog, .ctrl-trigger');
    if (!ctrlEl) return;
    this._resizing = true;
    this._resizeDir = handleEl.dataset.dir;
    this._resizeStartX = e.clientX;
    this._resizeStartY = e.clientY;
    this._dragId = ctrlEl.dataset.id;
    this._resizeOrigRect = {
      x: parseInt(ctrlEl.style.left) || 0,
      y: parseInt(ctrlEl.style.top) || 0,
      w: ctrlEl.offsetWidth,
      h: ctrlEl.offsetHeight,
    };
  }

  _onResizeMove(e) {
    if (!this._resizeOrigRect || !this._dragId || !this._workspace) return;
    const dx = e.clientX - this._resizeStartX;
    const dy = e.clientY - this._resizeStartY;
    const { x, y, w, h } = this._resizeOrigRect;
    const dir = this._resizeDir;
    const minSize = 20;

    let nx = x, ny = y, nw = w, nh = h;

    if (dir === 'se') {
      nw = Math.max(minSize, w + dx);
      nh = Math.max(minSize, h + dy);
    } else if (dir === 'sw') {
      nw = Math.max(minSize, w - dx);
      nh = Math.max(minSize, h + dy);
      nx = x + w - nw;
    } else if (dir === 'ne') {
      nw = Math.max(minSize, w + dx);
      nh = Math.max(minSize, h - dy);
      ny = y + h - nh;
    } else if (dir === 'nw') {
      nw = Math.max(minSize, w - dx);
      nh = Math.max(minSize, h - dy);
      nx = x + w - nw;
      ny = y + h - nh;
    }

    if (this._snapEnabled) {
      nx = snap(nx, this._gridSize);
      ny = snap(ny, this._gridSize);
      nw = snap(nw, this._gridSize);
      nh = snap(nh, this._gridSize);
      if (nw < minSize) nw = minSize;
      if (nh < minSize) nh = minSize;
    }

    const el = this._workspace.querySelector(`[data-id="${this._dragId}"]`);
    if (el) {
      el.style.left = `${nx}px`;
      el.style.top = `${ny}px`;
      el.style.width = `${nw}px`;
      el.style.height = `${nh}px`;
    }

    const ctrl = layout.activeControls.find(c => c.id === this._dragId);
    if (ctrl) {
      ctrl.x = nx;
      ctrl.y = ny;
      ctrl.width = nw;
      ctrl.height = nh;
    }

    this._debouncedSyncProperties();
  }

  _endResize() {
    if (this._dragId) {
      const ctrl = layout.activeControls.find(c => c.id === this._dragId);
      if (ctrl) {
        layout.updateControl(this._dragId, {
          x: ctrl.x, y: ctrl.y, width: ctrl.width, height: ctrl.height,
        });
      }
    }
    this._resizing = false;
    this._resizeDir = null;
    this._resizeOrigRect = null;
    this._dragId = null;
  }

  // -----------------------------------------------------------------
  // Properties panel
  // -----------------------------------------------------------------

  _syncPropertiesPanel() {
    if (!this._selectedId) return;
    const ctrl = layout.activeControls.find(c => c.id === this._selectedId);
    if (!ctrl) return;

    this._setField('prop-name', ctrl.name);
    this._setField('prop-keybind', ctrl.keybind);
    this._setField('prop-control-type', ctrl.type || 'button');
    this._setField('prop-x', ctrl.x);
    this._setField('prop-y', ctrl.y);
    this._setField('prop-width', ctrl.width);
    this._setField('prop-height', ctrl.height);
    this._setField('prop-font-size', ctrl.fontSize || 16);
    this._setField('prop-opacity', ctrl.opacity);
    this._setField('prop-layer', ctrl.layer || 0);
  }

  _setField(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
  }

  _wirePropertiesPanel() {
    const fields = [
      { id: 'prop-name', key: 'name', type: 'string' },
      { id: 'prop-keybind', key: 'keybind', type: 'string' },
      { id: 'prop-control-type', key: 'type', type: 'string' },
      { id: 'prop-x', key: 'x', type: 'number' },
      { id: 'prop-y', key: 'y', type: 'number' },
      { id: 'prop-width', key: 'width', type: 'number' },
      { id: 'prop-height', key: 'height', type: 'number' },
      { id: 'prop-font-size', key: 'fontSize', type: 'number' },
      { id: 'prop-opacity', key: 'opacity', type: 'number' },
      { id: 'prop-layer', key: 'layer', type: 'number' },
    ];

    for (const field of fields) {
      const el = document.getElementById(field.id);
      if (!el) continue;
      el.addEventListener('input', () => {
        if (!this._selectedId) return;
        const value = field.type === 'number' ? parseFloat(el.value) || 0 : el.value;
        layout.updateControl(this._selectedId, { [field.key]: value });
      });
    }

    const delBtn = document.getElementById('prop-delete');
    if (delBtn) delBtn.addEventListener('click', () => this.deleteSelected());

    const dupBtn = document.getElementById('prop-duplicate');
    if (dupBtn) dupBtn.addEventListener('click', () => this.duplicateSelected());
  }
}

export const editor = new EditorManager();
