---
name: boss-zhipin
description: BOSS直聘 automation — search remote/part-time tech jobs, auto-send "立即沟通" (chat request). Requires cdp-agent skill.
version: 2.1.0
---

# BOSS直聘 Auto-Communicate

Automatically find remote/part-time tech jobs on BOSS直聘 and send chat requests.

## Prerequisites

- cdp-agent middleware running on Windows (`cdp_agent_win.py`)
- Chrome logged in to BOSS直聘 (zhipin.com)

## Usage

```bash
python3 {baseDir}/scripts/run.py --ip 192.168.50.229 --keywords "remote dev,remote Java,remote frontend"
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--ip` | 192.168.50.229 | Windows CDP Agent IP address |
| `--keywords` | remote dev,remote Java,... | Search keywords, comma separated |
| `--tech-tags` | Java,frontend,backend,... | Tech stack for title matching |
| `--remote-tags` | remote,part-time,freelance | Remote/part-time keywords |
| `--max` | 500 | Max communications per run |
| `--city` | 100010000 | City code (100010000=nationwide) |

## Critical Flow (tested, do not change)

1. **Search** → `https://www.zhipin.com/web/geek/jobs?query={kw}&city=100010000` (wait 5s)
2. **Find jobs** → query `a.job-name` or `a[class*="job-name"]` links in the left sidebar
3. **Filter** → job title OR card text must contain a remote keyword AND a tech tag
4. **Skip** → jobs already marked with `dataset._cdp_seen`
5. **View detail** → click the job-name link (NOT `a.boss-info` company links), wait 2s
6. **Check chat button** → look for `a.op-btn-chat:not(.is-disabled)` in the detail panel
7. **Communicate** → click the chat button, wait 1.5s
8. **Stay on page** → find `<a>` with exact text "留在此页" and click it (do NOT click "继续沟通")
9. **Loop** → continue scanning the same page for more jobs
10. **Scroll** → when no more unprocessed jobs visible, scroll to bottom for lazy-loaded jobs
11. **Paginate** → when scrolling stops growing page height, click `a.next` or `a[class*=next]`
12. **Stop** → when no "next" link exists for 3 consecutive attempts

## Known Pitfalls

- **"立即沟通" click opens a dialog with TWO buttons**: "留在此页" (stay) and "继续沟通" (enter chat). ONLY click "留在此页". Clicking "继续沟通" enters the chat page and breaks the flow.
- **Do NOT click company links** (`a.boss-info`). Only click `a.job-name` (job title). Clicking wrong links may trigger resume-related pages.
- **Do NOT scroll/refresh the page** after clicking "留在此页". The dialog closes and the page stays in place — the next job is right there.
- **Mark jobs as processed** with `dataset._cdp_seen = '1'` to prevent re-processing the same job.
- **Some "立即沟通" buttons are `.is-disabled`** (expired job or already communicated). Skip those.
- **Lazy-loaded jobs**: scroll to bottom to trigger loading. May need 5-8 scrolls on first load.
- **BOSS直聘 auto-locates to your city** by default. Use `--city 100010000` for nationwide search.

## Custom Tech Stack

For someone with broad skills (Java, Python, Vue, React, AI, blockchain, etc.), use:

```bash
python3 {baseDir}/scripts/run.py \
  --ip 192.168.50.229 \
  --keywords "remote Java,remote fullstack,remote Go,remote Python" \
  --tech-tags "Java,Python,Vue,React,Go,AI,blockchain" \
  --max 200
```

## Notes

- The script connects to the Windows CDP Agent. Make sure it's running.
- Requires Chrome to be logged in to BOSS直聘. Login session is preserved via `--user-data-dir`.
- Designed for Chinese job market (BOSS直聘). Keywords are typically Chinese: "远程 开发", "兼职 开发", etc.
