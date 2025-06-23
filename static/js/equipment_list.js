console.log('equipment_list.js loaded');

// Add selected class style only if not already added
if (!document.getElementById('equipment-table-styles')) {
    const style = document.createElement('style');
    style.id = 'equipment-table-styles';
    style.textContent = `
        .equipment-table tr.selected {
            background-color: #e2e6ea !important;
        }
        .item-checkbox:checked {
            background-color: #0d6efd;
            border-color: #0d6efd;
        }
    `;
    document.head.appendChild(style);
}

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page with equipment table
    const tableBody = document.querySelector('.equipment-table tbody');
    
    if (!tableBody) {
        console.log('No equipment table found on this page, skipping equipment_list.js initialization');
        return;
    }
    
    // UI Elements
    const searchInput = document.getElementById('searchInput');
    const filterSelect = document.getElementById('filterSelect');
    const sortSelect = document.getElementById('sortSelect');
    const selectAllCheckbox = document.getElementById('selectAll');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    const selectedCountSpan = document.getElementById('selectedCount');
    
    let sortDirection = 1;
    let lastSortColumn = '';
    
    // Event listeners for table controls
    searchInput?.addEventListener('input', updateTable);
    filterSelect?.addEventListener('change', updateTable);
    sortSelect?.addEventListener('change', () => {
        if (sortSelect.value === lastSortColumn) {
            sortDirection *= -1;
        } else {
            sortDirection = 1;
        }
        lastSortColumn = sortSelect.value;
        updateTable();
    });

    // Determine data type from URL
    const dataType = window.location.pathname.includes('ppm') ? 'ppm' : 'ocm';
    
    // Column map based on data type
    const columnMap = dataType === 'ppm' ? {
        'EQUIPMENT': 3,
        'MODEL': 4,
        'SERIAL': 5,
        'MANUFACTURER': 6
    } : {
        'Name': 3,
        'Model': 4,
        'Serial': 5,
        'Manufacturer': 6
    };

    // Table update function
    function updateTable() {
        try {
            console.log('Updating table:', {
                search: searchInput?.value || '',
                filter: filterSelect?.value || '',
                sort: sortSelect?.value || ''
            });

            const rows = Array.from(tableBody.getElementsByTagName('tr'));
            const searchTerm = (searchInput?.value || '').toLowerCase();
            const filterValue = (filterSelect?.value || '').toLowerCase();
            const sortColumn = sortSelect?.value || '';

            // Reset select all checkbox
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = false;
            }

            // Filter and search
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                const statusCell = row.querySelector('td span.badge');
                const statusValue = statusCell ? statusCell.textContent.trim().toLowerCase() : '';
                const matchesSearch = text.includes(searchTerm);
                const matchesFilter = !filterValue || statusValue === filterValue;
                row.style.display = matchesSearch && matchesFilter ? '' : 'none';
            });

            // Show no results message
            const visibleRows = rows.filter(row => row.style.display !== 'none');
            if (visibleRows.length === 0) {
                const colspan = tableBody.querySelector('tr')?.cells.length || 16;
                tableBody.innerHTML = `<tr><td colspan="${colspan}" class="text-center">No results found</td></tr>`;
                updateBulkDeleteButton();
                return;
            }

            // Sort
            if (sortColumn) {
                const sortedRows = visibleRows.sort((a, b) => {
                    const columnIndex = getColumnIndex(sortColumn);
                    const aValue = a.cells[columnIndex]?.textContent.trim() || '';
                    const bValue = b.cells[columnIndex]?.textContent.trim() || '';
                    return aValue.localeCompare(bValue) * sortDirection;
                });

                const fragment = document.createDocumentFragment();
                sortedRows.forEach(row => fragment.appendChild(row));
                rows.forEach(row => {
                    if (row.style.display === 'none') {
                        fragment.appendChild(row);
                    }
                });
                tableBody.innerHTML = '';
                tableBody.appendChild(fragment);
            }

            // Reattach checkbox event listeners
            attachCheckboxEventListeners();
            updateBulkDeleteButton();

        } catch (error) {
            console.error('Error in updateTable:', error);
        }
    }

    function getColumnIndex(columnName) {
        return columnMap[columnName] || 0;
    }

    // Checkbox functionality
    function attachCheckboxEventListeners() {
        const itemCheckboxes = document.querySelectorAll('.item-checkbox');

        selectAllCheckbox?.addEventListener('change', function() {
            const visibleRows = Array.from(tableBody.querySelectorAll('tr'))
                .filter(row => row.style.display !== 'none');
            
            visibleRows.forEach(row => {
                const checkbox = row.querySelector('.item-checkbox');
                if (checkbox) {
                    checkbox.checked = selectAllCheckbox.checked;
                    toggleRowSelection(checkbox);
                }
            });
        });

        itemCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                if (!checkbox.checked && selectAllCheckbox) {
                    selectAllCheckbox.checked = false;
                }
                toggleRowSelection(checkbox);
            });
        });
    }

    function toggleRowSelection(checkbox) {
        const row = checkbox.closest('tr');
        if (row) {
            if (checkbox.checked) {
                row.classList.add('selected');
            } else {
                row.classList.remove('selected');
            }
        }
        updateBulkDeleteButton();
    }

    function updateBulkDeleteButton() {
        const checkedCount = document.querySelectorAll('.item-checkbox:checked').length;
        console.log('updateBulkDeleteButton called, checkedCount:', checkedCount);
        
        if (bulkDeleteBtn) {
            bulkDeleteBtn.style.display = checkedCount > 0 ? 'inline-block' : 'none';
        }
        if (selectedCountSpan) {
            selectedCountSpan.textContent = checkedCount;
        }
    }

    // Initial setup
    attachCheckboxEventListeners();
    
    // Bulk delete functionality
    bulkDeleteBtn?.addEventListener('click', async function() {
        const checkedBoxes = document.querySelectorAll('.item-checkbox:checked');
        const selectedSerials = Array.from(checkedBoxes).map(checkbox => {
            return dataType === 'ppm' ? checkbox.dataset.serial : checkbox.closest('tr').querySelector('td:nth-child(6)').textContent.trim();
        });
        
        if (!selectedSerials.length) {
            alert('Please select at least one item to delete.');
            return;
        }

        if (!confirm(`Are you sure you want to delete ${selectedSerials.length} selected records?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/bulk_delete/${dataType}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ serials: selectedSerials })
            });

            const result = await response.json();

            if (result.success) {
                // Remove deleted rows from the table
                checkedBoxes.forEach(checkbox => {
                    const row = checkbox.closest('tr');
                    if (row) {
                        row.remove();
                    }
                });

                // Update counters
                updateBulkDeleteButton();
                
                // Show success message
                const message = `Successfully deleted ${result.deleted_count} record(s).` +
                    (result.not_found > 0 ? ` ${result.not_found} record(s) were not found.` : '');
                alert(message);
            } else {
                alert(`Failed to delete records: ${result.message || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error during bulk delete:', error);
            alert('Error occurred while deleting records. Please try again.');
        }
    });
});