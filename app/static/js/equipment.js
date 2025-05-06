
document.addEventListener('DOMContentLoaded', function() {
    // Get all control elements
    const searchInput = document.getElementById('searchInput');
    const filterSelect = document.getElementById('filterSelect');
    const sortSelect = document.getElementById('sortSelect');
    const tableBody = document.querySelector('tbody');
    
    // Add event listeners
    if (searchInput) searchInput.addEventListener('input', updateTable);
    if (filterSelect) filterSelect.addEventListener('change', updateTable);
    if (sortSelect) sortSelect.addEventListener('change', updateTable);

    function updateTable() {
        const rows = Array.from(tableBody.getElementsByTagName('tr'));
        const searchTerm = searchInput.value.toLowerCase();
        const filterValue = filterSelect.value;
        const sortColumn = sortSelect.value;

        // Filter and search
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const ppmValue = row.querySelector('td:nth-child(7)').textContent; // PPM column
            const matchesSearch = text.includes(searchTerm);
            const matchesFilter = !filterValue || ppmValue === filterValue;
            row.style.display = matchesSearch && matchesFilter ? '' : 'none';
        });

        // Sort
        if (sortColumn) {
            const visibleRows = rows.filter(row => row.style.display !== 'none');
            const sortedRows = visibleRows.sort((a, b) => {
                const columnIndex = getColumnIndex(sortColumn);
                const aValue = a.cells[columnIndex].textContent;
                const bValue = b.cells[columnIndex].textContent;
                return aValue.localeCompare(bValue);
            });

            // Re-append sorted rows
            sortedRows.forEach(row => tableBody.appendChild(row));
        }
    }

    function getColumnIndex(columnName) {
        const columnMap = {
            'EQUIPMENT': 1,
            'MODEL': 2,
            'MFG_SERIAL': 3,
            'MANUFACTURER': 4
        };
        return columnMap[columnName] || 0;
    }

    // Bulk delete functionality
    const selectAllCheckbox = document.getElementById('selectAll');
    const itemCheckboxes = document.querySelectorAll('.item-checkbox');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');

    // Toggle all checkboxes
    selectAllCheckbox?.addEventListener('change', function() {
        itemCheckboxes.forEach(checkbox => {
            const row = checkbox.closest('tr');
            if (row.style.display !== 'none') { // Only check visible rows
                checkbox.checked = selectAllCheckbox.checked;
            }
        });
        updateBulkDeleteButton();
    });

    // Update bulk delete button visibility
    itemCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBulkDeleteButton);
    });

    function updateBulkDeleteButton() {
        const checkedCount = document.querySelectorAll('.item-checkbox:checked').length;
        if (bulkDeleteBtn) {
            bulkDeleteBtn.style.display = checkedCount > 0 ? 'inline-block' : 'none';
        }
    }

    // Handle bulk delete
    bulkDeleteBtn?.addEventListener('click', async function() {
        const selectedSerials = Array.from(document.querySelectorAll('.item-checkbox:checked'))
            .map(checkbox => checkbox.dataset.serial);
        
        if (!selectedSerials.length) return;

        if (!confirm(`Are you sure you want to delete ${selectedSerials.length} selected records?`)) {
            return;
        }

        try {
            const dataType = window.location.pathname.includes('ppm') ? 'ppm' : 'ocm';
            const response = await fetch(`/api/bulk_delete/${dataType}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ serials: selectedSerials })
            });

            const result = await response.json();
            
            if (result.success) {
                alert(`Successfully deleted ${result.deleted_count} records.`);
                window.location.reload();
            } else {
                alert('Error occurred during deletion.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred during bulk deletion.');
        }
    });
});
