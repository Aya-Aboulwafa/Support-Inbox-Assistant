/**
 * Support Inbox Assistant - Centralized API Client Module
 * Provides unified, typed access to all backend REST endpoints with timeout handling.
 */

const API_BASE_URL = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
  ? `${window.location.origin}/api/v1`
  : 'http://localhost:8000/api/v1';

class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Internal request wrapper with timeout and JSON error normalization.
   */
  async _request(endpoint, options = {}, timeoutMs = 10000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errJson = await response.json();
          if (errJson.detail) errorDetail = errJson.detail;
        } catch (_) {}
        throw new Error(errorDetail);
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new Error(`Request timed out after ${timeoutMs / 1000}s`);
      }
      throw err;
    }
  }

  /**
   * Check backend health and service connectivity.
   */
  async getHealth() {
    return this._request('/health', { method: 'GET' }, 3000);
  }

  /**
   * Retrieve list of tickets with optional filters and pagination.
   */
  async listTickets({ status, category, priority, escalate, limit = 100, offset = 0 } = {}) {
    const params = new URLSearchParams();
    if (status && status !== 'all') params.append('status', status);
    if (category) params.append('category', category);
    if (priority) params.append('priority', priority);
    if (escalate !== undefined && escalate !== null) params.append('escalate', escalate);
    params.append('limit', limit);
    params.append('offset', offset);

    const query = params.toString() ? `?${params.toString()}` : '';
    return this._request(`/tickets${query}`, { method: 'GET' }, 8000);
  }

  /**
   * Retrieve queue counts and urgency metrics for badges.
   */
  async getStats() {
    return this._request('/tickets/stats', { method: 'GET' }, 4000);
  }

  /**
   * Ingest a new ticket into the review queue.
   */
  async createTicket(ticketData) {
    return this._request('/tickets', {
      method: 'POST',
      body: JSON.stringify(ticketData)
    }, 8000);
  }

  /**
   * Retrieve a specific ticket and its triage details.
   */
  async getTicket(ticketId) {
    return this._request(`/tickets/${encodeURIComponent(ticketId)}`, { method: 'GET' }, 5000);
  }

  /**
   * Trigger LLM AI Triage on an existing ticket (longer timeout for model inference).
   */
  async triageTicket(ticketId) {
    return this._request(`/tickets/${encodeURIComponent(ticketId)}/triage`, {
      method: 'POST'
    }, 30000);
  }

  /**
   * Update ticket fields (edited reply, notes, priority, category).
   */
  async updateTicket(ticketId, updates) {
    return this._request(`/tickets/${encodeURIComponent(ticketId)}`, {
      method: 'PATCH',
      body: JSON.stringify(updates)
    }, 6000);
  }

  /**
   * 1-Click Action: Approve ticket and record final response.
   */
  async approveTicket(ticketId, finalReply) {
    return this._request(`/tickets/${encodeURIComponent(ticketId)}/approve`, {
      method: 'POST',
      body: JSON.stringify({ final_reply: finalReply })
    }, 6000);
  }

  /**
   * 1-Click Action: Escalate ticket to Tier 2 support.
   */
  async escalateTicket(ticketId, reason) {
    return this._request(`/tickets/${encodeURIComponent(ticketId)}/escalate`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    }, 6000);
  }
}

// Global singleton instance
window.api = new ApiClient();
