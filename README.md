<div align="center">

# Commit Spoof
### Makes you busy as a bee

</div>

Generate backdated Git commit history locally. Optionally configure SSH and force-push to GitHub.

## Requirements

- Python 3.8+
- Git on `PATH`

## Quick Start

```powershell
py spoof.py \
  --repo-path /home/Entropic-Code/lol \
  --start 1/1/2025 --end 12/21/2025 \
  --probability 50 --max-commits 5 \
  --name "Your Name" \
  --email "you@example.com" \
  --remote git@github.com:OWNER/REPO.git \
  --branch main
```

That generates commits across the date range, resets the repo if it already has history, sets up SSH if needed, and force-pushes.

### Date range

| Flag | Default | Meaning |
| --- | --- | --- |
| `--start M/D/YYYY` | 365 days before `--end` | First day (inclusive) |
| `--end M/D/YYYY` | today | Last day (inclusive) |

```powershell
# All of 2025
py spoof.py --repo-path my-repo --start 1/1/2025 --end 12/31/2025

# From a date through today
py spoof.py --repo-path my-repo --start 1/1/2025

# Last ~year ending today
py spoof.py --repo-path my-repo
```

### Windows paths

`/home/...` and relative paths map to `%USERPROFILE%\spofer\`:

```
/home/Entropic-Code/lol  →  C:\Users\You\spofer\Entropic-Code\lol
```

Omit `--repo-path` to use `%USERPROFILE%\spofer\<repo-name>` derived from `--remote`.

### Push only (no generation)

```powershell
py spoof.py --skip-gen \
  --repo-path my-repo \
  --remote git@github.com:OWNER/REPO.git \
  --branch main \
  --email "you@example.com"
```

## Options

| Option | Default | Description |
| --- | --- | --- |
| `--repo-path PATH` | from `--remote` | Target repo. Created if missing. |
| `--start M/D/YYYY` | 365 days before `--end` | First day to generate commits. |
| `--end M/D/YYYY` | today | Last day to generate commits. |
| `--probability N` | `75` | Daily commit chance (`0`–`100`). |
| `--max-commits N` | `8` | Max commits per active day (`1`–`50`). |
| `--no-weekends` | off | Skip Saturday and Sunday. |
| `--trend N` | `0.0` | Activity drift (`-1.0` to `1.0`). |
| `--remote URL` | none | Set `origin` and force-push. |
| `--branch NAME` | `main` | Branch to init and push. |
| `--name NAME` | `Git User` | Git `user.name`. |
| `--email ADDRESS` | `git@localhost` | Git `user.email` and SSH key comment. |
| `--skip-gen` | off | Push existing history only. Requires `--remote`. |
| `--append` | off | Stack onto existing commits instead of resetting. |
| `--skip-ssh-setup` | off | Skip automatic SSH setup. |

## Behavior

**Auto-reset** — Re-running without `--skip-gen` or `--append` wipes existing commits and regenerates. No manual folder deletion needed.

**Progress** — Prints every 25 commits. A full year can take several minutes.

**SSH** — With an SSH `--remote`, the script creates `~/.ssh/commit-spoof`, writes an SSH config alias, and tests the connection before pushing. It can install `gh` via `winget`/`apt`/`brew` or show the public key to add at [github.com/settings/ssh/new](https://github.com/settings/ssh/new). Reuses the existing key if auth already works.

**Push** — `--remote` always force-pushes. Review local history first.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Seems hung | Normal for hundreds of commits. Wait for progress lines. |
| SSH auth fails | Add the printed public key to GitHub, then `--skip-gen` to push. |
| Want to keep old commits | Pass `--append`. |
| Push rejected | Check URL, branch, and permissions. |

## License

Don't copy our shit without permittion
