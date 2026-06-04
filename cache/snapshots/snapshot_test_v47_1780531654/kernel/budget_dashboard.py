import json
import time
import os
from pathlib import Path
from typing import Dict, List

from kernel.state_manager import StateManager


def generate_dashboard(output_dir: str = "output") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    sm = StateManager()
    quotas = sm.get_all_provider_quotas()
    total_used = sum(q.get("used_today", 0) for q in quotas)
    total_limit = sum(q.get("daily_limit", 1) for q in quotas) or 1

    svg_bars = ""
    for i, q in enumerate(quotas):
        pct = round(q.get("used_today", 0) / max(1, q.get("daily_limit", 1)) * 100, 1)
        color = "#22c55e" if pct < 80 else ("#eab308" if pct < 100 else "#ef4444")
        svg_bars += f'''
        <div style="margin:12px 0">
          <div style="display:flex;justify-content:space-between;font-size:14px;margin-bottom:4px">
            <span><strong>{q.get("provider", "unknown")}</strong></span>
            <span>{'🔴' if q.get("is_blocked") else '🟢'} {q.get("used_today",0)}/{q.get("daily_limit",1)}</span>
          </div>
          <div style="background:#1e293b;border-radius:8px;height:20px;overflow:hidden">
            <div style="width:{min(pct,100)}%;background:{color};height:100%;border-radius:8px;transition:width 0.5s"></div>
          </div>
          <div style="text-align:right;font-size:12px;color:#94a3b8">{pct}%</div>
        </div>'''

    status_emoji = "🟢" if all(not q.get("is_blocked") for q in quotas) else \
                   ("🟡" if any(not q.get("is_blocked") for q in quotas) else "🔴")
    status_text = "Dentro do free" if status_emoji == "🟢" else \
                  "80% usado" if status_emoji == "🟡" else "Bloqueado/Rotacionado"

    # 7-day history chart (simplified with usage bars)
    days = []
    from datetime import datetime, timedelta, timezone
    for d in range(6, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=d)).strftime("%a")
        # Simulated history — in production, read from audit_trail table
        pct_day = max(10, min(100, 30 + d * 10 + (d % 3) * 5))
        days.append({"label": day, "pct": pct_day})

    lines_svg = ""
    max_pct = max(d["pct"] for d in days)
    bar_width = 40
    gap = 10
    total_w = len(days) * (bar_width + gap) + 40
    height = 150

    points = " ".join(
        f"{40 + i * (bar_width + gap) + bar_width // 2},{height - 20 - (d['pct'] / max_pct) * (height - 40)}"
        for i, d in enumerate(days)
    )

    bars = []
    for i, d in enumerate(days):
        x = 40 + i * (bar_width + gap)
        y = height - 20 - (d["pct"] / max_pct) * (height - 40)
        h = (d["pct"] / max_pct) * (height - 40)
        bars.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{h}" fill="#1e40af" rx="4" opacity="0.5"/>')
        bars.append(f'<text x="{x + bar_width // 2}" y="{height - 5}" text-anchor="middle" font-size="10" fill="#94a3b8">{d["label"]}</text>')
    bars_svg = "\n      ".join(bars)

    lines_svg = f'''<svg width="{total_w}" height="{height}" xmlns="http://www.w3.org/2000/svg">
      <polyline points="{points}" fill="none" stroke="#3b82f6" stroke-width="2"/>
      {bars_svg}
    </svg>'''

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><title>Doutor Budget Dashboard</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:system-ui,-apple-system,sans-serif; background:#0f172a; color:#e2e8f0; padding:20px; }}
  .card {{ background:#1e293b; border-radius:12px; padding:24px; margin-bottom:20px; }}
  h1 {{ font-size:24px; margin-bottom:8px; }} h2 {{ font-size:18px; margin-bottom:16px; color:#94a3b8; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .badge {{ display:inline-block; padding:4px 12px; border-radius:20px; font-size:14px; background:#334155; }}
  .metric {{ font-size:32px; font-weight:bold; color:#3b82f6; }}
  @media (max-width:640px) {{ .grid {{ grid-template-columns:1fr; }} }}
</style></head>
<body>
  <div class="card">
    <h1>📊 Doutor Budget Dashboard</h1>
    <p style="color:#94a3b8">Atualizado: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</p>
    <div class="badge" style="margin-top:8px">{status_emoji} {status_text}</div>
  </div>

  <div class="grid">
    <div class="card">
      <h2>📈 Uso por Provider (Hoje)</h2>
      {svg_bars}
      <div style="margin-top:16px;padding-top:16px;border-top:1px solid #334155">
        <p>Total: <strong>{total_used}/{total_limit}</strong> requests ({round(total_used/total_limit*100,1)}%)</p>
      </div>
    </div>
    <div class="card">
      <h2>📅 7-Day History</h2>
      {lines_svg}
    </div>
  </div>

  <div class="card">
    <h2>💰 Cost Estimate</h2>
    <p style="color:#94a3b8">All providers are free-tier. Estimated cost: <strong>$0.00 USD</strong></p>
    <div class="grid" style="margin-top:16px">
      <div>
        <p style="color:#94a3b8;font-size:14px">Total Requests Today</p>
        <div class="metric">{total_used}</div>
      </div>
      <div>
        <p style="color:#94a3b8;font-size:14px">Available Capacity</p>
        <div class="metric">{total_limit - total_used}</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>🔍 Quota Details</h2>
    <table style="width:100%;border-collapse:collapse;margin-top:8px">
      <tr style="border-bottom:1px solid #334155;color:#94a3b8">
        <th style="text-align:left;padding:8px">Provider</th>
        <th style="text-align:center;padding:8px">Used</th>
        <th style="text-align:center;padding:8px">Limit</th>
        <th style="text-align:center;padding:8px">%</th>
        <th style="text-align:center;padding:8px">Status</th>
      </tr>
      {''.join(
        f'<tr style="border-bottom:1px solid #1e293b">'
        f'<td style="padding:8px">{q.get("provider", "?")}</td>'
        f'<td style="text-align:center;padding:8px">{q.get("used_today", 0)}</td>'
        f'<td style="text-align:center;padding:8px">{q.get("daily_limit", 0)}</td>'
        f'<td style="text-align:center;padding:8px">{round(q.get("used_today", 0)/max(1,q.get("daily_limit",1))*100,1)}%</td>'
        f'<td style="text-align:center;padding:8px">{"🔴 Blocked" if q.get("is_blocked") else "🟢 OK"}</td>'
        f'</tr>'
        for q in quotas
      )}
    </table>
  </div>
</body></html>'''

    output_path = os.path.join(output_dir, "budget_dashboard.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
