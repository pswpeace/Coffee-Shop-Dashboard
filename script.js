document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/sales-data')
        .then(response => response.json())
        .then(data => {
            console.log("Data received:", data);
            // logic to update Chart.js goes here
        });
});