#!/usr/bin/env python3
"""
BOSS Zhipin Auto-Communicate
=============================

Search for remote/part-time tech jobs on BOSS直聘, auto-send "立即沟通",
then click "留在此页" to continue.

Usage:
    python3 run.py --ip 192.168.50.229 --keywords "remote dev,remote Java"
    python3 run.py --help

Prerequisites:
    - cdp-agent middleware running on Windows (cdp_agent_win.py)
    - Chrome logged in to BOSS直聘 (zhipin.com)

Requires:
    pip install websockets
"""

import sys
import os
import json
import time
import asyncio
import argparse
from urllib.parse import quote

# Locate cdp_agent_client.py in sibling skill directory
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
for p in [
    os.path.normpath(os.path.join(SKILL_DIR, '..', '..', 'cdp-agent')),
    os.path.join(os.path.dirname(SKILL_DIR), 'cdp-agent'),
]:
    if os.path.exists(os.path.join(p, 'cdp_agent_client.py')):
        sys.path.insert(0, p)
        break

from cdp_agent_client import CDPClient


# ====== Defaults ======
DEFAULT_IP = "192.168.50.229"
DEFAULT_KEYWORDS = [
    "remote dev", "remote Java", "remote frontend", "remote fullstack",
    "remote Python", "remote Go", "remote backend",
]
DEFAULT_TECH_TAGS = [
    "Java", "frontend", "backend", "fullstack", "Python", "Vue", "React", "Node",
    "dev", "software", "engineer", "architect", "algorithm", "AI", "data",
    "ops", "test", "blockchain", "Web3", "API", "Go", "PHP", ".NET", "C++", "IT",
]
DEFAULT_REMOTE_TAGS = ["remote", "part-time", "freelance", "contract"]
DEFAULT_MAX = 500


def parse_args():
    parser = argparse.ArgumentParser(description="BOSS Zhipin Auto-Communicate")
    parser.add_argument("--ip", default=DEFAULT_IP, help=f"Windows CDP agent IP (default: {DEFAULT_IP})")
    parser.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS),
                        help="Comma-separated search keywords")
    parser.add_argument("--tech-tags", default=",".join(DEFAULT_TECH_TAGS),
                        help="Comma-separated tech stack keywords for title matching")
    parser.add_argument("--remote-tags", default=",".join(DEFAULT_REMOTE_TAGS),
                        help="Comma-separated remote/part-time keywords")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX,
                        help=f"Max communications per run (default: {DEFAULT_MAX})")
    parser.add_argument("--city", default="100010000",
                        help="City code (100010000=nationwide, default: 100010000)")
    return parser.parse_args()


async def communicate_for_keyword(b, kw, tech_tags, remote_tags, city_code, max_count):
    """Search one keyword, find matching jobs, send chat requests."""
    url = f"https://www.zhipin.com/web/geek/jobs?query={quote(kw)}&city={city_code}"
    
    await b.navigate(url)
    time.sleep(5)
    
    tech_cond = " || ".join([f'title.includes("{t}")' for t in tech_tags])
    remote_cond = " || ".join([f'title.includes("{r}") || cardText.includes("{r}")' for r in remote_tags])
    
    sent = 0
    page = 1
    no_more = 0
    
    while sent < max_count:
        r = await b.eval(f"""
            (() => {{
                const links = document.querySelectorAll('a.job-name, a[class*="job-name"]');
                for (const a of links) {{
                    if (a.dataset._cdp_seen) continue;
                    const card = a.closest('.job-primary, [class*="card"], li');
                    const cardText = card ? card.innerText : '';
                    const title = a.innerText || '';
                    const isRemote = {remote_cond};
                    if (!isRemote) continue;
                    const isTech = {tech_cond};
                    if (!isTech) continue;
                    a.dataset._cdp_seen = '1';
                    a.click();
                    return JSON.stringify({{found: true, title: title.substring(0, 60)}});
                }}
                return JSON.stringify({{found: false}});
            }})()
        """)
        r = json.loads(r)
        
        if not r.get('found'):
            sh_before = await b.eval("document.documentElement.scrollHeight")
            await b.eval("window.scrollTo(0, document.documentElement.scrollHeight)")
            time.sleep(2)
            sh_after = await b.eval("document.documentElement.scrollHeight")
            if sh_after > sh_before:
                continue
            
            np = await b.eval("document.querySelector('a.next, a[class*=next]')?.click()")
            if np:
                page += 1
                time.sleep(4)
                continue
            
            no_more += 1
            if no_more >= 3:
                break
            time.sleep(2)
            continue
        
        no_more = 0
        time.sleep(2)
        
        has_chat = await b.eval("!!document.querySelector('a.op-btn-chat:not(.is-disabled)')")
        
        if has_chat:
            await b.eval("document.querySelector('a.op-btn-chat:not(.is-disabled)')?.click()")
            time.sleep(1.5)
            await b.eval("""
                for (const el of document.querySelectorAll('a')) {
                    if ((el.innerText || '').trim() === '留在此页') { el.click(); break; }
                }
            """)
            time.sleep(1)
            sent += 1
            if sent % 10 == 0:
                print(f"  [{sent}] {r.get('title','')[:40]}")
        else:
            time.sleep(0.5)
    
    return sent, page


async def main():
    args = parse_args()
    
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    tech_tags = [t.strip() for t in args.tech_tags.split(",") if t.strip()]
    remote_tags = [r.strip() for r in args.remote_tags.split(",") if r.strip()]
    
    print(f"CDP Agent IP: {args.ip}")
    print(f"Keywords ({len(keywords)}): {', '.join(keywords[:5])}...")
    print(f"Tech tags ({len(tech_tags)})")
    print(f"Max per run: {args.max}")
    print()
    
    b = CDPClient(f"ws://{args.ip}:19400")
    
    ok = await b.ping()
    if not ok:
        print("Error: Cannot connect to CDP Agent. Is it running on Windows?")
        sys.exit(1)
    print("Connected to CDP Agent\n")
    
    total = 0
    for kw in keywords:
        if total >= args.max:
            break
        
        print(f"=== {kw} ===")
        sent, pages = await communicate_for_keyword(
            b, kw, tech_tags, remote_tags, args.city, args.max - total
        )
        total += sent
        print(f"  [{kw}] done: {sent} (page {pages})\n")
    
    print(f"Total: {total} communications sent")
    await b.close()


if __name__ == "__main__":
    asyncio.run(main())
