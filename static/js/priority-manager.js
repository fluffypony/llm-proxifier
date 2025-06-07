/**
 * Priority Manager Component
 * Handles drag-and-drop interface for reordering model priorities
 */
class PriorityManager {
    constructor() {
        this.models = [];
        this.originalModels = [];
        this.isDirty = false;
        this.draggedElement = null;
        this.dragOverElement = null;
        
        this.initializeEventListeners();
    }

    async initialize() {
        await this.loadModels();
        this.renderPriorityList();
    }

    async loadModels() {
        try {
            const response = await fetch('/dashboard/api/models/priority');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.models = await response.json();
            this.originalModels = JSON.parse(JSON.stringify(this.models));
            return this.models;
        } catch (error) {
            console.error('Error loading models:', error);
            this.showNotification('Error loading models: ' + error.message, 'error');
            return [];
        }
    }

    renderPriorityList() {
        const listContainer = document.getElementById('priority-list');
        if (!listContainer) return;

        listContainer.innerHTML = '';

        // Sort models by priority
        const sortedModels = [...this.models].sort((a, b) => a.priority - b.priority);

        sortedModels.forEach((model, index) => {
            const item = this.createPriorityItem(model, index + 1);
            listContainer.appendChild(item);
        });

        this.updateSaveButtonState();
    }

    createPriorityItem(model, displayPriority) {
        const item = document.createElement('div');
        item.className = 'priority-item';
        item.draggable = true;
        item.dataset.modelName = model.name;
        item.dataset.originalPriority = model.priority;

        const statusClass = this.getStatusClass(model.status);
        const statusIcon = this.getStatusIcon(model.status);

        item.innerHTML = `
            <div class="drag-handle">⋮⋮</div>
            <div class="priority-number">${displayPriority}</div>
            <div class="model-info">
                <div class="model-name">${model.name}</div>
                <div class="model-details">
                    <span class="status ${statusClass}">
                        ${statusIcon} ${model.status}
                    </span>
                    <span class="resource-group">${model.resource_group}</span>
                </div>
            </div>
            <div class="model-controls">
                <label class="toggle-switch" title="Auto Start">
                    <input type="checkbox" ${model.auto_start ? 'checked' : ''} 
                           onchange="priorityManager.toggleAutoStart('${model.name}', this.checked)">
                    <span class="toggle-slider"></span>
                    <span class="toggle-label">Auto</span>
                </label>
                <label class="toggle-switch" title="Preload">
                    <input type="checkbox" ${model.preload ? 'checked' : ''} 
                           onchange="priorityManager.togglePreload('${model.name}', this.checked)">
                    <span class="toggle-slider"></span>
                    <span class="toggle-label">Pre</span>
                </label>
            </div>
            <div class="priority-input">
                <input type="number" min="1" max="10" value="${model.priority}" 
                       onchange="priorityManager.updatePriorityValue('${model.name}', this.value)">
            </div>
        `;

        // Add drag event listeners
        item.addEventListener('dragstart', (e) => this.handleDragStart(e));
        item.addEventListener('dragend', (e) => this.handleDragEnd(e));
        item.addEventListener('dragover', (e) => this.handleDragOver(e));
        item.addEventListener('drop', (e) => this.handleDrop(e));

        return item;
    }

    getStatusClass(status) {
        const statusMap = {
            'running': 'status-running',
            'stopped': 'status-stopped',
            'starting': 'status-starting',
            'error': 'status-error'
        };
        return statusMap[status] || 'status-unknown';
    }

    getStatusIcon(status) {
        const iconMap = {
            'running': '🟢',
            'stopped': '🔴',
            'starting': '🟡',
            'error': '❌'
        };
        return iconMap[status] || '⚪';
    }

    handleDragStart(e) {
        this.draggedElement = e.target.closest('.priority-item');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', this.draggedElement.outerHTML);
        this.draggedElement.classList.add('dragging');
    }

    handleDragEnd(e) {
        if (this.draggedElement) {
            this.draggedElement.classList.remove('dragging');
            this.draggedElement = null;
        }
        
        // Remove all drag-over classes
        document.querySelectorAll('.priority-item').forEach(item => {
            item.classList.remove('drag-over');
        });
    }

    handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const item = e.target.closest('.priority-item');
        if (item && item !== this.draggedElement) {
            // Remove previous drag-over indicator
            if (this.dragOverElement) {
                this.dragOverElement.classList.remove('drag-over');
            }
            
            this.dragOverElement = item;
            item.classList.add('drag-over');
        }
    }

    handleDrop(e) {
        e.preventDefault();
        
        if (!this.draggedElement || !this.dragOverElement) return;
        
        const draggedModelName = this.draggedElement.dataset.modelName;
        const targetModelName = this.dragOverElement.dataset.modelName;
        
        // Find the models and swap their priorities
        const draggedModel = this.models.find(m => m.name === draggedModelName);
        const targetModel = this.models.find(m => m.name === targetModelName);
        
        if (draggedModel && targetModel) {
            // Swap priorities
            const tempPriority = draggedModel.priority;
            draggedModel.priority = targetModel.priority;
            targetModel.priority = tempPriority;
            
            this.markDirty();
            this.renderPriorityList();
        }
    }

    toggleAutoStart(modelName, enabled) {
        const model = this.models.find(m => m.name === modelName);
        if (model) {
            model.auto_start = enabled;
            this.markDirty();
        }
    }

    togglePreload(modelName, enabled) {
        const model = this.models.find(m => m.name === modelName);
        if (model) {
            model.preload = enabled;
            this.markDirty();
        }
    }

    updatePriorityValue(modelName, newPriority) {
        const priority = parseInt(newPriority);
        if (!this.validatePriority(priority)) {
            this.showNotification('Priority must be between 1 and 10', 'error');
            this.renderPriorityList(); // Restore original value
            return;
        }

        const model = this.models.find(m => m.name === modelName);
        if (model) {
            model.priority = priority;
            this.markDirty();
            this.renderPriorityList();
        }
    }

    validatePriority(priority) {
        return Number.isInteger(priority) && priority >= 1 && priority <= 10;
    }

    markDirty() {
        this.isDirty = true;
        this.updateSaveButtonState();
    }

    updateSaveButtonState() {
        const saveButton = document.getElementById('save-priorities');
        const cancelButton = document.getElementById('cancel-priorities');
        
        if (saveButton) {
            saveButton.disabled = !this.isDirty;
            saveButton.textContent = this.isDirty ? 'Save Changes *' : 'Save Changes';
        }
        
        if (cancelButton) {
            cancelButton.disabled = !this.isDirty;
        }
    }

    async saveChanges() {
        if (!this.isDirty) return;

        try {
            const priorities = {};
            this.models.forEach(model => {
                priorities[model.name] = model.priority;
            });

            const response = await fetch('/dashboard/api/models/priority', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ model_priorities: priorities })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.originalModels = JSON.parse(JSON.stringify(this.models));
                this.isDirty = false;
                this.updateSaveButtonState();
                this.showNotification('Priorities saved successfully', 'success');
                
                // Notify dashboard of changes
                if (window.dashboardManager) {
                    window.dashboardManager.refreshStatus();
                }
            } else {
                throw new Error(result.message || 'Failed to save priorities');
            }
        } catch (error) {
            console.error('Error saving priorities:', error);
            this.showNotification('Error saving priorities: ' + error.message, 'error');
        }
    }

    cancelChanges() {
        if (!this.isDirty) return;

        this.models = JSON.parse(JSON.stringify(this.originalModels));
        this.isDirty = false;
        this.renderPriorityList();
        this.showNotification('Changes cancelled', 'info');
    }

    async batchUpdatePriorities(updates) {
        try {
            const response = await fetch('/dashboard/api/models/priority', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ model_priorities: updates })
            });

            const result = await response.json();
            if (result.success) {
                await this.loadModels();
                this.renderPriorityList();
                return result;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('Error in batch update:', error);
            throw error;
        }
    }

    initializeEventListeners() {
        // Save button event listener
        document.addEventListener('click', (e) => {
            if (e.target.id === 'save-priorities') {
                this.saveChanges();
            } else if (e.target.id === 'cancel-priorities') {
                this.cancelChanges();
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 's') {
                    e.preventDefault();
                    this.saveChanges();
                } else if (e.key === 'z') {
                    e.preventDefault();
                    this.cancelChanges();
                }
            }
        });
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
}

// Initialize global instance
window.priorityManager = new PriorityManager();
