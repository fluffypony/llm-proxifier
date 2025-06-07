// Dashboard JavaScript
class DashboardManager {
    constructor() {
        this.ws = null;
        this.autoRefresh = true;
        this.refreshInterval = null;
        this.data = null;
        this.currentTab = 'overview';
        this.components = {};
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupWebSocket();
        this.setupTheme();
        this.setupTabs();
        this.initializeComponents();
        this.startAutoRefresh();
        this.loadData();
    }
    
    initializeComponents() {
        // Initialize new component instances
        this.components.priorityManager = window.priorityManager;
        this.components.resourceGroupManager = window.resourceGroupManager;
        this.components.queueMonitor = window.queueMonitor;
        this.components.configEditor = window.configEditor;
        
        // Initialize components when their tabs are first shown
        this.componentInitialized = {
            overview: true, // Always initialized
            priority: false,
            groups: false,
            queues: false,
            config: false
        };
    }
    
    setupTabs() {
        // Add tab navigation functionality
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.dataset.tab;
                this.switchTab(tabName);
            });
        });
        
        // Add keyboard shortcuts for tab switching
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case '1':
                        e.preventDefault();
                        this.switchTab('overview');
                        break;
                    case '2':
                        e.preventDefault();
                        this.switchTab('priority');
                        break;
                    case '3':
                        e.preventDefault();
                        this.switchTab('groups');
                        break;
                    case '4':
                        e.preventDefault();
                        this.switchTab('queues');
                        break;
                    case '5':
                        e.preventDefault();
                        this.switchTab('config');
                        break;
                }
            }
        });
    }
    
    switchTab(tabName) {
        // Update active tab button
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
        
        // Hide all tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.style.display = 'none';
        });
        
        // Show selected tab content
        const selectedTab = document.getElementById(`${tabName}-tab`);
        if (selectedTab) {
            selectedTab.style.display = 'block';
        }
        
        // Initialize component if not already done
        if (!this.componentInitialized[tabName] && this.components[this.getComponentName(tabName)]) {
            this.initializeTabComponent(tabName);
            this.componentInitialized[tabName] = true;
        }
        
        this.currentTab = tabName;
        
        // Update URL hash without triggering reload
        window.history.replaceState(null, null, `#${tabName}`);
    }
    
    getComponentName(tabName) {
        const componentMap = {
            'priority': 'priorityManager',
            'groups': 'resourceGroupManager',
            'queues': 'queueMonitor',
            'config': 'configEditor'
        };
        return componentMap[tabName];
    }
    
    async initializeTabComponent(tabName) {
        try {
            switch(tabName) {
                case 'priority':
                    if (this.components.priorityManager) {
                        await this.components.priorityManager.initialize();
                    }
                    break;
                case 'groups':
                    if (this.components.resourceGroupManager) {
                        await this.components.resourceGroupManager.initialize();
                    }
                    break;
                case 'queues':
                    if (this.components.queueMonitor) {
                        await this.components.queueMonitor.initialize();
                    }
                    break;
                case 'config':
                    if (this.components.configEditor) {
                        await this.components.configEditor.initialize();
                    }
                    break;
            }
        } catch (error) {
            console.error(`Error initializing ${tabName} component:`, error);
            this.showNotification(`Error loading ${tabName} tab: ${error.message}`, 'error');
        }
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
        
        // Notify components of data updates
        this.notifyComponents(data);
    }
    
    notifyComponents(data) {
        // Update components with new data if they're initialized
        if (this.componentInitialized.priority && this.components.priorityManager) {
            // Priority manager will handle its own refresh
        }
        
        if (this.componentInitialized.groups && this.components.resourceGroupManager) {
            // Resource group manager will handle its own refresh
        }
        
        if (this.componentInitialized.queues && this.components.queueMonitor) {
            // Queue monitor handles its own auto-refresh
        }
    }
    
    // Public method for components to refresh dashboard data
    async refreshStatus() {
        await this.loadData();
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
        card.dataset.modelName = modelName;
        
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
                <div class="model-priority" title="Priority: ${model.priority || 5}">
                    P${model.priority || 5}
                </div>
                <div class="model-group" title="Resource Group: ${model.resource_group || 'default'}">
                    <span class="group-badge">${model.resource_group || 'default'}</span>
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
                <div class="control-group">
                    ${model.status === 'running' ? 
                        `<button class="btn btn-danger" onclick="dashboardManager.stopModel('${modelName}')">Stop</button>` :
                        `<button class="btn btn-success" onclick="dashboardManager.startModel('${modelName}')">Start</button>`
                    }
                    <button class="btn btn-secondary btn-sm" onclick="dashboardManager.showModelDetails('${modelName}')" title="Model Details">
                        📊
                    </button>
                </div>
                <div class="bulk-select">
                    <input type="checkbox" id="select-${modelName}" name="model-select" value="${modelName}">
                    <label for="select-${modelName}" title="Select for bulk actions"></label>
                </div>
            </div>
        `;
        
        return card;
    }
    
    showModelDetails(modelName) {
        const model = this.data?.models?.[modelName];
        if (!model) return;
        
        const modal = this.createModelDetailsModal(modelName, model);
        document.body.appendChild(modal);
        modal.classList.add('show');
    }
    
    createModelDetailsModal(modelName, model) {
        const modal = document.createElement('div');
        modal.className = 'modal model-details-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Model Details: ${modelName}</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Status:</span>
                            <span class="detail-value ${model.status}">${model.status}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Port:</span>
                            <span class="detail-value">${model.port}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Priority:</span>
                            <span class="detail-value">${model.priority || 5}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Resource Group:</span>
                            <span class="detail-value">${model.resource_group || 'default'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Model Path:</span>
                            <span class="detail-value">${model.model_path || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Context Length:</span>
                            <span class="detail-value">${model.context_length || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">GPU Layers:</span>
                            <span class="detail-value">${model.gpu_layers || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Uptime:</span>
                            <span class="detail-value">${model.uptime || 'N/A'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Memory Usage:</span>
                            <span class="detail-value">${model.memory_usage_mb?.toFixed(0) || 0} MB</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">CPU Usage:</span>
                            <span class="detail-value">${model.cpu_usage_percent?.toFixed(1) || 0}%</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Request Count:</span>
                            <span class="detail-value">${model.request_count || 0}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Last Accessed:</span>
                            <span class="detail-value">${model.last_accessed || 'Never'}</span>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
                    ${model.status === 'running' ? 
                        `<button class="btn btn-danger" onclick="dashboardManager.stopModel('${modelName}'); this.closest('.modal').remove();">Stop Model</button>` :
                        `<button class="btn btn-success" onclick="dashboardManager.startModel('${modelName}'); this.closest('.modal').remove();">Start Model</button>`
                    }
                </div>
            </div>
        `;
        return modal;
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
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Add to page
        const container = document.body;
        container.appendChild(notification);
        
        // Show with animation
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Remove after delay
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => container.removeChild(notification), 300);
        }, 3000);
    }
    
    // Handle bulk operations
    handleBulkOperations() {
        const selectedModels = this.getSelectedModels();
        if (selectedModels.length === 0) {
            this.showNotification('No models selected', 'warning');
            return;
        }
        
        // Add bulk action buttons if not already present
        this.addBulkActionButtons();
    }
    
    getSelectedModels() {
        const checkboxes = document.querySelectorAll('input[name="model-select"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }
    
    addBulkActionButtons() {
        let bulkActions = document.querySelector('.bulk-actions');
        if (!bulkActions) {
            bulkActions = document.createElement('div');
            bulkActions.className = 'bulk-actions';
            bulkActions.innerHTML = `
                <div class="bulk-actions-content">
                    <span class="selected-count">0 models selected</span>
                    <button class="btn btn-success btn-sm" onclick="dashboardManager.bulkStartSelected()">Start Selected</button>
                    <button class="btn btn-danger btn-sm" onclick="dashboardManager.bulkStopSelected()">Stop Selected</button>
                    <button class="btn btn-secondary btn-sm" onclick="dashboardManager.clearSelection()">Clear Selection</button>
                </div>
            `;
            
            const modelsGrid = document.getElementById('models-grid');
            modelsGrid.parentNode.insertBefore(bulkActions, modelsGrid);
        }
        
        // Update selected count
        const selectedCount = this.getSelectedModels().length;
        const countSpan = bulkActions.querySelector('.selected-count');
        countSpan.textContent = `${selectedCount} models selected`;
        
        // Show/hide bulk actions
        bulkActions.style.display = selectedCount > 0 ? 'block' : 'none';
    }
    
    async bulkStartSelected() {
        const selectedModels = this.getSelectedModels();
        for (const modelName of selectedModels) {
            await this.startModel(modelName);
        }
        this.clearSelection();
    }
    
    async bulkStopSelected() {
        const selectedModels = this.getSelectedModels();
        if (!confirm(`Stop ${selectedModels.length} selected models?`)) return;
        
        for (const modelName of selectedModels) {
            try {
                await fetch(`/dashboard/api/models/${modelName}/stop`, { method: 'POST' });
            } catch (error) {
                console.error(`Error stopping ${modelName}:`, error);
            }
        }
        this.clearSelection();
    }
    
    clearSelection() {
        document.querySelectorAll('input[name="model-select"]').forEach(cb => {
            cb.checked = false;
        });
        this.addBulkActionButtons(); // Update UI
    }
    
    // Initialize from URL hash
    initializeFromHash() {
        const hash = window.location.hash.substring(1);
        if (hash && ['overview', 'priority', 'groups', 'queues', 'config'].includes(hash)) {
            this.switchTab(hash);
        }
    }
    
    destroy() {
        // Clean up components
        Object.values(this.components).forEach(component => {
            if (component && typeof component.destroy === 'function') {
                component.destroy();
            }
        });
        
        this.stopAutoRefresh();
        
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Initialize dashboard when page loads
let dashboardManager;
document.addEventListener('DOMContentLoaded', () => {
    dashboardManager = new DashboardManager();
    
    // Initialize from URL hash
    dashboardManager.initializeFromHash();
    
    // Add event listeners for model selection
    document.addEventListener('change', (e) => {
        if (e.target.name === 'model-select') {
            dashboardManager.addBulkActionButtons();
        }
    });
    
    // Modal backdrop click to close
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.remove();
        }
    });
});

// Make dashboard available globally for onclick handlers
window.dashboardManager = dashboardManager;
