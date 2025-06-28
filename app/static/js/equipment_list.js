/**
 * Equipment List Page Functionality
 * Handles sorting, filtering, and other interactive elements on the equipment list page
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Equipment list page initialized');
    
    // Initialize bulk selection
    initBulkSelection();
    
    // Initialize sorting
    initSorting();
    
    // Initialize search form submission
    initSearchForm();
    
    // Initialize status filter
    initStatusFilter();
    
    // Initialize per page selector
    initPerPageSelector();
    
    // Initialize bulk delete button
    initBulkDeleteButton();
    
    // Initialize date pickers
    initDatePickers();
});

/**
 * Initialize bulk selection functionality
 */
function initBulkSelection() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const itemCheckboxes = document.querySelectorAll('.item-checkbox');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    const selectedCount = document.getElementById('selectedCount');
    
    if (!selectAllCheckbox || !bulkDeleteBtn || !selectedCount) return;
    
    // Toggle all checkboxes when 'select all' is clicked
    selectAllCheckbox.addEventListener('change', function() {
        const isChecked = this.checked;
        itemCheckboxes.forEach(checkbox => {
            checkbox.checked = isChecked;
        });
        updateBulkActions();
    });
    
    // Update 'select all' when individual checkboxes change
    itemCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateBulkActions();
            updateSelectAllCheckbox();
        });
    });
    
    function updateSelectAllCheckbox() {
        const allChecked = Array.from(itemCheckboxes).every(checkbox => checkbox.checked);
        const someChecked = Array.from(itemCheckboxes).some(checkbox => checkbox.checked);
        
        if (allChecked) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else if (someChecked) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        }
    }
    
    function updateBulkActions() {
        const selectedItems = document.querySelectorAll('.item-checkbox:checked');
        
        if (selectedItems.length > 0) {
            bulkDeleteBtn.style.display = 'inline-block';
            selectedCount.textContent = selectedItems.length;
        } else {
            bulkDeleteBtn.style.display = 'none';
        }
    }
}

/**
 * Initialize sorting functionality
 */
function initSorting() {
    const sortableHeaders = document.querySelectorAll('.sortable');
    
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const sortBy = this.getAttribute('data-sort');
            const currentSort = new URLSearchParams(window.location.search).get('sort');
            const currentSortDir = new URLSearchParams(window.location.search).get('sort_dir') || 'asc';
            
            // Toggle sort direction if clicking the same column
            const newSortDir = (sortBy === currentSort && currentSortDir === 'asc') ? 'desc' : 'asc';
            
            // Update URL with new sort parameters
            const url = new URL(window.location.href);
            url.searchParams.set('sort', sortBy);
            url.searchParams.set('sort_dir', newSortDir);
            
            // Reset to first page when changing sort
            url.searchParams.set('page', 1);
            
            window.location.href = url.toString();
        });
    });
}

/**
 * Initialize search form submission
 */
function initSearchForm() {
    const searchForm = document.getElementById('searchForm');
    if (!searchForm) return;
    
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const searchInput = document.getElementById('searchInput');
        const searchValue = searchInput.value.trim();
        
        const url = new URL(window.location.href);
        
        if (searchValue) {
            url.searchParams.set('search', searchValue);
        } else {
            url.searchParams.delete('search');
        }
        
        // Reset to first page when searching
        url.searchParams.set('page', 1);
        
        window.location.href = url.toString();
    });
}

/**
 * Initialize status filter
 */
function initStatusFilter() {
    const filterSelect = document.getElementById('filterSelect');
    if (!filterSelect) return;
    
    filterSelect.addEventListener('change', function() {
        const filterValue = this.value;
        const url = new URL(window.location.href);
        
        if (filterValue) {
            url.searchParams.set('filter', filterValue);
        } else {
            url.searchParams.delete('filter');
        }
        
        // Reset to first page when changing filter
        url.searchParams.set('page', 1);
        
        window.location.href = url.toString();
    });
}

/**
 * Initialize per page selector
 */
function initPerPageSelector() {
    const perPageSelect = document.getElementById('perPageSelect');
    if (!perPageSelect) return;
    
    perPageSelect.addEventListener('change', function() {
        const perPage = this.value;
        const url = new URL(window.location.href);
        
        if (perPage) {
            url.searchParams.set('per_page', perPage);
            // Reset to first page when changing items per page
            url.searchParams.set('page', 1);
        }
        
        window.location.href = url.toString();
    });
}

/**
 * Initialize bulk delete button
 */
function initBulkDeleteButton() {
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    const bulkActionForm = document.getElementById('bulkActionForm');
    const bulkItemIds = document.getElementById('bulkItemIds');
    
    if (!bulkDeleteBtn || !bulkActionForm || !bulkItemIds) return;
    
    bulkDeleteBtn.addEventListener('click', function() {
        const selectedItems = document.querySelectorAll('.item-checkbox:checked');
        const itemIds = Array.from(selectedItems).map(checkbox => checkbox.dataset.serial);
        
        if (itemIds.length === 0) {
            alert('Please select at least one item to delete.');
            return;
        }
        
        if (confirm(`Are you sure you want to delete ${itemIds.length} selected item(s)?`)) {
            bulkItemIds.value = JSON.stringify(itemIds);
            bulkActionForm.submit();
        }
    });
}

/**
 * Initialize date pickers
 */
function initDatePickers() {
    // Check if modern-datepicker is loaded
    if (typeof ModernDatepicker !== 'undefined') {
        // ModernDatepicker is already initialized by modern-datepicker.js
        console.log('Modern date picker is already initialized');
    } else {
        console.warn('Modern date picker not found, falling back to native date inputs');
        // Fallback to native date inputs
        document.querySelectorAll('input[type="date"]').forEach(input => {
            if (!input.type) {
                input.type = 'date';
            }
        });
    }
}
