import { colors } from './config.js';

const serviceStatusCtx = document.getElementById('serviceStatusChart').getContext('2d');
export let serviceStatusChart = new Chart(serviceStatusCtx, {
    type: 'doughnut',
    data: {
        labels: ['Healthy', 'Degraded', 'Down'],
        datasets: [{
            data: [0, 0, 0], 
            backgroundColor: [colors.brightGreen, colors.orangeGold, colors.alertRed],
            borderWidth: 2,
            borderColor: colors.widgetBg,
        }]
    },
    options: {
        maintainAspectRatio: false,
        plugins: { 
            legend: { 
                display: false,
                position: 'bottom', 
                labels: { color: colors.textMuted, font: { size: 12 } } 
            } 
        },
        cutout: '70%', 
        layout: { padding: 0 },
        animation: { duration: 800, easing: 'easeOutQuart' }
    }
});

const inlinePieCtx = document.getElementById('inlinePieChart') ? document.getElementById('inlinePieChart').getContext('2d') : null;
export let inlinePieChart = inlinePieCtx ? new Chart(inlinePieCtx, {
    type: 'doughnut',
    data: {
        labels: ['Healthy', 'Degraded', 'Down'],
        datasets: [{
            data: [0, 0, 0],
            backgroundColor: [colors.brightGreen, colors.orangeGold, colors.alertRed],
            borderWidth: 2,
            borderColor: '#232d45',
        }]
    },
    options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        cutout: '68%',
        layout: { padding: 0 },
        animation: { duration: 600 }
    }
}) : null;

const detailedTrafficCtx = document.getElementById('detailedTrafficChart').getContext('2d');
export let detailedTrafficChart = new Chart(detailedTrafficCtx, {
    type: 'line',
    data: {
        labels: ['T-30', 'T-25', 'T-20', 'T-15', 'T-10', 'T-5', 'Now'],
        datasets: [
            { label: 'CPU Usage (%)', data: [0, 0, 0, 0, 0, 0, 0], borderColor: colors.lineChartBlue, borderWidth: 2, fill: false, tension: 0.4, pointRadius: 0 },
            { label: 'Memory Usage (%)', data: [0, 0, 0, 0, 0, 0, 0], borderColor: colors.brightGreen, borderWidth: 2, borderDash: [5, 5], fill: false, tension: 0.4, pointRadius: 0 }
        ]
    },
    options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { color: colors.gridColor }, ticks: { color: colors.textMuted } },
            y: { beginAtZero: true, max: 100, grid: { color: colors.gridColor }, ticks: { color: colors.textMuted, stepSize: 20 } }
        },
        animation: { duration: 0 }
    }
});

const telemetryAiCtx = document.getElementById('telemetryAiChart').getContext('2d');
export let telemetryAiChart = new Chart(telemetryAiCtx, {
    type: 'line',
    data: {
        labels: Array.from({length: 30}, (_, i) => `T-${29 - i}`),
        datasets: [
            {
                label: 'Memory Load (%)',
                data: Array(30).fill(0),
                borderColor: colors.brightGreen,
                borderWidth: 2,
                fill: true,
                backgroundColor: 'rgba(94, 224, 132, 0.1)',
                tension: 0.4,
                pointRadius: 0,
                yAxisID: 'y'
            },
            {
                label: 'CPU Load (%)',
                data: Array(30).fill(0),
                borderColor: colors.lineChartBlue,
                borderWidth: 2,
                fill: false,
                tension: 0.4,
                pointRadius: 0,
                yAxisID: 'y'
            },
            {
                label: 'AI Confidence (%)',
                data: Array(30).fill(0),
                borderColor: colors.orangeGold,
                borderWidth: 3,
                fill: false,
                stepped: true,
                pointRadius: 0,
                yAxisID: 'y1'
            }
        ]
    },
    options: {
        maintainAspectRatio: false,
        plugins: { 
            legend: { position: 'top', labels: { color: colors.textMuted, boxWidth: 12, font: { size: 11 } } }
        },
        scales: {
            x: { grid: { color: colors.gridColor }, ticks: { display: false } },
            y: {
                type: 'linear',
                display: true,
                position: 'left',
                beginAtZero: true,
                max: 100,
                grid: { color: colors.gridColor },
                ticks: { color: colors.textMuted, callback: function(value) { return value + '%'; } }
            },
            y1: {
                type: 'linear',
                display: true,
                position: 'right',
                beginAtZero: true,
                max: 100,
                grid: { drawOnChartArea: false },
                ticks: { color: colors.orangeGold, callback: function(value) { return value + '%'; } }
            }
        },
        animation: { duration: 0 }
    }
});

const bottleneckRadarCtx = document.getElementById('bottleneckRadarChart').getContext('2d');
export let bottleneckRadarChart = new Chart(bottleneckRadarCtx, {
    type: 'radar',
    data: {
        labels: ['Frontend', 'Payment', 'Checkout', 'Catalog', 'Cart', 'Recommends'],
        datasets: [{
            label: 'Latency Load',
            data: [0, 0, 0, 0, 0, 0],
            backgroundColor: 'rgba(94, 224, 132, 0.2)',
            borderColor: colors.brightGreen,
            pointBackgroundColor: colors.brightGreen,
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: colors.brightGreen
        }]
    },
    options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            r: {
                angleLines: { color: colors.gridColor },
                grid: { color: colors.gridColor },
                pointLabels: { color: colors.textMuted, font: { size: 10 } },
                ticks: { display: false, min: 0, max: 100 }
            }
        },
        animation: { duration: 400 }
    }
});

const bottleneckRadarExpandedEl = document.getElementById('bottleneckRadarChartExpanded');
export let bottleneckRadarChartExpanded = bottleneckRadarExpandedEl ? new Chart(bottleneckRadarExpandedEl.getContext('2d'), {
    type: 'radar',
    data: {
        labels: ['Frontend', 'Payment', 'Checkout', 'Catalog', 'Cart', 'Recommends'],
        datasets: [{
            label: 'Latency Load',
            data: [0, 0, 0, 0, 0, 0],
            backgroundColor: 'rgba(94, 224, 132, 0.15)',
            borderColor: colors.brightGreen,
            borderWidth: 2,
            pointBackgroundColor: colors.brightGreen,
            pointBorderColor: '#fff',
            pointRadius: 4,
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: colors.brightGreen
        }]
    },
    options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            r: {
                angleLines: { color: colors.gridColor },
                grid: { color: colors.gridColor },
                pointLabels: { color: colors.textMuted, font: { size: 13 } },
                ticks: { display: false, min: 0, max: 100 }
            }
        },
        animation: { duration: 400 }
    }
}) : null;

const serviceTrafficBarCtx = document.getElementById('serviceTrafficBarChart').getContext('2d');
export let serviceTrafficBarChart = new Chart(serviceTrafficBarCtx, {
    type: 'bar',
    data: {
        labels: ['Frontend', 'Payment', 'Checkout', 'Catalog', 'Cart', 'Recommends'],
        datasets: [{
            label: 'Requests per Second',
            data: [0, 0, 0, 0, 0, 0],
            backgroundColor: colors.lineChartBlue,
            borderRadius: 4
        }]
    },
    options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { display: false }, ticks: { color: colors.textMuted } },
            y: { beginAtZero: true, grid: { color: colors.gridColor }, ticks: { color: colors.textMuted } }
        }
    }
});