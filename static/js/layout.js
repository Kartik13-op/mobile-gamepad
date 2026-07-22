import { eventBus, generateId } from './utils.js';
import { ws } from './websocket.js';

const DEFAULT_CONTROL = {
  id: '',
  name: 'Button',
  type: 'button',
  keybind: '',
  x: 0.5,
  y: 0.5,
  width: 60,
  height: 60,
  opacity: 1.0,
  fontSize: 16,
  layer: 0,
  visible: true,
};

export class LayoutManager {
  constructor() {
    this._layout = null;
    this._workspace = null;
    this._settings = null;
  }

  init() {
    this._workspace = document.getElementById('workspace');

    eventBus.on('ws:layout', (msg) => {
      this.setLayout(msg.data);
    });

    eventBus.on('ws:active_page', (msg) => {
      if (this._layout) {
        this._layout.activePageIndex = msg.index;
        this._renderPageTabs();
        this._renderControls();
      }
    });

    eventBus.on('ws:settings', (msg) => {
      this._settings = msg.data;
    });
  }

  get layout() { return this._layout; }
  get pages() { return this._layout?.pages || []; }
  get activePageIndex() { return this._layout?.activePageIndex ?? 0; }
  get activePage() { return this.pages[this.activePageIndex] || null; }
  get activePageId() { return this.activePage?.id || null; }

  get activeControls() {
    return this.activePage?.buttons || [];
  }

  setLayout(data) {
    this._layout = data;
    this._migratePositions();
    this._renderPageTabs();
    this._renderControls();
    eventBus.emit('layout:changed', data);
  }

  _migratePositions() {
    const ws = this._workspace;
    if (!ws) return;
    const w = ws.clientWidth || window.innerWidth;
    const h = ws.clientHeight || window.innerHeight;
    for (const page of this.pages) {
      for (const btn of (page.buttons || [])) {
        if (btn.x > 1) btn.x = btn.x / w;
        if (btn.y > 1) btn.y = btn.y / h;
      }
    }
  }

  switchPage(index) {
    if (!this._layout) return;
    if (index < 0 || index >= this.pages.length) return;
    this._layout.activePageIndex = index;
    this._renderPageTabs();
    this._renderControls();
    ws.send({ type: 'set_active_page', index });
    eventBus.emit('layout:page_changed', index);
  }

  addControl(controlData = {}) {
    const pageId = this.activePageId;
    if (!pageId) return;
    const data = { ...DEFAULT_CONTROL, ...controlData };
    ws.send({ type: 'add_button', pageId, data });
  }

  updateControl(controlId, updates) {
    const pageId = this.activePageId;
    if (!pageId) return;
    const ctrl = this.activeControls.find(c => c.id === controlId);
    if (ctrl) {
      Object.assign(ctrl, updates);
      this._applyControlStyle(controlId, ctrl);
    }
    ws.send({ type: 'update_button', pageId, buttonId: controlId, data: updates });
  }

  deleteControl(controlId) {
    const pageId = this.activePageId;
    if (!pageId) return;
    ws.send({ type: 'delete_button', pageId, buttonId: controlId });
  }

  duplicateControl(controlId) {
    const pageId = this.activePageId;
    if (!pageId) return;
    ws.send({ type: 'duplicate_button', pageId, buttonId: controlId });
  }

  addPage(name = 'New Page') {
    ws.send({ type: 'add_page', name });
  }

  deletePage(pageId) {
    ws.send({ type: 'delete_page', pageId });
  }

  renamePage(pageId, name) {
    ws.send({ type: 'rename_page', pageId, name });
  }

  saveLayout() {
    ws.send({ type: 'save_layout', data: this._layout });
  }

  undo() { ws.send({ type: 'undo' }); }
  redo() { ws.send({ type: 'redo' }); }
  exportLayout() { ws.send({ type: 'export_layout' }); }
  importLayout(data) { ws.send({ type: 'import_layout', data }); }

  // -----------------------------------------------------------------
  // Rendering
  // -----------------------------------------------------------------

  _renderControls() {
    if (!this._workspace) return;

    this._workspace.querySelectorAll('.ctrl-btn, .ctrl-analog, .ctrl-trigger').forEach(el => el.remove());

    let emptyState = this._workspace.querySelector('.empty-state');
    const controls = this.activeControls;

    if (controls.length === 0) {
      if (!emptyState) {
        emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        emptyState.innerHTML = `
          <span class="empty-icon">🎮</span>
          <span class="empty-text">NO CONTROLS</span>
          <span class="empty-hint">ADD CONTROLS IN EDIT MODE</span>
        `;
        this._workspace.appendChild(emptyState);
      }
    } else {
      if (emptyState) emptyState.remove();
    }

    for (const ctrl of controls) {
      if (ctrl.visible === false) continue;
      this._createControlElement(ctrl);
    }

    eventBus.emit('layout:rendered');
  }

  _createControlElement(ctrl) {
    const type = ctrl.type || 'button';

    if (type === 'analog_stick') {
      this._createAnalogStick(ctrl);
    } else if (type === 'trigger') {
      this._createTrigger(ctrl);
    } else {
      this._createButton(ctrl);
    }
  }

