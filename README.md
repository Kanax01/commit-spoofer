<div align="center">

# Commit Spoof
### Makes you busy as a bee

</div>

Generates backdated Git commit history in a local repo. Optionally sets up SSH and force-pushes to a remote.

## Requirements

- Python 3.8+
- Git on `PATH`
- No third-party Python packages

## Quick Start

Generate a year of commits locally:

```bash
py spoof.py --repo-path my-repo --days 365
```

Generate and push to GitHub (SSH setup is handled interactively):

```bash
py spoof.py \
  --repo-path my-repo \
  --remote git@github.com:OWNER/REPO.git \
  --branch main \
  --name "Your Name" \
  --email "you@example.com"
```

Push existing commits without generating more:

```bash
py spoof.py \
  --skip-gen \
  --repo-path my-repo \
  --remote git@github.com:OWNER/REPO.git \
  --branch main \
  --email "you@example.com"
```

On Windows, relative paths and `/home/...` paths are placed under `%USERPROFILE%\spofer\`. For example, `/home/Entropic-Code/lol` becomes `C:\Users\You\spofer\Entropic-Code\lol`. Omit `--repo-path` to default to `%USERPROFILE%\spofer\<repo-name>` derived from `--remote`.

Generation can take several minutes for a full year. Progress is printed every 25 commits.

## Options

| Option | Default | Description |
| --- | --- | --- |
| `--repo-path PATH` | from `--remote` | Target repo. Created and initialized if missing. |
| `--days N` | `365` | Days of history to generate (UTC). |
| `--probability N` | `75` | Chance each day gets commits (`0`–`100`). |
| `--max-commits N` | `8` | Max commits per active day (`1`–`50`). |
| `--no-weekends` | off | Skip Saturday and Sunday. |
| `--trend N` | `0.0` | Activity drift over time (`-1.0` to `1.0`). |
| `--remote URL` | none | Set `origin` and force-push. |
| `--branch NAME` | `main` | Branch to init and push. |
| `--name NAME` | `Git User` | Git `user.name` for the repo. |
| `--email ADDRESS` | `git@localhost` | Git `user.email` and SSH key comment. |
| `--skip-gen` | off | Skip generation; SSH setup + push only. Requires `--remote`. |
| `--skip-ssh-setup` | off | Skip automatic SSH key setup. |

```bash
py spoof.py --help
```

## SSH

When `--remote` is an SSH URL, the script will:

1. Create `~/.ssh/commit-spoof` if needed (reuses existing key if auth works).
2. Write an SSH config entry (e.g. `github.com-commit-spoof`).
3. Offer to install GitHub CLI via `winget` / `apt` / `brew` and upload the key, or show the public key to add manually at [github.com/settings/ssh/new](https://github.com/settings/ssh/new).
4. Test the connection before pushing.

Passphrase is optional — press Enter to skip. Use `--skip-ssh-setup` if you already have SSH configured.

## Starting Fresh

Re-running without `--skip-gen` **appends** more commits. To wipe and regenerate:

```powershell
# Windows
Remove-Item -Recurse -Force "$env:USERPROFILE\spofer\my-repo"
```

```bash
# Linux/macOS
rm -rf ~/spofer/my-repo
```

Review local history before pushing. `--remote` always force-pushes.

## Safety

- Use a disposable repo first.
- `--remote` overwrites remote branch history.
- `git add .` stages everything in the target repo.
- Do not use this to misrepresent real work or activity.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Seems hung during generation | Normal for 1000+ commits. Wait for progress output. |
| SSH auth fails | Add the printed public key to GitHub, then retry with `--skip-gen`. |
| Double commits | Delete the repo folder and regenerate (see above). |
| Push rejected | Check remote URL, branch name, and push permissions. |

## License

No license file included.
