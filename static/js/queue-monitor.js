/**
 * Queue Monitor Component
 * Handles real-time queue monitoring and visualization
 */
class QueueMonitor {
    constructor() {
        this.queueData = {};
        this.historicalData = {};
        this.charts = {};
        this.refreshInterval = null;
        this.refreshRate = 5000; // 5 seconds default
        this.maxHistoryPoints = 60; // Keep last 60 data points
        this.isPaused = false;
        this.errorCount = 0;
        this.isOnline = navigator.onLine;
        
        this.initializeEventListeners();
        this.setupOfflineDetection();
    }

    async initialize() {
        await this.loadQueueStatus();
        this.renderQueueDashboard();
        this.initializeCharts();
        this.startAutoRefresh();
    }

    async loadQueueStatus() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);
            
            const response = await fetch('/dashboard/api/queue/status', {
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                // Enhanced error handling based on status code
                if (response.status === 503) {
                    throw new Error('Queue manager temporarily unavailable');
                } else if (response.status >= 500) {
                    throw new Error(`Server error: ${response.status}`);
                } else if (response.status === 404) {
                    throw new Error('Queue status endpoint not found');
                } else {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            }
            
            const newData = await response.json();
            
            // Validate response format
            if (!this.validateQueueData(newData)) {
                throw new Error('Invalid queue data format received');
            }
            
            this.queueData = newData;
            this.updateHistoricalData(newData);
            
            // Clear any previous error state
            this.clearErrorState();
            
            return newData;
        } catch (error) {
            console.error('Error loading queue status:', error);
            
            // Enhanced error handling with retry logic
            this.handleLoadError(error);
            return {};
        }
    }

    updateHistoricalData(newData) {
        const timestamp = Date.now();
        
        if (!this.historicalData.timestamps) {
            this.historicalData.timestamps = [];
        }
        
        this.historicalData.timestamps.push(timestamp);
        
        // Process queue data for each model
        Object.entries(newData).forEach(([modelName, queueInfo]) => {
            if (!this.historicalData[modelName]) {
                this.historicalData[modelName] = {
                    depth: [],
                    avgWaitTime: [],
                    throughput: []
                };
            }
            
            this.historicalData[modelName].depth.push(queueInfo.depth || 0);
            this.historicalData[modelName].avgWaitTime.push(queueInfo.avg_wait_time || 0);
            this.historicalData[modelName].throughput.push(queueInfo.requests_per_minute || 0);
        });
        
        // Limit history size
        if (this.historicalData.timestamps.length > this.maxHistoryPoints) {
            const excess = this.historicalData.timestamps.length - this.maxHistoryPoints;
            this.historicalData.timestamps.splice(0, excess);
            
            Object.keys(this.historicalData).forEach(key => {
                if (key !== 'timestamps' && this.historicalData[key].depth) {
                    this.historicalData[key].depth.splice(0, excess);
                    this.historicalData[key].avgWaitTime.splice(0, excess);
                    this.historicalData[key].throughput.splice(0, excess);
                }
            });
        }
    }

    validateQueueData(data) {
        // Validate that data has expected structure
        if (!data || typeof data !== 'object') return false;
        
        for (const [modelName, queueInfo] of Object.entries(data)) {
            if (!queueInfo || typeof queueInfo !== 'object') return false;
            // Check for required fields
            const requiredFields = ['depth', 'avg_wait_time', 'requests_per_minute'];
            for (const field of requiredFields) {
                if (queueInfo[field] === undefined) return false;
            }
        }
        return true;
    }

    handleLoadError(error) {
        this.errorCount = (this.errorCount || 0) + 1;
        
        // Show error in UI
        this.showErrorState(error.message);
        
        // Implement exponential backoff for retries
        if (this.errorCount < 5) {
            const retryDelay = Math.min(1000 * Math.pow(2, this.errorCount), 30000);
            setTimeout(() => {
                this.loadQueueStatus();
            }, retryDelay);
        } else {
            // Stop auto-refresh after 5 consecutive failures
            this.stopAutoRefresh();
            this.showNotification('Auto-refresh disabled due to repeated errors. Click refresh to try again.', 'error');
        }
    }

    showErrorState(message) {
        const container = document.getElementById('queue-dashboard');
        if (!container) return;
        
        const errorBanner = document.createElement('div');
        errorBanner.className = 'error-banner';
        errorBanner.innerHTML = `
            <div class="error-content">
                <span class="error-icon">⚠️</span>
                <span class="error-message">${message}</span>
                <button class="btn btn-sm btn-secondary" onclick="queueMonitor.refreshNow()">Retry</button>
            </div>
        `;
        
        // Remove existing error banner
        const existingBanner = container.querySelector('.error-banner');
        if (existingBanner) {
            existingBanner.remove();
        }
        
        container.insertBefore(errorBanner, container.firstChild);
    }

    clearErrorState() {
        this.errorCount = 0;
        const errorBanner = document.querySelector('.error-banner');
        if (errorBanner) {
            errorBanner.remove();
        }
    }

    setupOfflineDetection() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.clearErrorState();
            this.showNotification('Connection restored', 'success');
            if (!this.isPaused) {
                this.startAutoRefresh();
            }
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.stopAutoRefresh();
            this.showErrorState('No internet connection');
        });
    }

    renderQueueDashboard() {
        const container = document.getElementById('queue-dashboard');
        if (!container) return;

        container.innerHTML = `
            <div class="queue-controls-panel">
                <div class="controls-group">
                    <button class="btn btn-secondary" id="refresh-now" onclick="queueMonitor.refreshNow()">
                        🔄 Refresh Now
                    </button>
                    <button class="btn btn-warning" id="pause-monitoring" onclick="queueMonitor.togglePause()">
                        ${this.isPaused ? '▶️ Resume' : '⏸️ Pause'}
                    </button>
                    <button class="btn btn-danger" id="clear-all-queues" onclick="queueMonitor.clearAllQueues()">
                        🗑️ Clear All Queues
                    </button>
                </div>
                <div class="refresh-control">
                    <label for="refresh-interval">Refresh Rate:</label>
                    <select id="refresh-interval" onchange="queueMonitor.setRefreshRate(this.value)">
                        <option value="1000">1s</option>
                        <option value="5000" selected>5s</option>
                        <option value="10000">10s</option>
                        <option value="30000">30s</option>
                    </select>
                </div>
            </div>
            
            <div class="queue-overview">
                ${this.renderQueueOverview()}
            </div>
            
            <div class="queue-models">
                ${this.renderQueueModels()}
            </div>
            
            <div class="queue-charts">
                <div class="chart-container">
                    <h3>Queue Depth Over Time</h3>
                    <canvas id="queue-depth-chart"></canvas>
                </div>
                <div class="chart-container">
                    <h3>Average Wait Time</h3>
                    <canvas id="wait-time-chart"></canvas>
                </div>
                <div class="chart-container">
                    <h3>Throughput (Requests/Min)</h3>
                    <canvas id="throughput-chart"></canvas>
                </div>
            </div>
        `;
    }

    renderQueueOverview() {
        let totalDepth = 0;
        let totalModels = 0;
        let activeQueues = 0;
        let avgWaitTime = 0;
        let totalThroughput = 0;

        Object.values(this.queueData).forEach(queueInfo => {
            totalModels++;
            totalDepth += queueInfo.depth || 0;
            totalThroughput += queueInfo.requests_per_minute || 0;
            
            if (queueInfo.depth > 0) {
                activeQueues++;
                avgWaitTime += queueInfo.avg_wait_time || 0;
            }
        });

        if (activeQueues > 0) {
            avgWaitTime = avgWaitTime / activeQueues;
        }

        return `
            <div class="overview-stats">
                <div class="stat-card ${totalDepth > 50 ? 'alert' : totalDepth > 20 ? 'warning' : ''}">
                    <div class="stat-label">Total Queue Depth</div>
                    <div class="stat-value">${totalDepth}</div>
                    <div class="stat-subtitle">Across ${totalModels} models</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Active Queues</div>
                    <div class="stat-value">${activeQueues}</div>
                    <div class="stat-subtitle">Out of ${totalModels} models</div>
                </div>
                <div class="stat-card ${avgWaitTime > 30 ? 'alert' : avgWaitTime > 10 ? 'warning' : ''}">
                    <div class="stat-label">Avg Wait Time</div>
                    <div class="stat-value">${this.formatTime(avgWaitTime)}</div>
                    <div class="stat-subtitle">Seconds</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Total Throughput</div>
                    <div class="stat-value">${Math.round(totalThroughput)}</div>
                    <div class="stat-subtitle">Requests/min</div>
                </div>
            </div>
        `;
    }

    renderQueueModels() {
        const models = Object.entries(this.queueData).map(([modelName, queueInfo]) => {
            const alertLevel = this.getQueueAlertLevel(queueInfo);
            const alertIcon = this.getAlertIcon(alertLevel);
            
            return `
                <div class="queue-model-card ${alertLevel}">
                    <div class="model-header">
                        <span class="model-name">${modelName}</span>
                        <span class="alert-icon">${alertIcon}</span>
                        <div class="model-actions">
                            <button class="btn btn-xs btn-secondary" onclick="queueMonitor.clearModelQueue('${modelName}')" 
                                    title="Clear queue for this model"
                                    ${(queueInfo.depth || 0) === 0 ? 'disabled' : ''}>
                                🗑️ Clear
                            </button>
                            <button class="btn btn-xs btn-primary" onclick="queueMonitor.showModelDetails('${modelName}')" 
                                    title="Show detailed queue information">
                                📊 Details
                            </button>
                        </div>
                    </div>
                    
                    <div class="model-metrics">
                        <div class="metric">
                            <span class="metric-label">Queue Depth</span>
                            <span class="metric-value ${this.getDepthClass(queueInfo.depth)}">${queueInfo.depth || 0}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Wait Time</span>
                            <span class="metric-value">${this.formatTime(queueInfo.avg_wait_time || 0)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Requests/Min</span>
                            <span class="metric-value">${Math.round(queueInfo.requests_per_minute || 0)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Processed</span>
                            <span class="metric-value">${queueInfo.total_processed || 0}</span>
                        </div>
                    </div>
                    
                    <div class="queue-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${Math.min(100, (queueInfo.depth || 0) / 10 * 100)}%"></div>
                        </div>
                        <span class="progress-text">${Math.min(100, Math.round((queueInfo.depth || 0) / 10 * 100))}% capacity</span>
                    </div>
                </div>
            `;
        });

        return `
            <div class="models-grid">
                ${models.join('')}
            </div>
        `;
    }

    getQueueAlertLevel(queueInfo) {
        const depth = queueInfo.depth || 0;
        const waitTime = queueInfo.avg_wait_time || 0;
        
        if (depth > 50 || waitTime > 30) return 'alert';
        if (depth > 20 || waitTime > 10) return 'warning';
        return 'normal';
    }

    getAlertIcon(level) {
        const icons = {
            'alert': '🚨',
            'warning': '⚠️',
            'normal': '✅'
        };
        return icons[level] || '⚪';
    }

    getDepthClass(depth) {
        if (depth > 50) return 'critical';
        if (depth > 20) return 'high';
        if (depth > 0) return 'moderate';
        return 'normal';
    }

    formatTime(seconds) {
        if (seconds < 1) return '< 1s';
        if (seconds < 60) return `${Math.round(seconds)}s`;
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.round(seconds % 60);
        return `${minutes}m ${remainingSeconds}s`;
    }

    initializeCharts() {
        // Initialize Chart.js charts
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js not loaded, skipping chart initialization');
            return;
        }

        this.initDepthChart();
        this.initWaitTimeChart();
        this.initThroughputChart();
    }

    initDepthChart() {
        const ctx = document.getElementById('queue-depth-chart');
        if (!ctx) return;

        this.charts.depth = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Queue Depth'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
        
        this.updateDepthChart();
    }

    initWaitTimeChart() {
        const ctx = document.getElementById('wait-time-chart');
        if (!ctx) return;

        this.charts.waitTime = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Wait Time (seconds)'
                        }
                    }
                }
            }
        });
        
        this.updateWaitTimeChart();
    }

    initThroughputChart() {
        const ctx = document.getElementById('throughput-chart');
        if (!ctx) return;

        this.charts.throughput = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Requests per Minute'
                        }
                    }
                }
            }
        });
        
        this.updateThroughputChart();
    }

    updateCharts() {
        this.updateDepthChart();
        this.updateWaitTimeChart();
        this.updateThroughputChart();
    }

    updateDepthChart() {
        if (!this.charts.depth || !this.historicalData.timestamps) return;

        const labels = this.historicalData.timestamps.map(ts => 
            new Date(ts).toLocaleTimeString()
        );

        const datasets = Object.keys(this.historicalData)
            .filter(key => key !== 'timestamps' && this.historicalData[key].depth)
            .map((modelName, index) => ({
                label: modelName,
                data: this.historicalData[modelName].depth,
                borderColor: this.getChartColor(index),
                backgroundColor: this.getChartColor(index, 0.1),
                tension: 0.1
            }));

        this.charts.depth.data.labels = labels;
        this.charts.depth.data.datasets = datasets;
        this.charts.depth.update('none');
    }

    updateWaitTimeChart() {
        if (!this.charts.waitTime || !this.historicalData.timestamps) return;

        const labels = this.historicalData.timestamps.map(ts => 
            new Date(ts).toLocaleTimeString()
        );

        const datasets = Object.keys(this.historicalData)
            .filter(key => key !== 'timestamps' && this.historicalData[key].avgWaitTime)
            .map((modelName, index) => ({
                label: modelName,
                data: this.historicalData[modelName].avgWaitTime,
                borderColor: this.getChartColor(index),
                backgroundColor: this.getChartColor(index, 0.1),
                tension: 0.1
            }));

        this.charts.waitTime.data.labels = labels;
        this.charts.waitTime.data.datasets = datasets;
        this.charts.waitTime.update('none');
    }

    updateThroughputChart() {
        if (!this.charts.throughput || !this.historicalData.timestamps) return;

        const labels = this.historicalData.timestamps.map(ts => 
            new Date(ts).toLocaleTimeString()
        );

        const datasets = Object.keys(this.historicalData)
            .filter(key => key !== 'timestamps' && this.historicalData[key].throughput)
            .map((modelName, index) => ({
                label: modelName,
                data: this.historicalData[modelName].throughput,
                borderColor: this.getChartColor(index),
                backgroundColor: this.getChartColor(index, 0.1),
                tension: 0.1
            }));

        this.charts.throughput.data.labels = labels;
        this.charts.throughput.data.datasets = datasets;
        this.charts.throughput.update('none');
    }

    getChartColor(index, alpha = 1) {
        const colors = [
            `rgba(255, 99, 132, ${alpha})`,
            `rgba(54, 162, 235, ${alpha})`,
            `rgba(255, 205, 86, ${alpha})`,
            `rgba(75, 192, 192, ${alpha})`,
            `rgba(153, 102, 255, ${alpha})`,
            `rgba(255, 159, 64, ${alpha})`
        ];
        return colors[index % colors.length];
    }

    async clearModelQueue(modelName) {
        if (!confirm(`Clear queue for model "${modelName}"?`)) return;

        try {
            const response = await fetch(`/dashboard/api/queue/${modelName}/clear`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`Queue cleared for model "${modelName}"`, 'success');
                await this.refreshNow();
            } else {
                throw new Error(result.message || 'Failed to clear queue');
            }
        } catch (error) {
            console.error(`Error clearing queue for ${modelName}:`, error);
            this.showNotification(`Error clearing queue: ${error.message}`, 'error');
        }
    }

    async clearAllQueues() {
        if (!confirm('Clear ALL queues? This action cannot be undone.')) return;

        const modelNames = Object.keys(this.queueData);
        let cleared = 0;
        let errors = 0;

        for (const modelName of modelNames) {
            try {
                const response = await fetch(`/dashboard/api/queue/${modelName}/clear`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    cleared++;
                } else {
                    errors++;
                }
            } catch (error) {
                errors++;
            }
        }

        this.showNotification(`Cleared ${cleared} queues${errors > 0 ? `, ${errors} errors` : ''}`, 
                            errors > 0 ? 'warning' : 'success');
        await this.refreshNow();
    }

    showModelDetails(modelName) {
        const queueInfo = this.queueData[modelName];
        if (!queueInfo) return;

        const modal = this.createDetailsModal(modelName, queueInfo);
        document.body.appendChild(modal);
        modal.classList.add('show');
    }

    createDetailsModal(modelName, queueInfo) {
        const modal = document.createElement('div');
        modal.className = 'modal queue-details-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Queue Details: ${modelName}</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Current Queue Depth:</span>
                            <span class="detail-value">${queueInfo.depth || 0}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Average Wait Time:</span>
                            <span class="detail-value">${this.formatTime(queueInfo.avg_wait_time || 0)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Requests per Minute:</span>
                            <span class="detail-value">${Math.round(queueInfo.requests_per_minute || 0)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Total Processed:</span>
                            <span class="detail-value">${queueInfo.total_processed || 0}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Peak Queue Depth:</span>
                            <span class="detail-value">${queueInfo.peak_depth || 0}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Last Activity:</span>
                            <span class="detail-value">${queueInfo.last_activity || 'Never'}</span>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
                    <button class="btn btn-danger" onclick="queueMonitor.clearModelQueue('${modelName}'); this.closest('.modal').remove();">
                        Clear Queue
                    </button>
                </div>
            </div>
        `;
        return modal;
    }

    async refreshNow() {
        await this.loadQueueStatus();
        this.renderQueueDashboard();
        this.updateCharts();
        this.showNotification('Queue status refreshed', 'info');
    }

    togglePause() {
        this.isPaused = !this.isPaused;
        
        const button = document.getElementById('pause-monitoring');
        if (button) {
            button.textContent = this.isPaused ? '▶️ Resume' : '⏸️ Pause';
            button.className = this.isPaused ? 'btn btn-success' : 'btn btn-warning';
        }
        
        if (this.isPaused) {
            this.stopAutoRefresh();
        } else {
            this.startAutoRefresh();
        }
        
        this.showNotification(`Monitoring ${this.isPaused ? 'paused' : 'resumed'}`, 'info');
    }

    setRefreshRate(rate) {
        this.refreshRate = parseInt(rate);
        if (!this.isPaused) {
            this.startAutoRefresh();
        }
    }

    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (!this.isPaused) {
            this.refreshInterval = setInterval(async () => {
                await this.loadQueueStatus();
                this.renderQueueDashboard();
                this.updateCharts();
            }, this.refreshRate);
        }
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    exportQueueStats() {
        const data = {
            timestamp: new Date().toISOString(),
            current_status: this.queueData,
            historical_data: this.historicalData
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `queue-stats-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
        this.showNotification('Queue statistics exported', 'success');
    }

    initializeEventListeners() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 'r') {
                    e.preventDefault();
                    this.refreshNow();
                } else if (e.key === ' ') {
                    e.preventDefault();
                    this.togglePause();
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
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }
}

// Initialize global instance
window.queueMonitor = new QueueMonitor();
