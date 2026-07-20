/**
 * TouchKeys — WebSocket connection manager.
 * Handles auto-reconnect, heartbeat, and latency measurement.
 * @module websocket
 */

import { eventBus } from './utils.js';

/** @type {number} Heartbeat interval in ms */
const HEARTBEAT_MS = 3000;

/** @type {number} Initial reconnect delay in ms */
const RECONNECT_BASE_MS = 500;

/** @type {number} Maximum reconnect delay in ms */
const RECONNECT_MAX_MS = 8000;

export class WebSocketManager {
  constructor() {
    /** @type {WebSocket|null} */
    this._ws = null;
    /** @type {boolean} */
    this._connected = false;
    /** @type {number} */
    this._latency = 0;
    /** @type {number} */
    this._reconnectDelay = RECONNECT_BASE_MS;
    /** @type {number} */
    this._heartbeatTimer = 0;
    /** @type {number} */
    this._reconnectTimer = 0;
    /** @type {boolean} */
    this._intentionalClose = false;
  }

  /** Whether the socket is currently connected. */
  get connected() { return this._connected; }

  /** Last measured round-trip latency in ms. */
  get latency() { return this._latency; }

  /**
   * Open a WebSocket connection to the server.
   * Automatically determines the ws:// URL from the current host.
   */
  connect() {
    this._intentionalClose = false;
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${protocol}://${location.host}/ws`;

    try {
      this._ws = new WebSocket(url);
    } catch (err) {
      console.error('[WS] Failed to create WebSocket:', err);
      this._scheduleReconnect();
      return;
    }

    this._ws.onopen = () => {
      this._connected = true;
      this._reconnectDelay = RECONNECT_BASE_MS;
      this._startHeartbeat();
      eventBus.emit('ws:connected');
      console.log('[WS] Connected');
    };

    this._ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        this._handleMessage(msg);
      } catch (err) {
        console.error('[WS] Bad message:', err);
      }
    };

    this._ws.onclose = () => {
      this._onDisconnect();
    };

    this._ws.onerror = (err) => {
      console.error('[WS] Error:', err);
      // onclose will fire after onerror
    };
  }

  /**
   * Send a JSON message to the server.
   * @param {object} data
   */
  send(data) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(data));
    }
  }

  /**
   * Gracefully close the connection.
   */
  disconnect() {
    this._intentionalClose = true;
    this._stopHeartbeat();
    clearTimeout(this._reconnectTimer);
    if (this._ws) {
      this._ws.close();
      this._ws = null;
    }
    this._connected = false;
  }

  // -----------------------------------------------------------
  // Internal
  // -----------------------------------------------------------

  /** @param {object} msg */
  _handleMessage(msg) {
    const { type } = msg;

    if (type === 'pong') {
      const now = Date.now();
      this._latency = now - (msg.timestamp || now);
      eventBus.emit('ws:latency', this._latency);
      return;
    }

    // Emit typed events for other modules to handle
    eventBus.emit(`ws:${type}`, msg);
  }

  _onDisconnect() {
    const wasConnected = this._connected;
    this._connected = false;
    this._stopHeartbeat();
    if (wasConnected) {
      eventBus.emit('ws:disconnected');
      console.log('[WS] Disconnected');
    }
    if (!this._intentionalClose) {
      this._scheduleReconnect();
    }
  }

  _scheduleReconnect() {
    clearTimeout(this._reconnectTimer);
    console.log(`[WS] Reconnecting in ${this._reconnectDelay}ms …`);
    this._reconnectTimer = setTimeout(() => {
      this._reconnectDelay = Math.min(this._reconnectDelay * 1.5, RECONNECT_MAX_MS);
      this.connect();
    }, this._reconnectDelay);
  }

  _startHeartbeat() {
    this._stopHeartbeat();
    this._heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping', timestamp: Date.now() });
    }, HEARTBEAT_MS);
  }

  _stopHeartbeat() {
    clearInterval(this._heartbeatTimer);
  }
}

/** Singleton instance used by all modules. */
export const ws = new WebSocketManager();
