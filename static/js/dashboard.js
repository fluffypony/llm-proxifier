// Dashboard JavaScript
class Dashboard {
    constructor() {
        this.ws = null;
        this.autoRefresh = true;
        this.refreshInterval = null;
        this.data = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupWebSocket();
        this.setupTheme();
        this.startAutoRefresh();
        this.loadData();
    }
    
    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadData();
        });
        
        // Auto-refresh toggle
        document.getElementById('auto-refresh').addEventListener('change', (e) => {
            this.autoRefresh = e.target.checked;
            if (this.autoRefresh) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });
        
        // Theme toggle
        document.getElementById('theme-toggle').addEventListener('click', () => {
            this.toggleTheme();
        });
        
        // Bulk actions
        document.getElementById('start-all-btn').addEventListener('click', () => {
            this.showConfirmModal('Start All Models', 'Start all configured models?', () => {
                this.startAllModels();
            });
        });
        
        document.getElementById('stop-all-btn').addEventListener('click', () => {
            this.showConfirmModal('Stop All Models', 'Stop all running models?', () => {
                this.stopAllModels();
            });
        });
        
        // Modal
        document.getElementById('modal-cancel').addEventListener('click', () => {
            this.hideModal();
        });
        
        document.getElementById('modal').addEventListener('click', (e) => {
            if (e.target.id === 'modal') {
                this.hideModal();
            }
        });
    }
    
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/dashboard/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            this.updateConnectionStatus(true);
            console.log('WebSocket connected');
        };
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'status_update') {
                this.updateUI(message.data);
            }
        };
        
        this.ws.onclose = () => {
            this.updateConnectionStatus(false);
            console.log('WebSocket disconnected');
            // Reconnect after 5 seconds
            setTimeout(() => this.setupWebSocket(), 5000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };
        
        // Send ping every 30 seconds to keep connection alive
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send('ping');
            }
        }, 30000);
    }
    
    setupTheme() {
        const savedTheme = localStorage.getItem('dashboard-theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        this.updateThemeButton(savedTheme);
    }
    
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('dashboard-theme', newTheme);
        this.updateThemeButton(newTheme);
    }
    
    updateThemeButton(theme) {
        const button = document.getElementById('theme-toggle');
        button.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
    
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        this.refreshInterval = setInterval(() => {
            if (this.autoRefresh) {
                this.loadData();
            }
        }, 5000);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    async loadData() {
        try {
            const response = await fetch('/dashboard/api/status');
            const data = await response.json();
            this.updateUI(data);
        } catch (error) {
            console.error('Error loading data:', error);
            this.showError('Failed to load data');
        }
    }
    
    updateUI(data) {
        this.data = data;
        this.updateSystemOverview(data);
        this.updateModels(data);
        this.updateLastUpdate();
    }
    
    updateSystemOverview(data) {
        if (data.error) {
            this.showError(data.error);
            return;
        }
        
        const system = data.system || {};
        
        // Active models
        document.getElementById('active-models').textContent = 
            `${system.active_models || 0} / ${system.total_models || 0}`;
        
        // System memory
        const memory = system.memory || {};
        const totalGB = ((memory.total || 0) / (1024 ** 3)).toFixed(1);
        const usedGB = ((memory.used || 0) / (1024 ** 3)).toFixed(1);
        const memoryPercent = memory.total ? (memory.used / memory.total * 100).toFixed(1) : 0;
        
        document.getElementById('system-memory').textContent = `${usedGB} / ${totalGB} GB`;
        document.getElementById('memory-progress').style.width = `${memoryPercent}%`;
        
        // Model memory
        const modelMemoryMB = system.total_memory_usage_mb || 0;
        document.getElementById('model-memory').textContent = `${modelMemoryMB.toFixed(0)} MB`;
    }
    
    updateModels(data) {
        const modelsGrid = document.getElementById('models-grid');
        modelsGrid.innerHTML = '';
        
        if (!data.models || Object.keys(data.models).length === 0) {
            modelsGrid.innerHTML = '<div class="card"><p>No models configured</p></div>';
            return;
        }
        
        Object.entries(data.models).forEach(([modelName, model]) => {
            const modelCard = this.createModelCard(modelName, model);
            modelsGrid.appendChild(modelCard);
        });
    }
    
    createModelCard(modelName, model) {
        const card = document.createElement('div');
        card.className = 'model-card';
        
        const statusClass = model.status === 'running' ? 'running' : 
                          model.status === 'starting' ? 'starting' : 'stopped';
        
        const statusIndicator = model.status === 'running' ? 'online' :
                               model.status === 'starting' ? 'starting' : 'offline';
        
        card.innerHTML = `
            <div class="model-header">
                <div class="model-name">${modelName}</div>
                <div class="model-status ${statusClass}">
                    <span class="status-indicator ${statusIndicator}"></span>
                    ${model.status}
                </div>
            </div>
            <div class="model-info">
                <div class="model-info-item">
                    <span class="model-info-label">Port:</span>
                    <span>${model.port}</span>
                </div>
                <div class="model-info-item">
                    <span class="model-info-label">Uptime:</span>
                    <span>${model.uptime || 'N/A'}</span>
                </div>
                <div class="model-info-item">
                    <span class="model-info-label">Memory:</span>
                    <span>${model.memory_usage_mb?.toFixed(0) || 0} MB</span>
                </div>
                <div class="model-info-item">
                    <span class="model-info-label">CPU:</span>
                    <span>${model.cpu_usage_percent?.toFixed(1) || 0}%</span>
                </div>
                <div class="model-info-item">
                    <span class="model-info-label">Requests:</span>
                    <span>${model.request_count || 0}</span>
                </div>
                <div class="model-info-item">
                    <span class="model-info-label">Context:</span>
                    <span>${model.context_length || 'N/A'}</span>
                </div>
            </div>
            <div class="model-controls">
                ${model.status === 'running' ? 
                    `<button class="btn btn-danger" onclick="dashboard.stopModel('${modelName}')">Stop</button>` :
                    `<button class="btn btn-success" onclick="dashboard.startModel('${modelName}')">Start</button>`
                }
            </div>
        `;
        
        return card;
    }
    
    async startModel(modelName) {
        try {
            const response = await fetch(`/dashboard/api/models/${modelName}/start`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess(result.message);
            } else {
                this.showError(result.message);
            }
        } catch (error) {
            console.error('Error starting model:', error);
            this.showError('Failed to start model');
        }
    }
    
    async stopModel(modelName) {
        this.showConfirmModal(
            'Stop Model',
            `Stop model "${modelName}"?`,
            async () => {
                try {
                    const response = await fetch(`/dashboard/api/models/${modelName}/stop`, {
                        method: 'POST'
                    });
                    const result = await response.json();
                    
                    if (result.success) {
                        this.showSuccess(result.message);
                    } else {
                        this.showError(result.message);
                    }
                } catch (error) {
                    console.error('Error stopping model:', error);
                    this.showError('Failed to stop model');
                }
            }
        );
    }
    
    async startAllModels() {
        if (!this.data || !this.data.models) return;
        
        const stoppedModels = Object.entries(this.data.models)
            .filter(([_, model]) => model.status !== 'running')
            .map(([name, _]) => name);
        
        for (const modelName of stoppedModels) {
            await this.startModel(modelName);
        }
    }
    
    async stopAllModels() {
        if (!this.data || !this.data.models) return;
        
        const runningModels = Object.entries(this.data.models)
            .filter(([_, model]) => model.status === 'running')
            .map(([name, _]) => name);
        
        for (const modelName of runningModels) {
            try {
                await fetch(`/dashboard/api/models/${modelName}/stop`, { method: 'POST' });
            } catch (error) {
                console.error(`Error stopping ${modelName}:`, error);
            }
        }
        
        this.showSuccess('Stopping all models...');
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('ws-status');
        const textElement = document.getElementById('ws-status-text');
        
        if (connected) {
            statusElement.className = 'status-indicator online';
            textElement.textContent = 'Connected';
        } else {
            statusElement.className = 'status-indicator offline';
            textElement.textContent = 'Disconnected';
        }
    }
    
    updateLastUpdate() {
        const now = new Date();
        document.getElementById('last-update').textContent = now.toLocaleTimeString();
    }
    
    showConfirmModal(title, message, onConfirm) {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-message').textContent = message;
        document.getElementById('modal').classList.add('show');
        
        const confirmBtn = document.getElementById('modal-confirm');
        confirmBtn.onclick = () => {
            this.hideModal();
            onConfirm();
        };
    }
    
    hideModal() {
        document.getElementById('modal').classList.remove('show');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showNotification(message, type) {
        // Simple console logging for now - could be enhanced with toast notifications
        console[type === 'error' ? 'error' : 'log'](message);
        
        // Could add toast notification here in the future
        alert(message);
    }
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new Dashboard();
});

// Make dashboard available globally for onclick handlers
window.dashboard = dashboard;