  _createButton(ctrl) {
    const el = document.createElement('div');
    el.className = 'ctrl-btn';
    el.dataset.id = ctrl.id;
    el.dataset.keybind = ctrl.keybind || '';
    el.dataset.controlType = 'button';

    el.innerHTML = `
      <div class="resize-handle nw" data-dir="nw"></div>
      <div class="resize-handle ne" data-dir="ne"></div>
      <div class="resize-handle sw" data-dir="sw"></div>
      <div class="resize-handle se" data-dir="se"></div>
      <span class="btn-label">${ctrl.name || ''}</span>
      ${ctrl.keybind ? `<span class="btn-keybind">${ctrl.keybind}</span>` : ''}
    `;

    this._applyBaseStyles(el, ctrl);
    this._workspace.appendChild(el);
  }

  _createAnalogStick(ctrl) {
    const el = document.createElement('div');
    el.className = 'ctrl-analog';
    el.dataset.id = ctrl.id;
    el.dataset.keybind = ctrl.keybind || '';
    el.dataset.controlType = 'analog_stick';

    el.innerHTML = `
      <div class="resize-handle nw" data-dir="nw"></div>
      <div class="resize-handle ne" data-dir="ne"></div>
      <div class="resize-handle sw" data-dir="sw"></div>
      <div class="resize-handle se" data-dir="se"></div>
      <div class="analog-outer">
        <div class="analog-inner" style="width:${Math.min(ctrl.width || 60, ctrl.height || 60) * 0.4}px;height:${Math.min(ctrl.width || 60, ctrl.height || 60) * 0.4}px;"></div>
      </div>
      <span class="btn-label">${ctrl.name || ''}</span>
    `;

    el.style.left = `${ctrl.x * 100}%`;
    el.style.top = `${ctrl.y * 100}%`;
    el.style.width = `${ctrl.width}px`;
    el.style.height = `${ctrl.height}px`;
    el.style.opacity = ctrl.opacity ?? 1;
    el.style.zIndex = ctrl.layer || 1;

    this._workspace.appendChild(el);
  }

  _createTrigger(ctrl) {
    const el = document.createElement('div');
    el.className = 'ctrl-trigger';
    el.dataset.id = ctrl.id;
    el.dataset.keybind = ctrl.keybind || '';
    el.dataset.controlType = 'trigger';

    el.innerHTML = `
      <div class="resize-handle nw" data-dir="nw"></div>
      <div class="resize-handle ne" data-dir="ne"></div>
      <div class="resize-handle sw" data-dir="sw"></div>
      <div class="resize-handle se" data-dir="se"></div>
      ${ctrl.name || ''}
    `;

    this._applyBaseStyles(el, ctrl);
    this._workspace.appendChild(el);
  }

  _applyBaseStyles(el, ctrl) {
    el.style.left = `${ctrl.x * 100}%`;
    el.style.top = `${ctrl.y * 100}%`;
    el.style.width = `${ctrl.width}px`;
    el.style.height = `${ctrl.height}px`;
    el.style.opacity = ctrl.opacity ?? 1;
    el.style.zIndex = ctrl.layer || 1;
    if (ctrl.fontSize) {
      el.style.fontSize = `${ctrl.fontSize}px`;
    }
  }

  _applyControlStyle(controlId, ctrl) {
    const selector = `[data-id="${controlId}"]`;
    const el = this._workspace?.querySelector(selector);
    if (!el) return;

    el.style.left = `${ctrl.x * 100}%`;
    el.style.top = `${ctrl.y * 100}%`;
    el.style.width = `${ctrl.width}px`;
    el.style.height = `${ctrl.height}px`;
    el.style.opacity = ctrl.opacity ?? 1;
    el.style.zIndex = ctrl.layer || 1;
    if (ctrl.fontSize) {
      el.style.fontSize = `${ctrl.fontSize}px`;
    }

    const label = el.querySelector('.btn-label');
    if (label) label.textContent = ctrl.name || '';
    const kb = el.querySelector('.btn-keybind');
    if (kb) kb.textContent = ctrl.keybind || '';
  }

  // -----------------------------------------------------------------
  // Page tabs
  // -----------------------------------------------------------------

  _renderPageTabs() {
    const container = document.getElementById('page-tabs-list');
    if (!container) return;

    container.innerHTML = '';
    const pages = this.pages;

    for (let i = 0; i < pages.length; i++) {
      const page = pages[i];
      const tab = document.createElement('button');
      tab.className = `page-tab${i === this.activePageIndex ? ' active' : ''}`;
      tab.textContent = page.name;
      tab.dataset.pageId = page.id;
      tab.dataset.index = String(i);
      tab.addEventListener('click', () => this.switchPage(i));

      let pressTimer = 0;
      tab.addEventListener('pointerdown', () => {
        pressTimer = setTimeout(() => {
          eventBus.emit('page:context', { pageId: page.id, name: page.name, index: i, el: tab });
        }, 600);
      });
      tab.addEventListener('pointerup', () => clearTimeout(pressTimer));
      tab.addEventListener('pointerleave', () => clearTimeout(pressTimer));

      container.appendChild(tab);
    }
  }
}

export const layout = new LayoutManager();
