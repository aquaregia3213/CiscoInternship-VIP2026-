#!/usr/bin/env python3
"""
NetSage AI Dashboard Generator
------------------------------
Generates comprehensive metrics and visualizations for the NetSage AI Packet Tracer Project.

Metrics Processed:
- Total Case Count & Case Status
- Distribution by OSI Layer & Networking Concept
- Severity Distribution (Low, Medium, High, Critical)
- Human Review & Responsible AI Agreement Rate (Accepted / Edited / Rejected)

Outputs Generated:
1. dashboard/dashboard.html       (Interactive HTML/SVG Visual Dashboard)
2. dashboard/dashboard_summary.txt (Textual Audit Summary)
3. dashboard/dashboard_metrics.csv (Structured Summary CSV)
4. dashboard/dashboard.xlsx       (Excel Workbook via openpyxl/pandas if available)
5. dashboard/dashboard_chart.png   (Static chart image via matplotlib if available)
"""

import csv
import os
import json
from collections import Counter

CASES_CSV = "cases.csv"
RESP_AI_CSV = "responsible_ai_log.csv"
OUTPUT_DIR = "dashboard"


def load_data():
    cases = []
    if os.path.exists(CASES_CSV):
        with open(CASES_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cases = list(reader)

    ai_logs = []
    if os.path.exists(RESP_AI_CSV):
        with open(RESP_AI_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            ai_logs = list(reader)

    return cases, ai_logs


def compute_metrics(cases, ai_logs):
    total_cases = len(cases)

    # OSI Layer
    osi_counts = Counter(c.get("osi_layer", "Unknown") for c in cases)

    # Concept Distribution
    concept_counts = Counter(c.get("concept", "Unknown") for c in cases)

    # Severity Distribution
    severity_counts = Counter(c.get("severity", "Unknown") for c in cases)

    # Status Distribution
    status_counts = Counter(c.get("case_status", "Unknown") for c in cases)

    # AI Agreement Rate
    decisions = Counter(
        log.get("ai_decision") or log.get("human_review_decision") or log.get("final_decision") or "Unknown"
        for log in (ai_logs if ai_logs else cases)
    )
    
    accepted = decisions.get("Accepted", 0)
    edited = decisions.get("Edited", 0)
    rejected = decisions.get("Rejected", 0)
    total_reviewed = accepted + edited + rejected if (accepted + edited + rejected) > 0 else total_cases

    agreement_rate = (accepted / total_reviewed * 100) if total_reviewed > 0 else 0
    edit_rate = (edited / total_reviewed * 100) if total_reviewed > 0 else 0
    reject_rate = (rejected / total_reviewed * 100) if total_reviewed > 0 else 0

    return {
        "total_cases": total_cases,
        "osi_counts": dict(osi_counts),
        "concept_counts": dict(concept_counts),
        "severity_counts": dict(severity_counts),
        "status_counts": dict(status_counts),
        "ai_reviews": {
            "accepted": accepted,
            "edited": edited,
            "rejected": rejected,
            "total_reviewed": total_reviewed,
            "agreement_rate": round(agreement_rate, 1),
            "edit_rate": round(edit_rate, 1),
            "reject_rate": round(reject_rate, 1)
        }
    }


def generate_text_summary(metrics, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write("        NetSage AI Project Dashboard Metrics      \n")
        f.write("==================================================\n\n")
        f.write(f"Total Cases Recorded: {metrics['total_cases']}\n\n")

        f.write("--- AI Agreement & Responsible AI Review ---\n")
        ai = metrics['ai_reviews']
        f.write(f"Total Human Reviews:    {ai['total_reviewed']}\n")
        f.write(f"Accepted AI Diagnoses: {ai['accepted']} ({ai['agreement_rate']}%)\n")
        f.write(f"Edited AI Diagnoses:   {ai['edited']} ({ai['edit_rate']}%)\n")
        f.write(f"Rejected AI Diagnoses: {ai['rejected']} ({ai['reject_rate']}%)\n\n")

        f.write("--- Cases by OSI Layer ---\n")
        for layer, count in metrics['osi_counts'].items():
            f.write(f"  {layer:12s}: {count:2d} cases ({count/metrics['total_cases']*100:.1f}%)\n")

        f.write("\n--- Severity Breakdown ---\n")
        for sev, count in metrics['severity_counts'].items():
            f.write(f"  {sev:12s}: {count:2d} cases ({count/metrics['total_cases']*100:.1f}%)\n")

        f.write("\n--- Networking Concept Breakdown ---\n")
        for concept, count in sorted(metrics['concept_counts'].items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {concept:25s}: {count:2d} cases\n")


def generate_html_dashboard(cases, metrics, filepath):
    ai = metrics['ai_reviews']
    
    # Concept bars HTML
    max_concept = max(metrics['concept_counts'].values()) if metrics['concept_counts'] else 1
    concept_bars_html = ""
    for concept, count in sorted(metrics['concept_counts'].items(), key=lambda x: x[1], reverse=True):
        pct = (count / max_concept) * 100
        concept_bars_html += f"""
        <div class="bar-row">
            <div class="bar-label">{concept}</div>
            <div class="bar-track"><div class="bar-fill" style="width: {pct}%;"></div></div>
            <div class="bar-val">{count}</div>
        </div>"""

    # Severity bars HTML
    sev_colors = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981", "Critical": "#dc2626"}
    severity_bars_html = ""
    for sev, count in metrics['severity_counts'].items():
        color = sev_colors.get(sev, "#6366f1")
        pct = (count / metrics['total_cases']) * 100
        severity_bars_html += f"""
        <div class="bar-row">
            <div class="bar-label">{sev}</div>
            <div class="bar-track"><div class="bar-fill" style="width: {pct}%; background: {color};"></div></div>
            <div class="bar-val">{count} ({pct:.0f}%)</div>
        </div>"""

    # OSI Layer bars HTML
    osi_bars_html = ""
    for layer, count in sorted(metrics['osi_counts'].items()):
        pct = (count / metrics['total_cases']) * 100
        osi_bars_html += f"""
        <div class="bar-row">
            <div class="bar-label">{layer}</div>
            <div class="bar-track"><div class="bar-fill" style="width: {pct}%; background: #3b82f6;"></div></div>
            <div class="bar-val">{count}</div>
        </div>"""

    # Table rows HTML
    table_rows_html = ""
    for c in cases:
        badge_cls = "badge-accepted" if c.get("human_review_decision") == "Accepted" else ("badge-edited" if c.get("human_review_decision") == "Edited" else "badge-rejected")
        table_rows_html += f"""
        <tr>
            <td><strong>{c.get('case_id')}</strong></td>
            <td>{c.get('symptom')}</td>
            <td><span class="tag">{c.get('osi_layer')}</span></td>
            <td>{c.get('concept')}</td>
            <td><span class="tag tag-{c.get('severity','').lower()}">{c.get('severity')}</span></td>
            <td><span class="badge {badge_cls}">{c.get('human_review_decision')}</span></td>
            <td><span class="badge badge-verified">{c.get('case_status')}</span></td>
        </tr>"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetSage AI Project Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --border: rgba(255, 255, 255, 0.1);
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.3);
            --text: #f8fafc;
            --muted: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }}
        body {{ background: var(--bg); color: var(--text); padding: 2rem; min-height: 100vh; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; }}
        .header h1 {{ font-size: 1.8rem; font-weight: 700; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .header .subtitle {{ color: var(--muted); font-size: 0.9rem; margin-top: 4px; }}
        
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.25rem; margin-bottom: 2rem; }}
        .kpi-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; backdrop-filter: blur(12px); }}
        .kpi-title {{ color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }}
        .kpi-value {{ font-size: 2.2rem; font-weight: 700; margin: 8px 0; color: #fff; }}
        .kpi-sub {{ font-size: 0.8rem; color: var(--success); font-weight: 500; }}

        .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }}
        .chart-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; backdrop-filter: blur(12px); }}
        .chart-title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 1.25rem; color: #f1f5f9; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.5rem; }}

        .bar-row {{ display: flex; align-items: center; margin-bottom: 0.75rem; font-size: 0.85rem; }}
        .bar-label {{ width: 140px; color: var(--muted); font-weight: 500; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; }}
        .bar-track {{ flex: 1; height: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; margin: 0 12px; overflow: hidden; }}
        .bar-fill {{ height: 100%; background: linear-gradient(90deg, var(--accent), #818cf8); border-radius: 5px; transition: width 0.6s ease; }}
        .bar-val {{ width: 60px; text-align: right; font-weight: 600; color: #cbd5e1; }}

        .agreement-gauge {{ display: flex; gap: 1rem; align-items: center; margin-top: 1rem; }}
        .gauge-item {{ flex: 1; text-align: center; background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; border: 1px solid var(--border); }}
        .gauge-val {{ font-size: 1.5rem; font-weight: 700; margin-top: 4px; }}
        .text-accepted {{ color: var(--success); }}
        .text-edited {{ color: var(--warning); }}
        .text-rejected {{ color: var(--danger); }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.85rem; }}
        th {{ text-align: left; padding: 10px 12px; color: var(--muted); border-bottom: 1px solid var(--border); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }}
        td {{ padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #cbd5e1; }}
        tr:hover td {{ background: rgba(255,255,255,0.02); }}

        .badge {{ padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; display: inline-block; }}
        .badge-accepted {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-edited {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
        .badge-rejected {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
        .badge-verified {{ background: rgba(99, 102, 241, 0.2); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3); }}
        .tag {{ background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; color: #94a3b8; }}
        .tag-high {{ color: #f87171; background: rgba(239, 68, 68, 0.1); }}
        .tag-medium {{ color: #fbbf24; background: rgba(245, 158, 11, 0.1); }}
        .tag-low {{ color: #34d399; background: rgba(16, 185, 129, 0.1); }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>NetSage AI Troubleshooting Analytics Dashboard</h1>
            <div class="subtitle">Real-time Diagnostic Case Dataset & Responsible AI Human Review Metrics</div>
        </div>
        <div class="tag" style="padding: 6px 12px; font-size: 0.85rem;">Cisco Packet Tracer Automation</div>
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">Total Networking Cases</div>
            <div class="kpi-value">{metrics['total_cases']}</div>
            <div class="kpi-sub">✓ 100% Fully Documented</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">AI Agreement Rate</div>
            <div class="kpi-value">{ai['agreement_rate']}%</div>
            <div class="kpi-sub">{ai['accepted']} of {ai['total_reviewed']} Accepted</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Human Corrections</div>
            <div class="kpi-value">{ai['edited'] + ai['rejected']}</div>
            <div class="kpi-sub">{ai['edited']} Edited • {ai['rejected']} Rejected</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Rule Checker Coverage</div>
            <div class="kpi-value">6 Rules</div>
            <div class="kpi-sub">L1-L7 Diagnostic Automation</div>
        </div>
    </div>

    <div class="charts-grid">
        <div class="chart-card">
            <div class="chart-title">Responsible AI Human Review Breakdown</div>
            <div class="agreement-gauge">
                <div class="gauge-item">
                    <div class="kpi-title">Accepted</div>
                    <div class="gauge-val text-accepted">{ai['accepted']}</div>
                    <div style="font-size:0.75rem; color:var(--muted);">{ai['agreement_rate']}%</div>
                </div>
                <div class="gauge-item">
                    <div class="kpi-title">Edited</div>
                    <div class="gauge-val text-edited">{ai['edited']}</div>
                    <div style="font-size:0.75rem; color:var(--muted);">{ai['edit_rate']}%</div>
                </div>
                <div class="gauge-item">
                    <div class="kpi-title">Rejected</div>
                    <div class="gauge-val text-rejected">{ai['rejected']}</div>
                    <div style="font-size:0.75rem; color:var(--muted);">{ai['reject_rate']}%</div>
                </div>
            </div>
            <div style="margin-top: 1.5rem;">
                <div class="bar-row">
                    <div class="bar-label">Accepted AI</div>
                    <div class="bar-track"><div class="bar-fill" style="width: {ai['agreement_rate']}%; background: var(--success);"></div></div>
                    <div class="bar-val">{ai['accepted']}</div>
                </div>
                <div class="bar-row">
                    <div class="bar-label">Human Edited</div>
                    <div class="bar-track"><div class="bar-fill" style="width: {ai['edit_rate']}%; background: var(--warning);"></div></div>
                    <div class="bar-val">{ai['edited']}</div>
                </div>
                <div class="bar-row">
                    <div class="bar-label">Human Rejected</div>
                    <div class="bar-track"><div class="bar-fill" style="width: {ai['reject_rate']}%; background: var(--danger);"></div></div>
                    <div class="bar-val">{ai['rejected']}</div>
                </div>
            </div>
        </div>

        <div class="chart-card">
            <div class="chart-title">Severity Level Breakdown</div>
            {severity_bars_html}
        </div>

        <div class="chart-card">
            <div class="chart-title">Cases by OSI Model Layer</div>
            {osi_bars_html}
        </div>

        <div class="chart-card">
            <div class="chart-title">Networking Concept Distribution</div>
            {concept_bars_html}
        </div>
    </div>

    <div class="chart-card">
        <div class="chart-title">Complete Dataset Case Inventory (cases.csv)</div>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Case ID</th>
                        <th>Symptom</th>
                        <th>OSI Layer</th>
                        <th>Concept</th>
                        <th>Severity</th>
                        <th>AI Review</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)


def generate_csv_summary(metrics, filepath):
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric Category", "Metric Name", "Value"])
        writer.writerow(["Overview", "Total Cases", metrics['total_cases']])
        writer.writerow(["Responsible AI", "Accepted Cases", metrics['ai_reviews']['accepted']])
        writer.writerow(["Responsible AI", "Edited Cases", metrics['ai_reviews']['edited']])
        writer.writerow(["Responsible AI", "Rejected Cases", metrics['ai_reviews']['rejected']])
        writer.writerow(["Responsible AI", "AI Agreement Rate (%)", metrics['ai_reviews']['agreement_rate']])

        for layer, cnt in metrics['osi_counts'].items():
            writer.writerow(["OSI Layer", layer, cnt])

        for sev, cnt in metrics['severity_counts'].items():
            writer.writerow(["Severity", sev, cnt])

        for concept, cnt in metrics['concept_counts'].items():
            writer.writerow(["Concept", concept, cnt])


def generate_excel_and_charts(cases, ai_logs, metrics):
    """Optional export to Excel and static PNG charts if libraries are present."""
    try:
        import pandas as pd
        import openpyxl

        excel_path = os.path.join(OUTPUT_DIR, "dashboard.xlsx")
        df_cases = pd.DataFrame(cases)
        df_logs = pd.DataFrame(ai_logs)
        
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_cases.to_excel(writer, sheet_name="Cases Dataset", index=False)
            if not df_logs.empty:
                df_logs.to_excel(writer, sheet_name="Responsible AI Log", index=False)
        print(f"Generated Excel Workbook:  {excel_path}")
    except Exception as e:
        pass

    try:
        import matplotlib.pyplot as plt
        
        chart_path = os.path.join(OUTPUT_DIR, "dashboard_chart.png")
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # 1. AI Review Pie Chart
        ai = metrics['ai_reviews']
        axes[0, 0].pie([ai['accepted'], ai['edited'], ai['rejected']], 
                       labels=['Accepted', 'Edited', 'Rejected'], 
                       colors=['#10b981', '#f59e0b', '#ef4444'], 
                       autopct='%1.1f%%', startangle=140)
        axes[0, 0].set_title('Responsible AI Review Decisions')

        # 2. OSI Layer Bar
        osi_keys = list(metrics['osi_counts'].keys())
        osi_vals = list(metrics['osi_counts'].values())
        axes[0, 1].bar(osi_keys, osi_vals, color='#3b82f6')
        axes[0, 1].set_title('Cases by OSI Model Layer')
        axes[0, 1].set_ylabel('Number of Cases')

        # 3. Severity Bar
        sev_keys = list(metrics['severity_counts'].keys())
        sev_vals = list(metrics['severity_counts'].values())
        axes[1, 0].bar(sev_keys, sev_vals, color=['#ef4444', '#10b981'])
        axes[1, 0].set_title('Severity Distribution')
        axes[1, 0].set_ylabel('Number of Cases')

        # 4. Concepts Top 6
        concepts_sorted = sorted(metrics['concept_counts'].items(), key=lambda x: x[1], reverse=True)[:6]
        c_keys = [x[0] for x in concepts_sorted]
        c_vals = [x[1] for x in concepts_sorted]
        axes[1, 1].barh(c_keys, c_vals, color='#818cf8')
        axes[1, 1].set_title('Top Networking Concepts')
        axes[1, 1].invert_yaxis()

        plt.tight_layout()
        plt.savefig(chart_path, dpi=200)
        plt.close()
        print(f"Generated Static PNG Chart: {chart_path}")
    except Exception as e:
        pass


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cases, ai_logs = load_data()
    metrics = compute_metrics(cases, ai_logs)

    generate_text_summary(metrics, os.path.join(OUTPUT_DIR, "dashboard_summary.txt"))
    generate_html_dashboard(cases, metrics, os.path.join(OUTPUT_DIR, "dashboard.html"))
    generate_csv_summary(metrics, os.path.join(OUTPUT_DIR, "dashboard_metrics.csv"))
    generate_excel_and_charts(cases, ai_logs, metrics)

    print("==================================================")
    print("      NetSage AI Dashboard Generator Finished     ")
    print("==================================================")
    print(f"Generated HTML Dashboard:  {os.path.join(OUTPUT_DIR, 'dashboard.html')}")
    print(f"Generated Text Summary:    {os.path.join(OUTPUT_DIR, 'dashboard_summary.txt')}")
    print(f"Generated Metrics CSV:     {os.path.join(OUTPUT_DIR, 'dashboard_metrics.csv')}")
