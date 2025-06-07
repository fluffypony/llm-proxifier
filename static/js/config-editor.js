/**
 * Configuration Editor Component
 * Handles configuration editing with validation and backup functionality
 */
class ConfigEditor {
    constructor() {
        this.currentConfig = null;
        this.originalConfig = null;
        this.configType = 'models'; // 'models' or 'auth'
        this.isDirty = false;
        this.validationErrors = [];
        this.validationWarnings = [];
        this.backups = [];
        
        this.initializeEventListeners();
    }

    async initialize() {
        await this.loadBackups();
        await this.loadConfiguration(this.configType);
        this.renderConfigEditor();
    }

    async loadConfiguration(type = 'models') {
        try {
            this.configType = type;
            const response = await fetch(`/dashboard/api/config/${type}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.currentConfig = await response.json();
            this.originalConfig = JSON.parse(JSON.stringify(this.currentConfig));
            this.isDirty = false;
            
            this.updateEditor();
            this.validateConfiguration();
            
            return this.currentConfig;
        } catch (error) {
            console.error(`Error loading ${type} configuration:`, error);
            this.showNotification(`Error loading ${type} configuration: ${error.message}`, 'error');
            return null;
        }
    }

    async loadBackups() {
        try {
            // Mock backup data for now - would need backend endpoint
            this.backups = [
                {
                    id: 'backup-1',
                    description: 'Before priority changes',
                    timestamp: new Date(Date.now() - 86400000).toISOString(),
                    type: 'models'
                },
                {
                    id: 'backup-2', 
                    description: 'Weekly auto-backup',
                    timestamp: new Date(Date.now() - 604800000).toISOString(),
                    type: 'models'
                }
            ];
        } catch (error) {
            console.error('Error loading backups:', error);
            this.backups = [];
        }
    }

    renderConfigEditor() {
        const container = document.querySelector('.config-editor');
        if (!container) return;

        container.innerHTML = `
            <div class="config-header">
                <h2>Configuration Editor</h2>
                <div class="config-controls">
                    <select id="config-type" onchange="configEditor.switchConfigType(this.value)">
                        <option value="models" ${this.configType === 'models' ? 'selected' : ''}>Models Configuration</option>
                        <option value="auth" ${this.configType === 'auth' ? 'selected' : ''}>Auth Configuration</option>
                    </select>
                    <button class="btn btn-secondary" id="create-backup" onclick="configEditor.createBackup()">
                        💾 Create Backup
                    </button>
                    <button class="btn btn-warning" id="reload-config" onclick="configEditor.reloadConfig()">
                        🔄 Reload
                    </button>
                    <button class="btn btn-primary" id="save-config" onclick="configEditor.saveConfiguration()" ${!this.isDirty ? 'disabled' : ''}>
                        💾 Save${this.isDirty ? ' *' : ''}
                    </button>
                </div>
            </div>
            
            <div class="config-editor-container">
                <div class="editor-panel">
                    <div class="editor-toolbar">
                        <button class="btn btn-xs" onclick="configEditor.formatJson()" title="Format JSON">🎨 Format</button>
                        <button class="btn btn-xs" onclick="configEditor.validateNow()" title="Validate">✅ Validate</button>
                        <button class="btn btn-xs" onclick="configEditor.showDiff()" title="Show changes">👁️ Diff</button>
                        <span class="editor-status">${this.getEditorStatus()}</span>
                    </div>
                    <textarea id="config-textarea" class="config-textarea" 
                              onkeyup="configEditor.onEditorChange()"
                              oninput="configEditor.onEditorChange()"
                              placeholder="Loading configuration...">${this.getFormattedConfig()}</textarea>
                </div>
                
                <div class="preview-panel">
                    <div class="validation-results" id="validation-results">
                        ${this.renderValidationResults()}
                    </div>
                    <div class="backup-manager" id="backup-manager">
                        ${this.renderBackupManager()}
                    </div>
                </div>
            </div>
        `;
    }

    getFormattedConfig() {
        if (!this.currentConfig) return '';
        try {
            return JSON.stringify(this.currentConfig, null, 2);
        } catch (error) {
            return 'Error formatting configuration';
        }
    }

    getEditorStatus() {
        let status = [];
        
        if (this.isDirty) status.push('Modified');
        if (this.validationErrors.length > 0) status.push(`${this.validationErrors.length} Errors`);
        if (this.validationWarnings.length > 0) status.push(`${this.validationWarnings.length} Warnings`);
        if (status.length === 0) status.push('Valid');
        
        return status.join(' | ');
    }

    updateEditor() {
        const textarea = document.getElementById('config-textarea');
        if (textarea) {
            textarea.value = this.getFormattedConfig();
        }
        
        this.updateSaveButton();
        this.updateEditorStatus();
    }

    updateSaveButton() {
        const saveButton = document.getElementById('save-config');
        if (saveButton) {
            saveButton.disabled = !this.isDirty || this.validationErrors.length > 0;
            saveButton.textContent = `💾 Save${this.isDirty ? ' *' : ''}`;
        }
    }

    updateEditorStatus() {
        const status = document.querySelector('.editor-status');
        if (status) {
            status.textContent = this.getEditorStatus();
            status.className = `editor-status ${this.validationErrors.length > 0 ? 'error' : this.validationWarnings.length > 0 ? 'warning' : 'valid'}`;
        }
    }

    onEditorChange() {
        const textarea = document.getElementById('config-textarea');
        if (!textarea) return;

        try {
            const newConfig = JSON.parse(textarea.value);
            this.currentConfig = newConfig;
            this.isDirty = true;
            
            // Debounced validation
            clearTimeout(this.validationTimeout);
            this.validationTimeout = setTimeout(() => {
                this.validateConfiguration();
            }, 500);
            
        } catch (error) {
            this.validationErrors = [`Invalid JSON: ${error.message}`];
            this.updateValidationResults();
        }
        
        this.updateSaveButton();
        this.updateEditorStatus();
    }

    validateConfiguration() {
        this.validationErrors = [];
        this.validationWarnings = [];
        
        if (!this.currentConfig) {
            this.validationErrors.push('Configuration is empty');
            this.updateValidationResults();
            return;
        }

        if (this.configType === 'models') {
            this.validateModelsConfig();
        } else if (this.configType === 'auth') {
            this.validateAuthConfig();
        }
        
        this.updateValidationResults();
    }

    validateModelsConfig() {
        if (!this.currentConfig.models || typeof this.currentConfig.models !== 'object') {
            this.validationErrors.push('Configuration must have a "models" object');
            return;
        }

        Object.entries(this.currentConfig.models).forEach(([modelName, config]) => {
            // Required fields
            if (!config.model_path) {
                this.validationErrors.push(`Model "${modelName}": model_path is required`);
            }
            
            if (!config.port) {
                this.validationErrors.push(`Model "${modelName}": port is required`);
            } else if (typeof config.port !== 'number' || config.port < 1 || config.port > 65535) {
                this.validationErrors.push(`Model "${modelName}": port must be a number between 1 and 65535`);
            }
            
            // Optional validations
            if (config.priority && (typeof config.priority !== 'number' || config.priority < 1 || config.priority > 10)) {
                this.validationWarnings.push(`Model "${modelName}": priority should be between 1 and 10`);
            }
            
            if (config.gpu_layers && typeof config.gpu_layers !== 'number') {
                this.validationWarnings.push(`Model "${modelName}": gpu_layers should be a number`);
            }
            
            if (config.context_length && typeof config.context_length !== 'number') {
                this.validationWarnings.push(`Model "${modelName}": context_length should be a number`);
            }
        });
    }

    validateAuthConfig() {
        if (this.currentConfig.enabled && typeof this.currentConfig.enabled !== 'boolean') {
            this.validationErrors.push('enabled field must be a boolean');
        }
        
        if (this.currentConfig.api_keys && !Array.isArray(this.currentConfig.api_keys)) {
            this.validationErrors.push('api_keys must be an array');
        }
        
        if (this.currentConfig.rate_limits && typeof this.currentConfig.rate_limits !== 'object') {
            this.validationErrors.push('rate_limits must be an object');
        }
    }

    validateNow() {
        this.validateConfiguration();
        this.showNotification(`Validation complete: ${this.validationErrors.length} errors, ${this.validationWarnings.length} warnings`, 
                            this.validationErrors.length > 0 ? 'error' : 'success');
    }

    renderValidationResults() {
        let html = '<h4>Validation Results</h4>';
        
        if (this.validationErrors.length === 0 && this.validationWarnings.length === 0) {
            html += '<div class="validation-success">✅ Configuration is valid</div>';
        } else {
            if (this.validationErrors.length > 0) {
                html += '<div class="validation-errors"><h5>Errors:</h5><ul>';
                this.validationErrors.forEach(error => {
                    html += `<li class="error">❌ ${error}</li>`;
                });
                html += '</ul></div>';
            }
            
            if (this.validationWarnings.length > 0) {
                html += '<div class="validation-warnings"><h5>Warnings:</h5><ul>';
                this.validationWarnings.forEach(warning => {
                    html += `<li class="warning">⚠️ ${warning}</li>`;
                });
                html += '</ul></div>';
            }
        }
        
        return html;
    }

    updateValidationResults() {
        const container = document.getElementById('validation-results');
        if (container) {
            container.innerHTML = this.renderValidationResults();
        }
        this.updateSaveButton();
        this.updateEditorStatus();
    }

    renderBackupManager() {
        let html = '<h4>Backup Management</h4>';
        
        if (this.backups.length === 0) {
            html += '<div class="no-backups">No backups available</div>';
        } else {
            html += '<div class="backups-list">';
            this.backups
                .filter(backup => backup.type === this.configType)
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                .forEach(backup => {
                    html += `
                        <div class="backup-item">
                            <div class="backup-info">
                                <div class="backup-description">${backup.description}</div>
                                <div class="backup-timestamp">${this.formatTimestamp(backup.timestamp)}</div>
                            </div>
                            <div class="backup-actions">
                                <button class="btn btn-xs btn-primary" onclick="configEditor.restoreBackup('${backup.id}')" title="Restore this backup">
                                    🔄 Restore
                                </button>
                                <button class="btn btn-xs btn-danger" onclick="configEditor.deleteBackup('${backup.id}')" title="Delete this backup">
                                    🗑️ Delete
                                </button>
                            </div>
                        </div>
                    `;
                });
            html += '</div>';
        }
        
        return html;
    }

    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }

    async switchConfigType(type) {
        if (this.isDirty && !confirm('You have unsaved changes. Switch configuration type?')) {
            // Reset the dropdown
            document.getElementById('config-type').value = this.configType;
            return;
        }
        
        await this.loadConfiguration(type);
        this.renderConfigEditor();
    }

    async reloadConfig() {
        if (this.isDirty && !confirm('You have unsaved changes. Reload from server?')) {
            return;
        }
        
        await this.loadConfiguration(this.configType);
        this.updateEditor();
        this.showNotification('Configuration reloaded', 'info');
    }

    async saveConfiguration() {
        if (!this.isDirty || this.validationErrors.length > 0) return;
        
        try {
            const response = await fetch(`/dashboard/api/config/${this.configType}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ config_data: this.currentConfig })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.originalConfig = JSON.parse(JSON.stringify(this.currentConfig));
                this.isDirty = false;
                this.updateSaveButton();
                this.showNotification(`${this.configType} configuration saved successfully`, 'success');
                
                // Refresh dashboard if needed
                if (window.dashboardManager) {
                    window.dashboardManager.refreshStatus();
                }
            } else {
                throw new Error(result.message || 'Failed to save configuration');
            }
        } catch (error) {
            console.error('Error saving configuration:', error);
            this.showNotification(`Error saving configuration: ${error.message}`, 'error');
        }
    }

    formatJson() {
        try {
            const textarea = document.getElementById('config-textarea');
            if (!textarea) return;
            
            const config = JSON.parse(textarea.value);
            textarea.value = JSON.stringify(config, null, 2);
            this.onEditorChange();
            this.showNotification('JSON formatted', 'info');
        } catch (error) {
            this.showNotification(`Error formatting JSON: ${error.message}`, 'error');
        }
    }

    showDiff() {
        if (!this.originalConfig || !this.currentConfig) {
            this.showNotification('No changes to compare', 'info');
            return;
        }
        
        const modal = this.createDiffModal();
        document.body.appendChild(modal);
        modal.classList.add('show');
    }

    createDiffModal() {
        const modal = document.createElement('div');
        modal.className = 'modal config-diff-modal';
        
        const originalJson = JSON.stringify(this.originalConfig, null, 2);
        const currentJson = JSON.stringify(this.currentConfig, null, 2);
        
        modal.innerHTML = `
            <div class="modal-content wide">
                <div class="modal-header">
                    <h3>Configuration Changes</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="diff-container">
                        <div class="diff-panel">
                            <h4>Original</h4>
                            <pre class="config-diff original">${this.escapeHtml(originalJson)}</pre>
                        </div>
                        <div class="diff-panel">
                            <h4>Current</h4>
                            <pre class="config-diff current">${this.escapeHtml(currentJson)}</pre>
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

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    async createBackup() {
        const description = prompt('Enter backup description:', `Manual backup - ${new Date().toLocaleString()}`);
        if (!description) return;
        
        try {
            // For now, just add to local backups (would need backend endpoint)
            const backup = {
                id: `backup-${Date.now()}`,
                description: description,
                timestamp: new Date().toISOString(),
                type: this.configType,
                config: JSON.parse(JSON.stringify(this.currentConfig))
            };
            
            this.backups.unshift(backup);
            this.updateBackupManager();
            this.showNotification('Backup created successfully', 'success');
            
        } catch (error) {
            console.error('Error creating backup:', error);
            this.showNotification('Error creating backup: ' + error.message, 'error');
        }
    }

    async restoreBackup(backupId) {
        const backup = this.backups.find(b => b.id === backupId);
        if (!backup) {
            this.showNotification('Backup not found', 'error');
            return;
        }
        
        if (!confirm(`Restore backup "${backup.description}"? This will overwrite current changes.`)) {
            return;
        }
        
        try {
            // For now, just restore from local backup (would need backend endpoint)
            this.currentConfig = JSON.parse(JSON.stringify(backup.config));
            this.isDirty = true;
            this.updateEditor();
            this.validateConfiguration();
            this.showNotification(`Backup "${backup.description}" restored`, 'success');
            
        } catch (error) {
            console.error('Error restoring backup:', error);
            this.showNotification('Error restoring backup: ' + error.message, 'error');
        }
    }

    async deleteBackup(backupId) {
        const backup = this.backups.find(b => b.id === backupId);
        if (!backup) return;
        
        if (!confirm(`Delete backup "${backup.description}"?`)) return;
        
        this.backups = this.backups.filter(b => b.id !== backupId);
        this.updateBackupManager();
        this.showNotification('Backup deleted', 'info');
    }

    updateBackupManager() {
        const container = document.getElementById('backup-manager');
        if (container) {
            container.innerHTML = this.renderBackupManager();
        }
    }

    initializeEventListeners() {
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 's') {
                    e.preventDefault();
                    this.saveConfiguration();
                } else if (e.key === 'r') {
                    e.preventDefault();
                    this.reloadConfig();
                } else if (e.key === 'd') {
                    e.preventDefault();
                    this.showDiff();
                }
            }
        });
        
        // Modal backdrop click to close
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.remove();
            }
        });
        
        // Warn before page unload if dirty
        window.addEventListener('beforeunload', (e) => {
            if (this.isDirty) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
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
        clearTimeout(this.validationTimeout);
    }
}

// Initialize global instance
window.configEditor = new ConfigEditor();
