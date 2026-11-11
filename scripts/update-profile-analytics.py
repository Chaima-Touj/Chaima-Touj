#!/usr/bin/env python3
"""Generate self-hosted GitHub profile analytics SVGs."""
import datetime as dt
import html
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
USER = "Chaima-Touj"
COLORS = {
    "JavaScript":"#f1e05a","TypeScript":"#3178c6","Python":"#3572A5","Java":"#b07219",
    "PHP":"#4F5D95","HTML":"#e34c26","CSS":"#563d7c","C":"#555555","C++":"#f34b7d",
    "C#":"#178600","Kotlin":"#A97BFF","Dart":"#00B4AB","Shell":"#89e051",
    "Vue":"#41b883","Jupyter Notebook":"#DA5B0B","Go":"#00ADD8","Rust":"#dea584"
}
HEAT = ["#161b22","#3b1d5b","#6b21a8","#9333ea","#d8b4fe"]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"Chaima-Touj-profile-analytics","Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def svg(title, width, height, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">{body}</svg>'

def get_contributions():
    data = fetch(f"https://github-contributions-api.jogruber.de/v4/{USER}?y=last")
    days = sorted(data.get("contributions", []), key=lambda d:d["date"])
    if not days:
        raise RuntimeError("No contribution data returned")
    total = int(data.get("total", {}).get("lastYear", sum(int(d["count"]) for d in days)))
    active = {dt.date.fromisoformat(d["date"]) for d in days if int(d.get("count",0)) > 0}
    longest = run = 0
    previous = None
    for day in sorted(active):
        run = run + 1 if previous == day - dt.timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    cursor = dt.datetime.now(dt.timezone.utc).date()
    if cursor not in active:
        cursor -= dt.timedelta(days=1)
    current = 0
    while cursor in active:
        current += 1
        cursor -= dt.timedelta(days=1)
    return days, total, current, longest

def write_stats(total, current, longest):
    cards = [
        ("CONTRIBUTIONS · LAST 12 MONTHS", f"{total:,}", "Public GitHub activity"),
        ("CURRENT STREAK", f"{current} day" + ("" if current == 1 else "s"), "Consecutive active days"),
        ("LONGEST STREAK", f"{longest} days", "Best consecutive period"),
    ]
    body = '<defs><linearGradient id="p" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111827"/><stop offset="1" stop-color="#0b1020"/></linearGradient></defs><rect width="1120" height="195" rx="22" fill="url(#p)" stroke="#312e81"/>'
    for i,(label,value,note) in enumerate(cards):
        x=30+i*374
        body += f'<g transform="translate({x},0)" font-family="Arial,sans-serif"><text y="52" fill="#c4b5fd" font-size="14" font-weight="700">{label}</text><text y="116" fill="#f8fafc" font-size="43" font-weight="700">{html.escape(value)}</text><text y="150" fill="#9ca3af" font-size="13">{html.escape(note)}</text></g>'
        if i<2: body += f'<path d="M{x+342} 32v132" stroke="#344054" stroke-width="1.5"/>'
    body += '<text x="1090" y="181" text-anchor="end" fill="#6b7280" font-family="Arial,sans-serif" font-size="10">Updated by GitHub Actions</text>'
    (ASSETS/"github-stats.svg").write_text(svg("GitHub analytics",1120,195,body),encoding="utf-8")

def write_calendar(days):
    first=dt.date.fromisoformat(days[0]["date"])
    sunday=first-dt.timedelta(days=(first.weekday()+1)%7)
    body='<defs><linearGradient id="p" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111827"/><stop offset="1" stop-color="#0b1020"/></linearGradient></defs><rect width="1120" height="220" rx="22" fill="url(#p)" stroke="#312e81"/>'
    body+='<text x="42" y="39" fill="#f8fafc" font-family="Arial,sans-serif" font-size="19" font-weight="700">Contribution activity · last 12 months</text>'
    for i,label in enumerate(["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]):
        body+=f'<text x="42" y="{82+i*15}" fill="#9ca3af" font-family="Arial,sans-serif" font-size="10">{label}</text>'
    for item in days:
        day=dt.date.fromisoformat(item["date"])
        offset=(day-sunday).days
        col,row=offset//7,offset%7
        x,y=86+col*15,70+row*15
        level=max(0,min(4,int(item.get("level",0))))
        count=int(item.get("count",0))
        body+=f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="{HEAT[level]}"><title>{day.isoformat()}: {count} contributions</title></rect>'
        if day.day==1:
            body+=f'<text x="{x}" y="59" fill="#9ca3af" font-family="Arial,sans-serif" font-size="10">{day.strftime("%b")}</text>'
    body+='<g transform="translate(850 192)" font-family="Arial,sans-serif" fill="#9ca3af" font-size="10"><text>Less</text>'
    for i,color in enumerate(HEAT):
        body+=f'<rect x="{32+i*15}" y="-10" width="10" height="10" rx="2" fill="{color}"/>'
    body+='<text x="112" y="0">More</text></g>'
    (ASSETS/"github-contributions.svg").write_text(svg("GitHub contribution calendar",1120,220,body),encoding="utf-8")

def write_languages():
    repos=fetch(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&sort=updated")
    totals={}
    for repo in repos:
        if repo.get("fork"): continue
        try:
            for language,size in fetch(repo["languages_url"]).items():
                totals[language]=totals.get(language,0)+int(size)
        except Exception as exc:
            print(f"Skipping {repo.get('name')}: {exc}")
    ranked=sorted(totals.items(),key=lambda x:x[1],reverse=True)[:8]
    if not ranked: raise RuntimeError("No language breakdown returned")
    denominator=sum(v for _,v in ranked) or 1
    body='<defs><linearGradient id="p" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111827"/><stop offset="1" stop-color="#0b1020"/></linearGradient></defs><rect width="1120" height="360" rx="22" fill="url(#p)" stroke="#312e81"/>'
    body+='<text x="42" y="42" fill="#f8fafc" font-family="Arial,sans-serif" font-size="20" font-weight="700">Most used programming languages</text><text x="1074" y="42" text-anchor="end" fill="#9ca3af" font-family="Arial,sans-serif" font-size="12">Public repository code</text>'
    for i,(name,count) in enumerate(ranked):
        y=86+i*32
        pct=count/denominator*100
        color=COLORS.get(name,"#a78bfa")
        body+=f'<g font-family="Arial,sans-serif"><text x="42" y="{y}" fill="#e5e7eb" font-size="15">{html.escape(name)}</text><rect x="240" y="{y-13}" width="720" height="11" rx="5" fill="#202938"/><rect x="240" y="{y-13}" width="{720*pct/100:.2f}" height="11" rx="5" fill="{color}"/><text x="1074" y="{y}" text-anchor="end" fill="#c4b5fd" font-size="14">{pct:.1f}%</text></g>'
    body+='<text x="42" y="337" fill="#6b7280" font-family="Arial,sans-serif" font-size="11">Calculated from GitHub repository language data · refreshed daily</text>'
    (ASSETS/"github-languages.svg").write_text(svg("Programming language statistics",1120,360,body),encoding="utf-8")

def main():
    ASSETS.mkdir(parents=True,exist_ok=True)
    days,total,current,longest=get_contributions()
    write_stats(total,current,longest)
    write_calendar(days)
    write_languages()
    print(f"Updated analytics: {total} contributions, streak {current}/{longest} days.")
if __name__=="__main__":
    main()
