document.addEventListener('DOMContentLoaded', async () => {
    const listContainer = document.getElementById('report-list');
    const dashboard = document.getElementById('dashboard');
    
    let reports = [];

    try {
        const response = await fetch('/api/reports');
        reports = await response.json();
        renderList(reports);
    } catch (err) {
        listContainer.innerHTML = '<div style="padding: 20px; color: red;">Failed to load reports. Ensure ui_server.py is running.</div>';
    }

    function renderList(data) {
        listContainer.innerHTML = '';
        if (data.length === 0) {
            listContainer.innerHTML = '<div style="padding: 20px;">No reports found in outputs/ folder.</div>';
            return;
        }

        data.forEach(report => {
            const item = document.createElement('div');
            item.className = 'report-item';
            
            const score = (report.final_utility_score || 0).toFixed(2);
            const badgeClass = score < 0.5 ? 'low-score' : '';
            
            item.innerHTML = `
                <span class="report-id">${report.report_id}</span>
                <span class="report-score-badge ${badgeClass}">${score}</span>
            `;
            
            item.addEventListener('click', () => {
                document.querySelectorAll('.report-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
                renderDashboard(report);
            });
            
            listContainer.appendChild(item);
        });
    }

    async function renderDashboard(report) {
        dashboard.style.display = 'block';
        
        document.getElementById('report-title').innerText = report.report_id;
        document.getElementById('final-score').innerText = (report.final_utility_score || 0).toFixed(2);
        
        const comps = report.components || {};
        const cov = comps.coverage_score || 0;
        const val = comps.validation_score || 0;
        const sig = comps.signal_score || 0;
        const noi = comps.noise_score || 0;
        
        document.getElementById('score-coverage').innerText = cov.toFixed(2);
        document.getElementById('bar-coverage').style.width = `${cov * 100}%`;
        
        document.getElementById('score-validation').innerText = val.toFixed(2);
        document.getElementById('bar-validation').style.width = `${val * 100}%`;
        
        document.getElementById('score-signal').innerText = sig.toFixed(2);
        document.getElementById('bar-signal').style.width = `${sig * 100}%`;
        
        document.getElementById('score-noise').innerText = noi.toFixed(2);
        document.getElementById('bar-noise').style.width = `${noi * 100}%`;
        
        // Render Weaknesses
        const weakContainer = document.getElementById('weaknesses-container');
        weakContainer.innerHTML = '';
        
        let hasWeaknesses = false;
        if (report.diagnostics && report.diagnostics.failure_reasons && report.diagnostics.failure_reasons.length > 0) {
            hasWeaknesses = true;
            report.diagnostics.failure_reasons.forEach(f => {
                weakContainer.innerHTML += `<div class="bullet-item"><strong>${f.dimension.toUpperCase()}:</strong> ${f.issue} (${f.evidence})</div>`;
            });
        }
        
        if (report.diagnostics && report.diagnostics.missing_information && report.diagnostics.missing_information.length > 0) {
            hasWeaknesses = true;
            report.diagnostics.missing_information.forEach(m => {
                weakContainer.innerHTML += `<div class="bullet-item">${m}</div>`;
            });
        }
        
        if (!hasWeaknesses) {
            weakContainer.innerHTML = '<div class="bullet-item" style="color: #1f2937;">No critical weaknesses identified.</div>';
        }

        // Render Strengths
        const strContainer = document.getElementById('strengths-container');
        strContainer.innerHTML = '';
        if (report.diagnostics && report.diagnostics.why_report_is_useful_or_not && report.diagnostics.why_report_is_useful_or_not.length > 0) {
            report.diagnostics.why_report_is_useful_or_not.forEach(s => {
                strContainer.innerHTML += `<div class="bullet-item">${s}</div>`;
            });
        } else {
            strContainer.innerHTML = '<div class="bullet-item" style="color: #1f2937;">No distinct analytical strengths.</div>';
        }
        // Fetch and Render XML
        const xmlContainer = document.getElementById('xml-content');
        xmlContainer.innerHTML = '<div style="padding: 16px; color: var(--text-secondary); font-size: 13px;">Loading structured data...</div>';
        try {
            const xmlRes = await fetch(`/api/xml/${report.report_id}`);
            if (xmlRes.ok) {
                const xmlText = await xmlRes.text();
                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(xmlText, "text/xml");
                
                xmlContainer.innerHTML = '';
                const table = document.createElement('table');
                table.style.width = '100%';
                table.style.borderCollapse = 'collapse';
                
                const elements = xmlDoc.querySelectorAll('*');
                elements.forEach(el => {
                    if (el.children.length === 0 && el.textContent.trim() !== '') {
                        const tr = document.createElement('tr');
                        const isReason = el.tagName.toLowerCase() === 'reason';
                        
                        let labelStyle = "padding: 12px 16px; border-bottom: 1px solid var(--border-color); width: 25%; font-weight: 600; font-size: 11px; color: var(--text-secondary); text-transform: uppercase; vertical-align: top;";
                        
                        if (isReason) {
                            tr.innerHTML = `
                                <td style="${labelStyle}">${el.tagName}</td>
                                <td style="padding: 12px 16px; border-bottom: 1px solid var(--border-color); font-size: 13px; color: var(--text-primary); line-height: 1.6; background-color: #f8fafc;">${el.textContent.trim()}</td>
                            `;
                        } else {
                            tr.innerHTML = `
                                <td style="${labelStyle}">${el.tagName}</td>
                                <td style="padding: 12px 16px; border-bottom: 1px solid var(--border-color); font-size: 13px; color: var(--text-primary); font-family: monospace;">${el.textContent.trim()}</td>
                            `;
                        }
                        table.appendChild(tr);
                    }
                });
                xmlContainer.appendChild(table);
            } else {
                xmlContainer.innerHTML = '<div style="padding: 16px; color: #ef4444; font-size: 13px;">XML report source not found on disk.</div>';
            }
        } catch(e) {
            xmlContainer.innerHTML = '<div style="padding: 16px; color: #ef4444; font-size: 13px;">Error loading XML source.</div>';
        }
    }
});
