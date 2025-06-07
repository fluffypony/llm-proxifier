/**
 * Resource Group Manager Component
 * Handles resource group visualization and management
 */
class ResourceGroupManager {
    constructor() {
        this.groups = {};
        this.selectedGroup = null;
        this.refreshInterval = null;
        
        this.initializeEventListeners();
    }

    async initialize() {
        await this.loadGroups();
        this.renderGroups();
        this.startAutoRefresh();
    }

    async loadGroups() {
        try {
            const response = await fetch('/dashboard/api/groups');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.groups = await response.json();
            return this.groups;
        } catch (error) {
            console.error('Error loading resource groups:', error);
            this.showNotification('Error loading resource groups: ' + error.message, 'error');
            return {};
        }
    }

    renderGroups() {
        const container = document.getElementById('groups-grid');
        if (!container) return;

        container.innerHTML = '';

        Object.entries(this.groups).forEach(([groupName, groupData]) => {
            const groupCard = this.createGroupCard(groupName, groupData);
            container.appendChild(groupCard);
        });

        // Add "Create Group" card
        const createCard = this.createNewGroupCard();
        container.appendChild(createCard);
    }

    createGroupCard(groupName, groupData) {
        const card = document.createElement('div');
        card.className = 'group-card';
        card.dataset.groupName = groupName;

        const totalModels = groupData.models ? groupData.models.length : 0;
        const runningModels = groupData.models ? 
            groupData.models.filter(m => m.status === 'running').length : 0;
        const stoppedModels = totalModels - runningModels;

        const groupBadgeClass = this.getGroupBadgeClass(groupName);
        const groupStatus = this.getGroupStatus(groupData);
        const statusIcon = this.getStatusIcon(groupStatus);

        card.innerHTML = `
            <div class="group-header">
                <div class="group-name">
                    <span class="group-badge ${groupBadgeClass}">${groupName}</span>
                    <span class="group-status ${groupStatus}">
                        ${statusIcon} ${this.capitalizeFirst(groupStatus)}
                    </span>
                </div>
                <div class="group-actions">
                    <button class="btn btn-sm btn-success" onclick="resourceGroupManager.startGroup('${groupName}')" 
                            ${groupStatus === 'running' ? 'disabled' : ''}>
                        ▶️ Start
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="resourceGroupManager.stopGroup('${groupName}')"
                            ${groupStatus === 'stopped' ? 'disabled' : ''}>
                        ⏹️ Stop
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="resourceGroupManager.showGroupDetails('${groupName}')">
                        ℹ️ Details
                    </button>
                </div>
            </div>
            
            <div class="group-stats">
                <div class="stat-item">
                    <div class="stat-label">Total Models</div>
                    <div class="stat-value">${totalModels}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Running</div>
                    <div class="stat-value running">${runningModels}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Stopped</div>
                    <div class="stat-value stopped">${stoppedModels}</div>
                </div>
            </div>

            <div class="group-models">
                <div class="models-header">
                    <span>Models</span>
                    <button class="btn btn-xs btn-secondary" onclick="resourceGroupManager.toggleModelsVisibility('${groupName}')">
                        <span class="models-toggle">▼</span>
                    </button>
                </div>
                <div class="models-list" id="models-${groupName}" style="display: none;">
                    ${this.renderGroupModels(groupData.models || [])}
                </div>
            </div>

            <div class="group-metrics">
                <div class="metric-item">
                    <span class="metric-label">Memory Usage</span>
                    <span class="metric-value">${this.formatMemory(this.getTotalMemory(groupData.models))}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Avg CPU</span>
                    <span class="metric-value">${this.getAverageCPU(groupData.models)}%</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Total Requests</span>
                    <span class="metric-value">${this.getTotalRequests(groupData.models)}</span>
                </div>
            </div>
        `;

        return card;
    }

    createNewGroupCard() {
        const card = document.createElement('div');
        card.className = 'group-card new-group-card';
        card.innerHTML = `
            <div class="new-group-content">
                <div class="new-group-icon">➕</div>
                <div class="new-group-text">Create New Group</div>
                <button class="btn btn-primary" onclick="resourceGroupManager.showCreateGroupDialog()">
                    Create Group
                </button>
            </div>
        `;
        return card;
    }

