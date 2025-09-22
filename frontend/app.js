/**
 * AI File Organizer V3 - Search Interface
 * ADHD-friendly search with real-time API integration
 */

class SearchInterface {
    constructor() {
        // Search elements
        this.searchInput = document.getElementById('searchInput');
        this.searchLoading = document.getElementById('searchLoading');
        this.resultsSection = document.getElementById('resultsSection');
        this.resultsTitle = document.getElementById('resultsTitle');
        this.resultsCount = document.getElementById('resultsCount');
        this.resultsContainer = document.getElementById('resultsContainer');
        this.emptyState = document.getElementById('emptyState');
        this.modeButtons = document.querySelectorAll('.mode-btn');
        
        // Navigation elements
        this.searchNavBtn = document.getElementById('searchNavBtn');
        this.triageNavBtn = document.getElementById('triageNavBtn');
        
        // Triage elements
        this.triageSection = document.getElementById('triageSection');
        this.triageCount = document.getElementById('triageCount');
        this.triageContainer = document.getElementById('triageContainer');
        this.triageEmpty = document.getElementById('triageEmpty');
        
        // Search state
        this.currentMode = 'auto';
        this.debounceTimer = null;
        this.lastQuery = '';
        this.isSearching = false;
        
        // Application state
        this.currentView = 'search'; // 'search' or 'triage'
        
        this.init();
    }
    
