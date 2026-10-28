# SERVING — the default working page

**Read this before starting, stopping, or serving anything.** It exists because an
assistant once found port 8021 idle, assumed it was free, and served a *different*
project folder on it — replacing the page the owner was checking. The owner then had
to prove their own work still existed. Do not repeat that.

## The default working page

| | |
|---|---|
| **URL** | http://127.0.0.1:8021/ |
| **Build** | **v0.93** (page shows a `v0.93` pill in the header) |
| **Repository** | `D:\SMART BUSINESSWRITER` |
| **Branch** | **`design/v0.73-rail`** — this is the checked-out default |
| **Layout** | Subjects in the side rail: Home · Accounting · Finance · Economics · Management & strategy · Project management · Entrepreneurship · Operations management · Supply chain & logistics · Marketing & customers · People & organisation · Research & statistics · Calculator |

This page is meant to be **always up**. It is started at logon and supervised, so it
restarts if it crashes. There is no terminal to keep open.

## How it runs

- **Launcher** — `C:\Users\Roderick\.smart-business-writer\serve-8021.ps1`
  Runs `scripts/serve.py --port 8021` from this repo and restarts it 5 seconds after
  any exit. One instance only (named mutex `SBW-Serve-8021`).
- **Autostart** — `SmartBusinessWriter-8021.vbs` in the per-user Startup folder, so it
  needs no administrator rights. (A Scheduled Task was attempted and refused: *Access is
  denied*. The Startup folder is the working equivalent.)
- **Log** — `C:\Users\Roderick\.smart-business-writer\server.log`

To start it by hand:

```powershell
wscript.exe "C:\Users\Roderick\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\SmartBusinessWriter-8021.vbs"
```

To stop it (both the supervisor and the server):

```powershell
Get-Process powershell | Where-Object { $_.CommandLine -like '*serve-8021.ps1*' } | Stop-Process -Force
Get-NetTCPConnection -State Listen -LocalPort 8021 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

## The rule

**Port 8021 belongs to this page. Do not serve a different directory on it.**

If a page has to be served from somewhere else — an older build, a comparison, a
throwaway clone — use a **different port** (8022, 8030, …) and say which one. Never
take 8021 away from the default page, not even briefly "to check something".

## Where the other work lives

Nothing was deleted to create this branch. The earlier subject-first build (0.68) is
still here, on its own branch:

| What | Where |
|---|---|
| 0.68 subject-first build (16 panels, old rail) | branch `opencode/ui-site` @ `f1b6364` — **not pushed to GitHub** |
| Uncommitted 0.68 edits (194/74 in `web/index.html`, `subjects.py`) | `git stash list` → *"0.68 wip before v0.73 branch"* |
| Same files, plain copies | `C:\Users\Roderick\AppData\Local\Temp\opencode\sbw-backup-20261027-212839\` |
| Cline's v0.70–v0.73 line | `main` on GitHub (`7fedc8e`), fetched here as `cli/cline/main` |
| Throwaway clone Cline created | `C:\Users\Roderick\sbw-072` — **do not depend on it**; Cline's own setup command deletes and re-clones it |
