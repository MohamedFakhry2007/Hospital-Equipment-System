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
