// --- CONFIG ---
let currentShop = 'Overall';
let currentMonth = 'Overall';

// Chart Instances
let chartPieSales, chartPieQty, chartLine;

// --- INIT ---
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setupFilters();
    fetchData();
});

function setupFilters() {
    // Helper to handle button clicks for both groups
    const bindGroup = (id, type) => {
        const group = document.getElementById(id);
        if(!group) return;

        group.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // 1. Reset visual state for this group
                group.querySelectorAll('button').forEach(b => {
                    b.classList.remove(type === 'shop' ? 'btn-primary' : 'btn-secondary', 'active');
                    b.classList.add(type === 'shop' ? 'btn-outline-primary' : 'btn-outline-secondary');
                });

                // 2. Set active state for clicked button
                const clicked = e.currentTarget;
                clicked.classList.remove(type === 'shop' ? 'btn-outline-primary' : 'btn-outline-secondary');
                clicked.classList.add(type === 'shop' ? 'btn-primary' : 'btn-secondary', 'active');

                // 3. Update Global State
                if(type === 'shop') currentShop = clicked.getAttribute('data-val');
                else currentMonth = clicked.getAttribute('data-val');
                
                // 4. Fetch New Data
                fetchData();
            });
        });
    };

    bindGroup('shop-filters', 'shop');
    bindGroup('month-filters', 'month');
}

function fetchData() {
    const url = `/api/dashboard_data?shop=${currentShop}&month=${currentMonth}`;
    console.log("Fetching:", url);

    fetch(url)
        .then(r => r.json())
        .then(data => {
            updateMetrics(data.metrics);
            updatePies(data.pie_data);
            updateLine(data.line_data);
            updateTable(data.table_data);
        })
        .catch(err => console.error("Error fetching data:", err));
}

function updateMetrics(m) {
    if(!m) return;
    const fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
    const el = document.getElementById('total-revenue');
    if(el) el.innerText = "Total Rev: " + fmt.format(m.total_revenue);
}

function updatePies(data) {
    if(!data || !data.sales) return;

    const fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumSignificantDigits: 3 });
    
    // Update Sales Pie
    if(chartPieSales) {
        chartPieSales.data.labels = data.labels;
        chartPieSales.data.datasets[0].data = data.sales;
        chartPieSales.update();
        
        const totalS = data.sales.reduce((a,b)=>a+b, 0);
        const el = document.getElementById('pie-sales-total');
        if(el) el.innerText = fmt.format(totalS);
    }

    // Update Qty Pie
    if(chartPieQty) {
        chartPieQty.data.labels = data.labels;
        chartPieQty.data.datasets[0].data = data.qty;
        chartPieQty.update();

        const totalQ = data.qty.reduce((a,b)=>a+b, 0);
        const el = document.getElementById('pie-qty-total');
        if(el) el.innerText = totalQ.toLocaleString() + " Units";
    }
}

function updateLine(data) {
    if(chartLine && data) {
        chartLine.data.labels = data.dates;
        // Map datasets to ensure styling is preserved
        chartLine.data.datasets = data.datasets.map(ds => ({
            ...ds,
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.3,
            fill: false
        }));
        chartLine.update();
    }
}

function updateTable(rows) {
    const table = document.getElementById('main-table');
    if(!table) return;
    
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = ''; // Clear existing rows
    
    const fmt = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

    rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="ps-3 fw-bold text-secondary">${row.category}</td>
            
            <td class="text-end data-bar-cell">
                <div class="data-bar-bg" style="width: ${row.percent_sales}%; background-color: #d1e7dd;"></div>
                <span class="position-relative">${fmt.format(row.sales)}</span>
            </td>
            
            <td class="text-end text-muted small">${row.percent_sales.toFixed(1)}%</td>
            
            <td class="text-end">${fmt.format(row.avg_price)}</td>
            
            <td class="text-end pe-3 data-bar-cell">
                 <div class="data-bar-bg" style="width: ${row.percent_qty}%; background-color: #e2e3e5;"></div>
                 <span class="position-relative">${row.qty.toLocaleString()}</span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function initCharts() {
    const pieOpts = {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%', // Donut style
        plugins: { legend: { display: false } }
    };

    const colors = ['#2c3e50', '#e67e22', '#27ae60'];

    // 1. Sales Pie
    const ctxSales = document.getElementById('pieSales');
    if(ctxSales) {
        chartPieSales = new Chart(ctxSales.getContext('2d'), {
            type: 'doughnut',
            data: { labels: [], datasets: [{ data: [], backgroundColor: colors, borderWidth:0 }] },
            options: pieOpts
        });
    }

    // 2. Qty Pie
    const ctxQty = document.getElementById('pieQty');
    if(ctxQty) {
        chartPieQty = new Chart(ctxQty.getContext('2d'), {
            type: 'doughnut',
            data: { labels: [], datasets: [{ data: [], backgroundColor: colors, borderWidth:0 }] },
            options: pieOpts
        });
    }

    // 3. Line Chart
    const ctxLine = document.getElementById('lineChart');
    if(ctxLine) {
        chartLine = new Chart(ctxLine.getContext('2d'), {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: { legend: { position: 'top', labels: {boxWidth: 10} } },
                scales: { 
                    x: { grid: {display: false} },
                    y: { beginAtZero: true, grid: {borderDash: [5,5]} } 
                }
            }
        });
    }
}
