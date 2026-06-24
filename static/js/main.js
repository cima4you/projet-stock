// Main JavaScript file for Stock Management System
// Handles common functionality across all pages

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize popovers
    initializePopovers();
    
    // Handle form validation
    initializeFormValidation();
    
    // Initialize data tables if present
    initializeDataTables();
    
    // Handle auto-hide alerts
    initializeAutoHideAlerts();
    
    // Initialize confirmation dialogs
    initializeConfirmationDialogs();
    
    // Handle responsive navigation
    initializeResponsiveNavigation();
    
    // Initialize search functionality
    initializeSearchFunctionality();
    
    // Handle notification management
    initializeNotificationManagement();
    
    // Initialize theme handling
    initializeThemeHandling();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize Bootstrap popovers
 */
function initializePopovers() {
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    // Bootstrap form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Custom validations
    initializeCustomValidations();
}

/**
 * Initialize custom form validations
 */
function initializeCustomValidations() {
    // Password strength validation
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(function(input) {
        if (input.hasAttribute('minlength')) {
            input.addEventListener('input', function() {
                validatePasswordStrength(this);
            });
        }
    });
    
    // Email validation
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            validateEmail(this);
        });
    });
    
    // Numeric validations
    const numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            validateNumericInput(this);
        });
    });
}

/**
 * Validate password strength
 */
function validatePasswordStrength(input) {
    const password = input.value;
    const minLength = parseInt(input.getAttribute('minlength')) || 6;
    
    if (password.length < minLength) {
        input.setCustomValidity('Le mot de passe doit contenir au moins ' + minLength + ' caractères');
    } else {
        input.setCustomValidity('');
    }
}

/**
 * Validate email format
 */
function validateEmail(input) {
    const email = input.value;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (email && !emailRegex.test(email)) {
        input.setCustomValidity('Veuillez entrer une adresse email valide');
    } else {
        input.setCustomValidity('');
    }
}

/**
 * Validate numeric input
 */
function validateNumericInput(input) {
    const value = parseFloat(input.value);
    const min = parseFloat(input.getAttribute('min'));
    const max = parseFloat(input.getAttribute('max'));
    
    if (isNaN(value)) {
        input.setCustomValidity('Veuillez entrer un nombre valide');
        return;
    }
    
    if (!isNaN(min) && value < min) {
        input.setCustomValidity('La valeur doit être supérieure ou égale à ' + min);
        return;
    }
    
    if (!isNaN(max) && value > max) {
        input.setCustomValidity('La valeur doit être inférieure ou égale à ' + max);
        return;
    }
    
    input.setCustomValidity('');
}

/**
 * Initialize data tables functionality
 */
function initializeDataTables() {
    // Add sorting functionality to tables
    const tables = document.querySelectorAll('.table-sortable');
    tables.forEach(function(table) {
        makeTableSortable(table);
    });
    
    // Add row highlighting on hover
    const hoverTables = document.querySelectorAll('.table-hover');
    hoverTables.forEach(function(table) {
        addTableHoverEffects(table);
    });
}

/**
 * Make table sortable
 */
function makeTableSortable(table) {
    const headers = table.querySelectorAll('th[data-sortable]');
    headers.forEach(function(header, index) {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            sortTableByColumn(table, index, header);
        });
    });
}

/**
 * Sort table by column
 */
