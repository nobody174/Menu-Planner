function toggleChecked() {
    const checkboxes = document.querySelectorAll('.shopping-checkbox');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);

    checkboxes.forEach(checkbox => {
        checkbox.checked = !allChecked;
    });
}

function refreshMenu() {
    if (!confirm('Generer ny ukemeny? Dette vil erstatte den eksisterende menyen.')) {
        return;
    }

    fetch('/api/regenerate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Ny meny generert! Siden vil nå laste på nytt.');
            location.reload();
        } else {
            alert('Feil ved generering av meny: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Feil ved kontakt med server');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const checkboxes = document.querySelectorAll('.shopping-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            localStorage.setItem('shopping-' + this.parentElement.textContent, this.checked);
        });

        const saved = localStorage.getItem('shopping-' + checkbox.parentElement.textContent);
        if (saved === 'true') {
            checkbox.checked = true;
        }
    });
});

function clearShopping() {
    localStorage.clear();
    const checkboxes = document.querySelectorAll('.shopping-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
}