    renderGroupModels(models) {
        if (!models || models.length === 0) {
            return '<div class="no-models">No models in this group</div>';
        }

        return models.map(model => `
            <div class="model-item ${model.status}">
                <span class="model-name">${model.name}</span>
                <span class="model-status ${model.status}">${this.getStatusIcon(model.status)}</span>
                <div class="model-actions">
                    <button class="btn btn-xs" onclick="resourceGroupManager.moveModel('${model.name}')" title="Move to another group">
                        🔄
                    </button>
                </div>
            </div>
        `).join('');
    }

    getGroupBadgeClass(groupName) {
        const badgeMap = {
            'production': 'production',
            'staging': 'staging',
            'development': 'development',
            'default': 'default'
        };
        return `group-badge-${badgeMap[groupName.toLowerCase()] || 'default'}`;
    }

    getGroupStatus(groupData) {
        if (!groupData.models || groupData.models.length === 0) {
            return 'empty';
        }

        const runningCount = groupData.models.filter(m => m.status === 'running').length;
        const totalCount = groupData.models.length;

        if (runningCount === 0) return 'stopped';
        if (runningCount === totalCount) return 'running';
        return 'partial';
    }

    getStatusIcon(status) {
        const iconMap = {
            'running': '🟢',
            'stopped': '🔴',
            'starting': '🟡',
            'partial': '🟠',
            'empty': '⚪',
            'error': '❌'
        };
        return iconMap[status] || '⚪';
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    getTotalMemory(models) {
        if (!models) return 0;
        return models.reduce((total, model) => total + (model.memory_usage_mb || 0), 0);
    }

    getAverageCPU(models) {
        if (!models || models.length === 0) return 0;
        const runningModels = models.filter(m => m.status === 'running');
        if (runningModels.length === 0) return 0;
        
        const totalCPU = runningModels.reduce((total, model) => total + (model.cpu_usage_percent || 0), 0);
        return Math.round(totalCPU / runningModels.length);
    }

    getTotalRequests(models) {
        if (!models) return 0;
        return models.reduce((total, model) => total + (model.request_count || 0), 0);
    }

    formatMemory(mb) {
        if (mb < 1024) return `${mb} MB`;
        return `${(mb / 1024).toFixed(1)} GB`;
    }

    async startGroup(groupName) {
        try {
            this.showNotification(`Starting resource group: ${groupName}`, 'info');
            
            const response = await fetch(`/dashboard/api/groups/${groupName}/start`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`Resource group '${groupName}' started successfully`, 'success');
                await this.loadGroups();
                this.renderGroups();
                
                // Notify dashboard of changes
                if (window.dashboardManager) {
                    window.dashboardManager.refreshStatus();
                }
            } else {
                throw new Error(result.message || 'Failed to start resource group');
            }
        } catch (error) {
            console.error(`Error starting resource group ${groupName}:`, error);
            this.showNotification(`Error starting resource group: ${error.message}`, 'error');
        }
    }