function sortTableByColumn(table, columnIndex, header) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const isAscending = !header.classList.contains('sort-asc');
    
    // Clear previous sort indicators
    table.querySelectorAll('th').forEach(h => {
        h.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Add current sort indicator
    header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
    
    rows.sort((a, b) => {
        const aValue = a.cells[columnIndex].textContent.trim();
        const bValue = b.cells[columnIndex].textContent.trim();
        
        // Try to parse as numbers first
        const aNum = parseFloat(aValue);
        const bNum = parseFloat(bValue);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? aNum - bNum : bNum - aNum;
        }
        
        // Sort as strings
        return isAscending ? 
            aValue.localeCompare(bValue) : 
            bValue.localeCompare(aValue);
    });
    
    // Reorder rows in DOM
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Add hover effects to table
 */
function addTableHoverEffects(table) {
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(function(row) {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = 'rgba(0, 123, 255, 0.1)';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
}

/**
 * Initialize auto-hide alerts
 */
function initializeAutoHideAlerts() {
    const autoHideAlerts = document.querySelectorAll('.alert[data-auto-hide]');
    autoHideAlerts.forEach(function(alert) {
        const delay = parseInt(alert.getAttribute('data-auto-hide')) || 5000;
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, delay);
    });
}

/**
 * Initialize confirmation dialogs
 */
function initializeConfirmationDialogs() {
    const confirmLinks = document.querySelectorAll('a[data-confirm], button[data-confirm]');
    confirmLinks.forEach(function(element) {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Êtes-vous sûr?';
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Initialize responsive navigation
 */
function initializeResponsiveNavigation() {
    // Handle mobile menu toggle
    const navbarToggler = document.querySelector('.navbar-toggler');
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function() {
            const target = document.querySelector(this.getAttribute('data-bs-target'));
            if (target) {
                target.classList.toggle('show');
            }
        });
    }
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(e) {
        const navbarCollapse = document.querySelector('.navbar-collapse');
        const navbarToggler = document.querySelector('.navbar-toggler');
        
        if (navbarCollapse && navbarCollapse.classList.contains('show')) {
            if (!navbarCollapse.contains(e.target) && !navbarToggler.contains(e.target)) {
                navbarCollapse.classList.remove('show');
            }
        }
    });
}

/**
 * Initialize search functionality
 */
function initializeSearchFunctionality() {
    const searchInputs = document.querySelectorAll('.search-input');
    searchInputs.forEach(function(input) {
        let debounceTimer;
        input.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                performSearch(this);
            }, 300);
        });
    });
}

/**
 * Perform search in table
 */
function performSearch(input) {
    const searchTerm = input.value.toLowerCase();
    const targetTable = document.querySelector(input.getAttribute('data-target'));
    
    if (!targetTable) return;
    
    const rows = targetTable.querySelectorAll('tbody tr');
    let visibleCount = 0;
    
    rows.forEach(function(row) {
        const text = row.textContent.toLowerCase();
        const isVisible = text.includes(searchTerm);
        row.style.display = isVisible ? '' : 'none';
        if (isVisible) visibleCount++;
    });
    
    // Update results counter if exists
    const counter = document.querySelector('.search-results-count');
    if (counter) {
        counter.textContent = `${visibleCount} résultat(s) trouvé(s)`;
    }
}

/**
 * Initialize notification management
 */
function initializeNotificationManagement() {
    // Handle notification preference changes
    const notificationCheckboxes = document.querySelectorAll('input[type="checkbox"][name^="notify_"]');
    notificationCheckboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            updateNotificationPreview();
        });
    });
    
    // Handle email test functionality
    const testEmailButtons = document.querySelectorAll('.test-email-btn');
    testEmailButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            testEmailConnection(this);
        });
    });
}

/**
 * Update notification preview
 */
function updateNotificationPreview() {
    const preview = document.querySelector('.notification-preview');
    if (!preview) return;
    
    const selectedTypes = [];
    const checkboxes = document.querySelectorAll('input[type="checkbox"][name^="notify_"]:checked');
    
    checkboxes.forEach(function(checkbox) {
        const label = document.querySelector(`label[for="${checkbox.id}"]`);
        if (label) {
            selectedTypes.push(label.textContent.trim());
        }
    });
    
    preview.innerHTML = selectedTypes.length > 0 
        ? `Notifications activées pour: ${selectedTypes.join(', ')}`
        : 'Aucune notification activée';
}

/**
 * Test email connection
 */
function testEmailConnection(button) {
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = 'Test en cours...';
    
    // The actual test will be handled by the server
    // This just provides UI feedback
    setTimeout(function() {
        button.disabled = false;
        button.textContent = originalText;
    }, 3000);
}

/**
 * Initialize theme handling
 */
