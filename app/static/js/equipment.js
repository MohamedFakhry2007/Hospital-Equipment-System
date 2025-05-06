document.addEventListener('DOMContentLoaded', function() {
    // Search/Filter functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filterEquipment);
    }

    // Delete confirmations
    const deleteLinks = document.querySelectorAll('.delete-link');
    deleteLinks.forEach(link => {
        link.addEventListener('click', confirmDelete);
    });
});

function filterEquipment() {
    const filterValue = document.getElementById('searchInput').value.toLowerCase();
    const tableRows = document.querySelectorAll('tbody tr');

    tableRows.forEach(row => {
        const rowData = row.textContent.toLowerCase();
        if (rowData.includes(filterValue)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function confirmDelete(event) {
    event.preventDefault(); // Prevent default link action
    const link = event.currentTarget;
    const url = link.href;
    const mfgSerial = link.dataset.mfgSerial; // Get MFG_SERIAL from data attribute
    const data_type = link.dataset.dataType; // Get data_type from data attribute

    if (confirm(`Are you sure you want to delete equipment with serial: ${mfgSerial}?`)) {
        // Proceed with deletion
        fetch(`/api/equipment/${data_type}/${mfgSerial}`, {
            method: 'DELETE',
        })
        .then(response => {
            if (response.ok) {
                window.location.reload(); // Reload page after successful deletion
            } else {
                alert('Failed to delete equipment.');
            }
        });
    }
}
// Bulk delete functionality
document.addEventListener('DOMContentLoaded', function() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const itemCheckboxes = document.querySelectorAll('.item-checkbox');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');

    // Toggle all checkboxes
    selectAllCheckbox?.addEventListener('change', function() {
        itemCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
        });
        updateBulkDeleteButton();
    });

    // Update bulk delete button visibility
    itemCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBulkDeleteButton);
    });

    function updateBulkDeleteButton() {
        const checkedCount = document.querySelectorAll('.item-checkbox:checked').length;
        bulkDeleteBtn.style.display = checkedCount > 0 ? 'inline-block' : 'none';
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