    init() {
        // Search input event listeners
        this.searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value);
        });
        
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.performSearch(e.target.value, true);
            }
        });
        
        // Mode button event listeners
        this.modeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.setSearchMode(e.target.dataset.mode);
            });
        });
        
        // Example search click handlers
        const exampleSearches = document.querySelectorAll('.example-searches li');
        exampleSearches.forEach(item => {
            item.addEventListener('click', () => {
                const query = item.textContent.replace(/"/g, '');
                this.searchInput.value = query;
                this.performSearch(query, true);
            });
        });
        
        // Navigation event listeners
        this.searchNavBtn.addEventListener('click', () => {
            this.showSearchView();
        });
        
        this.triageNavBtn.addEventListener('click', () => {
            this.showTriageView();
        });
        
        // Focus search input on page load
        this.searchInput.focus();
    }
    
    handleSearchInput(query) {
        // Clear previous debounce timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // If query is empty, show empty state
        if (!query.trim()) {
            this.showEmptyState();
            return;
        }
        
        // Debounce search to avoid excessive API calls
        this.debounceTimer = setTimeout(() => {
            if (query.trim() !== this.lastQuery) {
                this.performSearch(query.trim());
            }
        }, 300);
    }
    
    setSearchMode(mode) {
        this.currentMode = mode;
        
        // Update button states
        this.modeButtons.forEach(button => {
            button.classList.remove('active');
            if (button.dataset.mode === mode) {
                button.classList.add('active');
            }
        });
        
        // Re-search with new mode if there's a current query
        if (this.searchInput.value.trim()) {
            this.performSearch(this.searchInput.value.trim(), true);
        }
    }
    
    async performSearch(query, immediate = false) {
        if (!query.trim() || this.isSearching) {
            return;
        }
        
        this.isSearching = true;
        this.lastQuery = query;
        
        try {
            this.showLoadingState();
            
            // Construct API URL
            const params = new URLSearchParams({
                q: query,
                mode: this.currentMode
            });
            
            const response = await fetch(`/api/search?${params}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Search failed: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            this.displayResults(data);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showErrorState(error.message);
        } finally {
            this.hideLoadingState();
            this.isSearching = false;
        }
    }
    
    showLoadingState() {
        this.searchLoading.style.display = 'block';
        this.searchInput.style.paddingRight = '60px';
    }
    
    hideLoadingState() {
        this.searchLoading.style.display = 'none';
        this.searchInput.style.paddingRight = '';
    }
    
    showEmptyState() {
        this.resultsSection.style.display = 'none';
        this.emptyState.style.display = 'block';
    }
    
    displayResults(data) {
        this.emptyState.style.display = 'none';
        this.resultsSection.style.display = 'block';
        
        // Update results header
        this.resultsTitle.textContent = `Search Results for "${data.query}"`;
        this.resultsCount.textContent = `${data.count} result${data.count !== 1 ? 's' : ''} found`;
        
        // Clear previous results
        this.resultsContainer.innerHTML = '';
        
        // Display each result
        data.results.forEach(result => {
            const resultCard = this.createResultCard(result);
            this.resultsContainer.appendChild(resultCard);
        });
        
        // Scroll to results
        this.resultsSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }
    
    createResultCard(result) {
        const card = document.createElement('div');
        card.className = 'result-card';
        
        // Create relevance score badge
        const scorePercentage = Math.round(result.relevance_score * 100);
        const scoreClass = scorePercentage >= 80 ? 'high' : scorePercentage >= 60 ? 'medium' : 'low';
        
        // Format file size
        const fileSize = this.formatFileSize(result.file_size);
        
        // Format date
        const lastModified = this.formatDate(result.last_modified);
        
        // Create status indicator
        const statusIndicator = this.createStatusIndicator(result.availability, result.sync_status);
        
        card.innerHTML = `
            <div class="result-header">
                <div class="result-filename">
                    ${this.createFileLink(result)}
                </div>
                <div class="result-score">${scorePercentage}%</div>
            </div>
            
            <div class="result-metadata">
                <span>📁 ${this.escapeHtml(result.file_category || 'Uncategorized')}</span>
                <span>📊 ${fileSize}</span>
                <span>🕒 ${lastModified}</span>
                ${statusIndicator}
            </div>
            
            ${result.matching_content ? `
                <div class="result-content">
                    ${this.escapeHtml(result.matching_content)}
                </div>
            ` : ''}
            
            <div class="result-path">
                ${this.escapeHtml(result.local_path || result.drive_path || 'Path not available')}
            </div>
            
            ${result.reasoning && result.reasoning.length > 0 ? `
                <div class="result-reasoning">
                    <h4>Why this matches:</h4>
                    <ul class="reasoning-list">
                        ${result.reasoning.map(reason => `
                            <li>${this.escapeHtml(reason)}</li>
                        `).join('')}
                    </ul>
                </div>
            ` : ''}
        `;
        
        // Add click handler for local file links
        const localFileLink = card.querySelector('.file-link.local-file');
        if (localFileLink) {
            localFileLink.addEventListener('click', (e) => {
                e.preventDefault();
                const filePath = localFileLink.getAttribute('data-local-path');
                this.openFile(filePath);
            });
        }
        
        return card;
    }
    
    createStatusIndicator(availability, syncStatus) {
        let statusClass = 'status-available';
        let statusText = 'Available';
        let statusIcon = '✅';
        
        if (availability === 'syncing' || syncStatus === 'syncing') {
            statusClass = 'status-syncing';
            statusText = 'Syncing';
            statusIcon = '🔄';
        } else if (availability === 'offline' || syncStatus === 'offline') {
            statusClass = 'status-offline';
            statusText = 'Offline';
            statusIcon = '❌';
        }
        
        return `<span class="status-indicator ${statusClass}">${statusIcon} ${statusText}</span>`;
    }
    
    formatFileSize(bytes) {
        if (!bytes) return 'Unknown size';
        
        const sizes = ['B', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 B';
        
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        const size = bytes / Math.pow(1024, i);
        
        return `${size.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
    }
    
    formatDate(dateString) {
        if (!dateString) return 'Unknown date';
        
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            if (diffDays === 1) {
                return 'Yesterday';
            } else if (diffDays < 7) {
                return `${diffDays} days ago`;
            } else if (diffDays < 30) {
                const weeks = Math.floor(diffDays / 7);
                return `${weeks} week${weeks > 1 ? 's' : ''} ago`;
            } else {
                return date.toLocaleDateString();
            }
        } catch (error) {
            return 'Invalid date';
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    createFileLink(result) {
        const filename = this.escapeHtml(result.filename);
        
        // Create clickable link based on file location
        if (result.local_path) {
            // Local file - use click handler to call backend API
            return `<a href="#" class="file-link local-file" data-local-path="${this.escapeHtml(result.local_path)}" title="Open local file: ${this.escapeHtml(result.local_path)}">${filename}</a>`;
        } else if (result.drive_path && result.file_id) {
            // Google Drive file - use Google Drive URL (direct links work in browsers)
            const driveUrl = `https://drive.google.com/file/d/${result.file_id}`;
            return `<a href="${driveUrl}" target="_blank" class="file-link drive-file" title="Open in Google Drive: ${this.escapeHtml(result.drive_path)}">${filename}</a>`;
        } else if (result.drive_path) {
            // Google Drive file without file_id - fallback to search
            const searchQuery = encodeURIComponent(result.filename);
            const driveSearchUrl = `https://drive.google.com/drive/search?q=${searchQuery}`;
            return `<a href="${driveSearchUrl}" target="_blank" class="file-link drive-file" title="Search in Google Drive: ${this.escapeHtml(result.filename)}">${filename}</a>`;
        } else {
            // No path available - return plain text
            return `<span class="file-link no-link" title="File location not available">${filename}</span>`;
        }
    }
    
    async openFile(filePath) {
        console.log('Opening file:', filePath);
        
        try {
            // Show a subtle loading indicator (could be enhanced with UI feedback)
            const response = await fetch('/api/open-file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ path: filePath })
            });
            
            if (!response.ok) {
                // Try to get error details from response
                let errorMessage = `HTTP ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorMessage;
                } catch {
                    errorMessage = `${errorMessage} ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            
            const result = await response.json();
            
            if (result.success) {
                console.log('✅ File opened successfully:', result.message);
                // Could show a subtle success notification here
                this.showFileOpenFeedback('success', `Opened: ${result.message}`);
            } else {
                throw new Error(result.message || 'Unknown error occurred');
            }
            
        } catch (error) {
            console.error('❌ Error opening file:', error);
            this.showFileOpenFeedback('error', `Failed to open file: ${error.message}`);
        }
    }
    
    showFileOpenFeedback(type, message) {
        // Create a temporary toast notification for file open feedback
        const toast = document.createElement('div');
        toast.className = `file-open-toast ${type}`;
        toast.textContent = message;
        
        // Style the toast
        Object.assign(toast.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: '500',
            zIndex: '10000',
            maxWidth: '400px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            transform: 'translateX(100%)',
            transition: 'transform 0.3s ease-out',
            backgroundColor: type === 'success' ? '#10b981' : '#ef4444',
            color: 'white'
        });
        
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
        }, 10);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
    
    // ===== VIEW NAVIGATION METHODS =====
    
    showSearchView() {
        this.currentView = 'search';
        
        // Update navigation buttons
        this.searchNavBtn.classList.add('active');
        this.triageNavBtn.classList.remove('active');
        
        // Show/hide sections
        document.querySelector('.search-section').style.display = 'block';
        this.triageSection.style.display = 'none';
        this.resultsSection.style.display = this.resultsContainer.children.length > 0 ? 'block' : 'none';
        this.emptyState.style.display = this.resultsContainer.children.length > 0 ? 'none' : 'block';
        
        // Focus search input
        this.searchInput.focus();
    }
    
    showTriageView() {
        this.currentView = 'triage';
        
        // Update navigation buttons
        this.searchNavBtn.classList.remove('active');
        this.triageNavBtn.classList.add('active');
        
        // Show/hide sections
        document.querySelector('.search-section').style.display = 'none';
        this.resultsSection.style.display = 'none';
        this.emptyState.style.display = 'none';
        this.triageSection.style.display = 'block';
        
        // Load triage data (for now, just show the static card)
        this.loadTriageFiles();
    }
    
    async loadTriageFiles() {
        try {
            this.triageCount.textContent = 'Loading...';
            
            // Fetch real files from the API
            const response = await fetch('/api/triage/files_to_review', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to fetch files: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Clear existing triage cards
            this.triageContainer.innerHTML = '';
            
            if (data.files && data.files.length > 0) {
                // Update count and show triage container
                this.triageCount.textContent = `${data.count} file${data.count !== 1 ? 's' : ''} need${data.count === 1 ? 's' : ''} review`;
                
                // Create a card for each file needing review
                data.files.forEach(file => {
                    const triageCard = this.createTriageCard(file);
                    this.triageContainer.appendChild(triageCard);
                });
                
                // Show the triage container
                this.triageContainer.style.display = 'block';
                this.triageEmpty.style.display = 'none';
                
            } else {
                // No files to review - show empty state
                this.showTriageEmptyState();
            }
            
        } catch (error) {
            console.error('Error loading triage files:', error);
            this.triageCount.textContent = 'Error loading files';
            this.showTriageErrorState(error.message);
        }
    }
    
    createTriageCard(file) {
        const card = document.createElement('div');
        card.className = 'triage-card';
        card.dataset.filePath = file.file_path;
        
        // Extract filename from path
        const filename = file.file_path.split('/').pop() || 'Unknown file';
        
        // Calculate confidence percentage
        const confidencePercentage = Math.round(file.confidence * 100);
        
        // Create confidence level indicator
        const confidenceClass = confidencePercentage >= 70 ? 'medium' : 'low';
        
        card.innerHTML = `
            <div class="triage-card-header">
                <h3 class="triage-filename">${this.escapeHtml(filename)}</h3>
                <div class="triage-confidence">${confidencePercentage}%</div>
            </div>
            
            <div class="triage-suggestion">
                <div class="suggested-category">
                    <span class="category-label">Suggested Category:</span>
                    <span class="category-value">${this.escapeHtml(file.suggested_category)}</span>
                </div>
                <div class="confidence-indicator">
                    <span class="confidence-label">Confidence:</span>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${confidencePercentage}%;"></div>
                    </div>
                    <span class="confidence-text">${confidencePercentage}% - Needs Review</span>
                </div>
            </div>
            
            <div class="triage-file-path">
                <small>📁 ${this.escapeHtml(file.file_path)}</small>
            </div>
            
            <div class="triage-actions">
                <button class="btn btn-primary triage-confirm" data-action="confirm">
                    ✅ Confirm Suggestion
                </button>
                <button class="btn btn-secondary triage-reclassify" data-action="reclassify">
                    🔄 Re-classify
                </button>
            </div>
        `;
        
        // Add event listeners to the buttons
        const confirmBtn = card.querySelector('.triage-confirm');
        const reclassifyBtn = card.querySelector('.triage-reclassify');
        
        confirmBtn.addEventListener('click', (e) => {
            this.handleTriageAction(e.target, 'confirm');
        });
        
        reclassifyBtn.addEventListener('click', (e) => {
            this.handleTriageAction(e.target, 'reclassify');
        });
        
        return card;
    }
    
    async handleTriageAction(button, action) {
        const card = button.closest('.triage-card');
        const filename = card.querySelector('.triage-filename').textContent;
        const filePath = card.dataset.filePath;
        const suggestedCategory = card.querySelector('.category-value').textContent;
        
        try {
            // Disable button during processing
            button.disabled = true;
            button.textContent = action === 'confirm' ? '⏳ Confirming...' : '⏳ Processing...';
            
            if (action === 'confirm') {
                // Send confirmation to API
                const response = await fetch('/api/triage/classify', {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        file_path: filePath,
                        confirmed_category: suggestedCategory
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Classification failed: ${response.status} ${response.statusText}`);
                }
                
                const result = await response.json();
                
                // Show success feedback
                this.showTriageActionFeedback('success', `✅ ${filename} has been filed successfully!`);
                
                // Remove the card with animation
                card.style.opacity = '0.5';
                card.style.transform = 'translateX(100%)';
                
                setTimeout(() => {
                    card.remove();
                    
                    // Check if there are any cards left
                    const remainingCards = this.triageContainer.querySelectorAll('.triage-card');
                    if (remainingCards.length === 0) {
                        this.showTriageEmptyState();
                    } else {
                        this.triageCount.textContent = `${remainingCards.length} file${remainingCards.length !== 1 ? 's' : ''} need${remainingCards.length === 1 ? 's' : ''} review`;
                    }
                }, 300);
                
            } else {
                // For re-classify, show a simple message for now
                // In future versions, this could open a category selection modal
                this.showTriageActionFeedback('info', `🔄 Re-classification for ${filename} would open category selection here`);
                
                // Reset button
                button.disabled = false;
                button.innerHTML = '🔄 Re-classify';
            }
            
        } catch (error) {
            console.error('Triage action error:', error);
            this.showTriageActionFeedback('error', `❌ Error processing ${filename}: ${error.message}`);
            
            // Reset button
            button.disabled = false;
            button.innerHTML = action === 'confirm' ? '✅ Confirm Suggestion' : '🔄 Re-classify';
        }
    }
    
    showTriageEmptyState() {
        this.triageContainer.style.display = 'none';
        this.triageEmpty.style.display = 'block';
        this.triageCount.textContent = 'All files reviewed!';
        
        // Setup refresh button (remove any existing listeners to avoid duplicates)
        const refreshBtn = document.getElementById('refreshTriageBtn');
        if (refreshBtn) {
            // Clone node to remove existing event listeners
            const newRefreshBtn = refreshBtn.cloneNode(true);
            refreshBtn.parentNode.replaceChild(newRefreshBtn, refreshBtn);
            
            // Add fresh event listener
            newRefreshBtn.addEventListener('click', () => {
                this.loadTriageFiles();
            });
        }
    }
    
    showTriageErrorState(errorMessage) {
        this.triageContainer.innerHTML = `
            <div class="triage-card" style="border-color: var(--error); background: rgba(239, 68, 68, 0.1);">
                <div class="triage-card-header">
                    <h3 class="triage-filename" style="color: var(--error);">
                        ❌ Error Loading Files
                    </h3>
                </div>
                <div class="triage-content-preview" style="color: var(--error);">
                    <p>${this.escapeHtml(errorMessage)}</p>
                </div>
                <div class="triage-actions">
                    <button class="btn btn-secondary" onclick="window.searchInterface.loadTriageFiles()">
                        🔄 Try Again
                    </button>
                </div>
            </div>
        `;
        
        this.triageContainer.style.display = 'block';
        this.triageEmpty.style.display = 'none';
    }
    
    showTriageActionFeedback(type, message) {
        // Create a temporary toast notification for triage actions
        const toast = document.createElement('div');
        toast.className = `triage-action-toast ${type}`;
        toast.textContent = message;
        
        // Style the toast
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            info: '#3b82f6'
        };
        
        Object.assign(toast.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '14px',
            fontWeight: '500',
            zIndex: '10000',
            maxWidth: '400px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            transform: 'translateX(100%)',
            transition: 'transform 0.3s ease-out',
            backgroundColor: colors[type] || colors.info,
            color: 'white'
        });
        
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
        }, 10);
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }
    
    showErrorState(message) {
        this.emptyState.style.display = 'none';
        this.resultsSection.style.display = 'block';
        
        this.resultsTitle.textContent = 'Search Error';
        this.resultsCount.textContent = '';
        
        this.resultsContainer.innerHTML = `
            <div class="result-card" style="border-color: var(--error); background: rgba(239, 68, 68, 0.1);">
                <div class="result-header">
                    <div class="result-filename" style="color: var(--error);">
                        ❌ Search Error
                    </div>
                </div>
                <div class="result-content" style="color: var(--error);">
                    ${this.escapeHtml(message)}
                </div>
                <div style="margin-top: 1rem; font-size: 0.875rem; color: var(--text-muted);">
                    Please try again or check your internet connection. If the problem persists, 
                    make sure the AI File Organizer backend is running.
                </div>
            </div>
        `;
    }
}

// Keyboard shortcuts for ADHD-friendly navigation
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        window.searchInterface.showSearchView();
    }
    
    // Ctrl/Cmd + T to show triage view
    if ((e.ctrlKey || e.metaKey) && e.key === 't') {
        e.preventDefault();
        window.searchInterface.showTriageView();
    }
    
    // Escape to clear search or go back to search view
    if (e.key === 'Escape') {
        if (window.searchInterface.currentView === 'triage') {
            window.searchInterface.showSearchView();
        } else {
            const searchInput = document.getElementById('searchInput');
            if (document.activeElement === searchInput) {
                searchInput.value = '';
                searchInput.dispatchEvent(new Event('input'));
            }
        }
    }
});

// Initialize the search interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.searchInterface = new SearchInterface();
    
    // Add helpful console message
    console.log('🔍 AI File Organizer V3 Search Interface Ready');
    console.log('📋 Triage Center Ready');
    console.log('💡 Keyboard shortcuts:');
    console.log('   - Ctrl/Cmd + K: Show search view');
    console.log('   - Ctrl/Cmd + T: Show triage view');
    console.log('   - Escape: Clear search or return to search');
    console.log('   - Enter: Immediate search');
});