function initializeThemeHandling() {
    // Handle RTL/LTR direction changes
    const langSwitchers = document.querySelectorAll('[data-lang]');
    langSwitchers.forEach(function(switcher) {
        switcher.addEventListener('click', function(e) {
            const lang = this.getAttribute('data-lang');
            if (lang === 'ar') {
                document.documentElement.setAttribute('dir', 'rtl');
                document.body.classList.add('rtl');
            } else {
                document.documentElement.setAttribute('dir', 'ltr');
                document.body.classList.remove('rtl');
            }
        });
    });
}

/**
 * Utility functions
 */

// Format number with thousand separators
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

// Format date to locale string
function formatDate(date, locale = 'fr-FR') {
    return new Date(date).toLocaleDateString(locale);
}

// Show loading spinner
function showLoading(element) {
    const spinner = document.createElement('div');
    spinner.className = 'spinner-border spinner-border-sm me-2';
    spinner.setAttribute('role', 'status');
    element.prepend(spinner);
    element.disabled = true;
}

// Hide loading spinner
function hideLoading(element) {
    const spinner = element.querySelector('.spinner-border');
    if (spinner) {
        spinner.remove();
    }
    element.disabled = false;
}

// Show toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

// Create toast container if it doesn't exist
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

// Smooth scroll to element
function scrollToElement(element) {
    element.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
}

// Copy text to clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Texte copié dans le presse-papiers', 'success');
    } catch (err) {
        console.error('Erreur lors de la copie:', err);
        showToast('Erreur lors de la copie', 'danger');
    }
}

// Export functions for global access
window.StockManagement = {
    formatNumber,
    formatDate,
    showLoading,
    hideLoading,
    showToast,
    scrollToElement,
    copyToClipboard
};

// Live notification polling
(function startNotificationPolling() {
    const badge = document.getElementById('notificationBadge');
    const bell = document.getElementById('notificationBell');
    if (!badge || !bell) return;

    async function poll() {
        try {
            const resp = await fetch('/api/unread_count');
            const data = await resp.json();
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        } catch (_) {}
    }
    poll();
    setInterval(poll, 15000);

    bell.addEventListener('click', async function () {
        try {
            const resp = await fetch('/api/unread_notifications');
            const notifs = await resp.json();
            if (notifs.length === 0) {
                showToast('Aucune nouvelle notification', 'info');
                return;
            }
            notifs.forEach(function (n) {
                showToast(n.subject, 'info');
                fetch('/api/mark_notification_read/' + n.id, { method: 'GET' });
            });
            badge.style.display = 'none';
        } catch (_) {}
    });
})();

// Live search-as-you-type
(function initLiveSearch() {
    const input = document.getElementById('liveSearch');
    const results = document.getElementById('liveSearchResults');
    if (!input || !results) return;

    let debounceTimer;
    input.addEventListener('input', function () {
        clearTimeout(debounceTimer);
        const q = this.value.trim();
        if (q.length < 2) { results.innerHTML = ''; results.style.display = 'none'; return; }
        debounceTimer = setTimeout(async () => {
            try {
                const resp = await fetch('/api/search_products?q=' + encodeURIComponent(q));
                const data = await resp.json();
                if (data.length === 0) {
                    results.innerHTML = '<div class="dropdown-item text-muted">Aucun résultat</div>';
                } else {
                    results.innerHTML = data.map(p =>
                        `<a class="dropdown-item" href="/product_history/${p.id}">
                            <strong>${p.code}</strong> - ${p.name}
                            <span class="badge bg-${p.quantity > 0 && p.min_quantity > 0 && p.quantity < p.min_quantity ? 'danger' : 'secondary'} float-end">${p.quantity}</span>
                         </a>`
                    ).join('');
                }
                results.style.display = 'block';
            } catch (_) { results.style.display = 'none'; }
        }, 250);
    });
    document.addEventListener('click', function (e) {
        if (!input.contains(e.target) && !results.contains(e.target)) {
            results.style.display = 'none';
        }
    });
})();

// Handle page-specific initialization
if (typeof window.pageInit === 'function') {
    window.pageInit();
}

