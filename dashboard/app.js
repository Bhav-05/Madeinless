import { colors } from './config.js';
import { 
    serviceStatusChart, inlinePieChart, detailedTrafficChart, 
    telemetryAiChart, bottleneckRadarChart, bottleneckRadarChartExpanded, 
    serviceTrafficBarChart 
} from './charts.js';
import { addLogbookEntry, initTerminal, setupWidgetInteractions } from './ui.js';

async function updateDashboard() {
    try {
        const response = await fetch('http://localhost:8000/api/v1/dashboard/state');
        const data = await response.json();

        // --- Microservices Table ---
        const tbody = document.getElementById('microservices-tbody');
        if (tbody) {
            tbody.innerHTML = '';
            data.microservices.forEach(item => {
                const tr = document.createElement('tr');

                // FIX: don't show "WAITING..." — if server has no AI classification yet,
                // show "Normal" (no webhook has fired = no anomaly detected).
                const anomalyText = (!item.log_anomaly || item.log_anomaly === 'WAITING...')
                    ? 'Normal'
                    : item.log_anomaly;

                let nlpClass = 'text-good';
                if (anomalyText !== 'Normal' && anomalyText !== 'None') {
                    nlpClass = anomalyText.toLowerCase().includes('warn') ? 'text-warn' : 'text-alert';
                }

                let confStatus = 'good';
                if (item.ai_confidence > 80) confStatus = 'alert';
                else if (item.ai_confidence > 50) confStatus = 'warn';

                let actionClass = item.remediation && item.remediation !== 'None' ? 'text-good' : 'text-muted';

                // FIX: backend sends net_out KB/s labelled as latency_ms — display correctly
                const latencyDisplay = item.latency_ms > 0
                    ? `${item.latency_ms} KB/s`
                    : '0 KB/s';

                tr.innerHTML = `
                    <td>${item.name}</td>
                    <td><div class="bar-wrap"><div class="bar ${item.latency_status}" style="width: ${item.latency_pct}%">${latencyDisplay}</div></div></td>
                    <td><span class="${nlpClass}">${anomalyText}</span></td>
                    <td>${item.metric_state || 'UNKNOWN'}</td>
                    <td><div class="bar-wrap"><div class="bar ${confStatus}" style="width: ${Math.max(item.ai_confidence, 0)}%">${item.ai_confidence}%</div></div></td>
                    <td><span class="${actionClass}">${item.remediation || 'None'}</span></td>
                `;
                tbody.appendChild(tr);
            });
        }

        // --- Global Metric Cards ---
        const slaEl = document.getElementById('val-sla');
        if (slaEl) slaEl.innerText = data.global_metrics.last_remediation_sla_seconds + 's';

        const logsEl = document.querySelector('.stat-card:nth-child(2) .stat-value');
        if (logsEl) logsEl.innerHTML = `${data.global_metrics.logs_ingested_per_sec}<span>↑</span>`;

        const anomalyEl = document.getElementById('val-anomalies');
        if (anomalyEl) {
            anomalyEl.innerText = data.global_metrics.active_anomalies;
            anomalyEl.className = data.global_metrics.active_anomalies > 0 ? 'stat-value text-alert' : 'stat-value text-good';
        }

        const confEl = document.getElementById('val-confidence');
        if (confEl) confEl.innerText = data.global_metrics.peak_ai_confidence_pct + '%';

        const recEl = document.getElementById('val-recoveries');
        if (recEl) recEl.innerText = data.global_metrics.total_auto_recoveries;

        const suppEl = document.querySelector('.stat-card:nth-child(6) .stat-value');
        if (suppEl) suppEl.innerText = data.global_metrics.alerts_suppressed;

        // --- Hardware Charts ---
        detailedTrafficChart.data.datasets[0].data = data.hardware_charts.cpu_usage_pct.slice(-7);
        detailedTrafficChart.data.datasets[1].data = data.hardware_charts.memory_usage_pct.slice(-7);
        detailedTrafficChart.update();

        telemetryAiChart.data.datasets[0].data = data.hardware_charts.memory_usage_pct;
        telemetryAiChart.data.datasets[1].data = data.hardware_charts.cpu_usage_pct;
        telemetryAiChart.data.datasets[2].data = data.hardware_charts.ai_conf_pct;
        telemetryAiChart.update();

        // --- Radar / Bar Charts ---
        bottleneckRadarChart.data.datasets[0].data = data.microservices.map(m => m.latency_pct);
        let radarColor = data.global_metrics.active_anomalies > 0 ? colors.alertRed : colors.brightGreen;
        bottleneckRadarChart.data.datasets[0].borderColor = radarColor;
        bottleneckRadarChart.data.datasets[0].pointBackgroundColor = radarColor;
        bottleneckRadarChart.data.datasets[0].pointHoverBorderColor = radarColor;
        bottleneckRadarChart.update();

        if (bottleneckRadarChartExpanded) {
            bottleneckRadarChartExpanded.data.datasets[0].data = data.microservices.map(m => m.latency_pct);
            bottleneckRadarChartExpanded.data.datasets[0].borderColor = radarColor;
            bottleneckRadarChartExpanded.data.datasets[0].backgroundColor =
                radarColor === colors.alertRed ? 'rgba(224,70,70,0.15)' : 'rgba(94,224,132,0.15)';
            bottleneckRadarChartExpanded.data.datasets[0].pointBackgroundColor = radarColor;
            bottleneckRadarChartExpanded.update();
        }

        serviceTrafficBarChart.data.datasets[0].data = data.traffic_rps;
        serviceTrafficBarChart.update();

        // --- FIX: Pie Chart counts derived entirely from server data, no hardcoded 6 ---
        const totalServices = data.microservices.length;
        let degradedCount = 0;
        let downCount = 0;
        data.microservices.forEach(m => {
            if (m.latency_status === 'alert') downCount++;
            else if (m.latency_status === 'warn') degradedCount++;
        });
        const healthyCount = totalServices - degradedCount - downCount;

        serviceStatusChart.data.datasets[0].data = [healthyCount, degradedCount, downCount];
        serviceStatusChart.options.plugins.legend.display = (degradedCount > 0 || downCount > 0);
        serviceStatusChart.update();

        if (inlinePieChart) {
            inlinePieChart.data.datasets[0].data = [healthyCount, degradedCount, downCount];
            inlinePieChart.update();
        }

        const inlinePieLabel = document.getElementById('inline-pie-label');
        if (inlinePieLabel) {
            const issues = downCount + degradedCount;
            inlinePieLabel.textContent = issues === 0
                ? 'Status: OK'
                : `${issues} Issue${issues > 1 ? 's' : ''}`;
            inlinePieLabel.style.color = issues === 0
                ? colors.brightGreen
                : (downCount > 0 ? colors.alertRed : colors.orangeGold);
        }

        const overlayOk = document.getElementById('status-ok-label');
        if (overlayOk) {
            if (totalServices > 0 && downCount === 0 && degradedCount === 0) {
                overlayOk.classList.add('visible');
            } else {
                overlayOk.classList.remove('visible');
            }
        }

        // --- Live Terminal: render log stream from backend ---
        const terminal = document.getElementById('live-terminal');
        if (terminal && data.log_stream) {
            const logs = data.log_stream;
            const lastLog = logs.length > 0 ? logs[logs.length - 1].log_text : '';

            if (terminal.dataset.lastLog !== lastLog) {
                terminal.innerHTML = '';
                logs.forEach(log => {
                    const line = document.createElement('div');
                    line.className = 'term-line';

                    let badgeColor = '#94a0b3';
                    if (log.badge_type === 'INFO') badgeColor = '#3b79f6';
                    if (log.badge_type === 'WARN') badgeColor = '#f5a623';
                    if (log.badge_type === 'CRIT') badgeColor = '#e04646';
                    if (log.badge_type === 'SYS')  badgeColor = '#5ee084';
                    if (log.badge_type === 'AI')   badgeColor = '#3b79f6';

                    let textColor = 'var(--text-main)';
                    if (log.classification === 'CRITICAL') textColor = '#e04646';
                    if (log.classification === 'WARNING')  textColor = '#f5a623';
                    if (log.classification === 'RESOLVED') textColor = '#5ee084';

                    line.innerHTML = `
                        <span class="term-timestamp">${log.timestamp}</span>
                        <span class="term-badge" style="background:${badgeColor}18; color:${badgeColor}; border:1px solid ${badgeColor}50;">${log.badge_type}</span>
                        <span class="term-text" style="color:${textColor};">${log.log_text}</span>`;

                    terminal.appendChild(line);
                });
                terminal.scrollTop = terminal.scrollHeight;
                terminal.dataset.lastLog = lastLog;
            }
        }

        // --- FIX: Resolution Logbook populated from latest_remediation ---
        if (data.latest_remediation) {
            const rem = data.latest_remediation;
            // Use received_at + service as a unique key so we only add each entry once
            const logbookKey = `${rem.received_at}::${rem.service}`;

            if (window._lastLogbookKey !== logbookKey) {
                window._lastLogbookKey = logbookKey;

                const conf = Math.round((rem.total_confidence || 0) * 100);
                let resolutionLabel;

                if (conf < 50) {
                    resolutionLabel = `False Positive — ${conf}% confidence (below threshold), no action taken`;
                } else {
                    const action = (rem.action_taken || 'auto_restart').replace(/_/g, ' ');
                    const summary = rem.log_anomaly_summary || rem.remediation_type || 'anomaly';
                    resolutionLabel = `${action} → resolved "${summary}"`;
                }

                addLogbookEntry(
                    rem.service,
                    resolutionLabel,
                    rem.restart_latency_sec != null ? rem.restart_latency_sec.toFixed(2) : '?'
                );
            }
        }

    } catch (_err) {
        // Backend offline — fail silently
    }
}

async function injectChaos(service, faultType) {
    try {
        await fetch('http://localhost:8000/api/v1/chaos/inject', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_service: service, fault_type: faultType })
        });
    } catch (_err) {
        console.error('Failed to reach backend API.');
    }
}

// --- Chaos Buttons ---
const btnPayment = document.getElementById('btn-trigger-payment');
if (btnPayment) btnPayment.addEventListener('click', (e) => { e.stopPropagation(); injectChaos('payment', 'oom'); });

const btnCheckout = document.getElementById('btn-trigger-checkout');
if (btnCheckout) btnCheckout.addEventListener('click', (e) => { e.stopPropagation(); injectChaos('checkout', 'timeout'); });

const btnCatalog = document.getElementById('btn-trigger-catalog');
if (btnCatalog) btnCatalog.addEventListener('click', (e) => { e.stopPropagation(); injectChaos('catalog', 'deadlock'); });

const btnCart = document.getElementById('btn-trigger-cart');
if (btnCart) btnCart.addEventListener('click', (e) => { e.stopPropagation(); injectChaos('cart', 'sync_fail'); });

// --- Init ---
initTerminal();
setupWidgetInteractions();
updateDashboard();
setInterval(updateDashboard, 500);