    async stopGroup(groupName) {
        if (!confirm(`Are you sure you want to stop all models in the '${groupName}' resource group?`)) {
            return;
        }

        try {
            this.showNotification(`Stopping resource group: ${groupName}`, 'info');
            
            const response = await fetch(`/dashboard/api/groups/${groupName}/stop`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`Resource group '${groupName}' stopped successfully`, 'success');
                await this.loadGroups();
                this.renderGroups();
                
                // Notify dashboard of changes
                if (window.dashboardManager) {
                    window.dashboardManager.refreshStatus();
                }
            } else {
                throw new Error(result.message || 'Failed to stop resource group');
            }
        } catch (error) {
            console.error(`Error stopping resource group ${groupName}:`, error);
            this.showNotification(`Error stopping resource group: ${error.message}`, 'error');
        }
    }

    showGroupDetails(groupName) {
        const groupData = this.groups[groupName];
        if (!groupData) return;

        const modal = this.createGroupDetailsModal(groupName, groupData);
        document.body.appendChild(modal);
        modal.classList.add('show');
    }

    createGroupDetailsModal(groupName, groupData) {
        const modal = document.createElement('div');
        modal.className = 'modal group-details-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Resource Group: ${groupName}</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="group-overview">
                        <h4>Overview</h4>
                        <div class="overview-stats">
                            <div class="stat">Total Models: ${groupData.models ? groupData.models.length : 0}</div>
                            <div class="stat">Running: ${groupData.models ? groupData.models.filter(m => m.status === 'running').length : 0}</div>
                            <div class="stat">Memory: ${this.formatMemory(this.getTotalMemory(groupData.models))}</div>
                        </div>
                    </div>
                    
                    <div class="models-detail">
                        <h4>Models</h4>
                        <div class="models-table">
                            ${this.createModelsTable(groupData.models || [])}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
                </div>
            </div>
        `;
        return modal;
    }

    createModelsTable(models) {
        if (!models || models.length === 0) {
            return '<div class="no-data">No models in this group</div>';
        }

        const tableRows = models.map(model => `
            <tr class="model-row ${model.status}">
                <td>${model.name}</td>
                <td><span class="status-badge ${model.status}">${this.getStatusIcon(model.status)} ${model.status}</span></td>
                <td>${model.port || 'N/A'}</td>
                <td>${this.formatMemory(model.memory_usage_mb || 0)}</td>
                <td>${model.cpu_usage_percent || 0}%</td>
                <td>${model.request_count || 0}</td>
            </tr>
        `).join('');

        return `
            <table class="models-table">
                <thead>
                    <tr>
                        <th>Model Name</th>
                        <th>Status</th>
                        <th>Port</th>
                        <th>Memory</th>
                        <th>CPU</th>
                        <th>Requests</th>
                    </tr>
                </thead>
                <tbody>
                    ${tableRows}
                </tbody>
            </table>
        `;
    }

    toggleModelsVisibility(groupName) {
        const modelsList = document.getElementById(`models-${groupName}`);
        const toggle = document.querySelector(`[onclick="resourceGroupManager.toggleModelsVisibility('${groupName}')"] .models-toggle`);
        
        if (modelsList.style.display === 'none') {
            modelsList.style.display = 'block';
            toggle.textContent = '▲';
        } else {
            modelsList.style.display = 'none';
            toggle.textContent = '▼';
        }
    }

    showCreateGroupDialog() {
        const modal = document.createElement('div');
        modal.className = 'modal create-group-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Create New Resource Group</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label for="group-name">Group Name:</label>
                        <input type="text" id="group-name" placeholder="Enter group name" maxlength="50">
                        <small>Use lowercase letters, numbers, and hyphens only</small>
                    </div>
                    <div class="form-group">
                        <label for="group-description">Description (optional):</label>
                        <textarea id="group-description" placeholder="Describe the purpose of this group"></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button class="btn btn-primary" onclick="resourceGroupManager.createGroup()">Create Group</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.classList.add('show');
        
        // Focus on name input
        setTimeout(() => {
            document.getElementById('group-name').focus();
        }, 100);
    }

    async createGroup() {
        const nameInput = document.getElementById('group-name');
        const descriptionInput = document.getElementById('group-description');
        
        const groupName = nameInput.value.trim().toLowerCase();
        const description = descriptionInput.value.trim();
        
        if (!groupName) {
            this.showNotification('Group name is required', 'error');
            return;
        }
        
        if (!/^[a-z0-9-]+$/.test(groupName)) {
            this.showNotification('Group name can only contain lowercase letters, numbers, and hyphens', 'error');
            return;
        }
        
        if (this.groups[groupName]) {
            this.showNotification('A group with this name already exists', 'error');
            return;
        }

        try {
            // For now, just add to local groups (would need backend endpoint)
            this.groups[groupName] = {
                name: groupName,
                description: description,
                models: [],
                created_at: new Date().toISOString()
            };
            
            this.renderGroups();
            this.showNotification(`Resource group '${groupName}' created successfully`, 'success');
            
            // Close modal
            document.querySelector('.create-group-modal').remove();
            
        } catch (error) {
            console.error('Error creating group:', error);
            this.showNotification('Error creating group: ' + error.message, 'error');
        }
    }

    async moveModel(modelName) {
        // This would show a dialog to select target group
        const targetGroup = prompt('Enter target resource group name:');
        if (!targetGroup || !this.groups[targetGroup]) {
            this.showNotification('Invalid target group', 'error');
            return;
        }
        
        // Implementation would require backend endpoint
        this.showNotification('Model movement not yet implemented - requires backend support', 'warning');
    }

    startAutoRefresh(interval = 10000) {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(async () => {
            await this.loadGroups();
            this.renderGroups();
        }, interval);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    initializeEventListeners() {
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 'r') {
                    e.preventDefault();
                    this.loadGroups().then(() => this.renderGroups());
                }
            }
        });
        
        // Modal backdrop click to close
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.remove();
            }
        });
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        setTimeout(() => notification.classList.add('show'), 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 3000);
    }

    destroy() {
        this.stopAutoRefresh();
    }
}

// Initialize global instance
window.resourceGroupManager = new ResourceGroupManager();
