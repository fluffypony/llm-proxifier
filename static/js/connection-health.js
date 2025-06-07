/**
 * Connection Health Monitor
 * Monitors connection health and provides visual feedback
 */
class ConnectionHealthMonitor {
    constructor() {
        this.isHealthy = true;
        this.lastSuccessfulPing = Date.now();
        this.healthCheckInterval = null;
        this.healthCheckRate = 30000; // 30 seconds
        this.failureCount = 0;
        this.maxFailures = 3;
        
        this.startHealthCheck();
    }
    
    startHealthCheck() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
        }
        
        this.healthCheckInterval = setInterval(async () => {
            await this.performHealthCheck();
        }, this.healthCheckRate);
        
        // Perform initial health check
        this.performHealthCheck();
    }
    
    async performHealthCheck() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            const response = await fetch('/dashboard/api/health', {
                method: 'GET',
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                this.lastSuccessfulPing = Date.now();
                this.failureCount = 0;
                
                if (!this.isHealthy) {
                    this.isHealthy = true;
                    this.showConnectionRestored();
                }
            } else {
                this.handleConnectionIssue(`HTTP ${response.status}`);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                this.handleConnectionIssue('Request timeout');
            } else {
                this.handleConnectionIssue(error.message);
            }
        }
    }
    
    handleConnectionIssue(reason = 'Unknown error') {
        this.failureCount++;
        
        if (this.failureCount >= this.maxFailures && this.isHealthy) {
            this.isHealthy = false;
            this.showConnectionIssue(reason);
        }
    }
    
    showConnectionIssue(reason = '') {
        // Remove any existing banner
        const existingBanner = document.getElementById('connection-health-banner');
        if (existingBanner) {
            existingBanner.remove();
        }
        
        const banner = document.createElement('div');
        banner.id = 'connection-health-banner';
        banner.className = 'health-banner warning';
        banner.innerHTML = `
            <div class="health-content">
                <span class="health-icon">⚠️</span>
                <span class="health-message">Connection issues detected${reason ? ': ' + reason : ''}. Some features may not work properly.</span>
                <button class="btn btn-xs btn-secondary" onclick="connectionHealth.forceCheck()">Test Connection</button>
                <button class="btn btn-xs btn-outline" onclick="connectionHealth.dismissBanner()">Dismiss</button>
            </div>
        `;
        
        document.body.insertBefore(banner, document.body.firstChild);
        
        // Auto-dismiss after 10 seconds if connection is restored
        setTimeout(() => {
            if (this.isHealthy) {
                this.dismissBanner();
            }
        }, 10000);
    }
    
    showConnectionRestored() {
        const banner = document.getElementById('connection-health-banner');
        if (banner) {
            banner.className = 'health-banner success';
            banner.innerHTML = `
                <div class="health-content">
                    <span class="health-icon">✅</span>
                    <span class="health-message">Connection restored</span>
                </div>
            `;
            
            // Auto-remove success banner after 3 seconds
            setTimeout(() => banner.remove(), 3000);
        }
    }
    
    dismissBanner() {
        const banner = document.getElementById('connection-health-banner');
        if (banner) {
            banner.remove();
        }
    }
    
    async forceCheck() {
        await this.performHealthCheck();
        
        if (this.isHealthy) {
            this.showNotification('Connection test successful', 'success');
        } else {
            this.showNotification('Connection test failed', 'error');
        }
    }
    
    showNotification(message, type = 'info') {
        // Use existing notification system if available
        if (window.queueMonitor && typeof window.queueMonitor.showNotification === 'function') {
            window.queueMonitor.showNotification(message, type);
        } else if (window.configEditor && typeof window.configEditor.showNotification === 'function') {
            window.configEditor.showNotification(message, type);
        } else {
            // Fallback notification
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
    
    getHealthStatus() {
        return {
            isHealthy: this.isHealthy,
            lastSuccessfulPing: this.lastSuccessfulPing,
            timeSinceLastPing: Date.now() - this.lastSuccessfulPing,
            failureCount: this.failureCount,
            maxFailures: this.maxFailures
        };
    }
    
    updateHealthCheckRate(rate) {
        this.healthCheckRate = Math.max(10000, rate); // Minimum 10 seconds
        this.startHealthCheck();
    }
    
    destroy() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }
        
        this.dismissBanner();
    }
}

// Initialize global connection health monitor
window.connectionHealth = new ConnectionHealthMonitor();
