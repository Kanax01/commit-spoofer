<div align="center">

# Commit Spoof
### Makes you busy as a bee

</div>

## Requirements

- Python 3.8 or newer
- Git installed and available on `PATH`
- A writable target directory
- Remote push permission when using `--remote`

No third-party Python packages are required.

## Files

- `spoof.py`: command-line generator
- `example.txt`: example command lines
- `sshkey`, `sshkey.pub`: SSH key files present in this workspace; do not publish, reuse, or share private key material

## Quick Start

From this directory, run the generator against a private repo (you may need to set up the github ssh key, see below for that):

```bash
python3 spoof.py --repo-path /path/to/test-repository
```

The default run considers 365 days, uses a 75% chance of committing on each day, and creates up to 8 commits on an active day. It writes generated files such as `core.py`, `utils.py`, and `models.py` into the target repository.

To preview the local result without pushing:

```bash
git -C /path/to/test-repository log --date=iso --pretty=fuller
git -C /path/to/test-repository status
```

## Command-Line Options

| Option | Default | Description |
| --- | --- | --- |
| `--repo-path PATH` | required | Target repository path. Missing directories are created and initialized as Git repositories. |
| `--days N` | `365` | Number of days to generate, counting backward from the current UTC time. |
| `--probability N` | `75` | Percentage chance that each eligible day receives commits. Must be `0`-`100`. |
| `--max-commits N` | `8` | Maximum commits on an active day. The generator chooses a random number from `1` through `N`. Must be `1`-`50`. |
| `--no-weekends` | off | Skips Saturday and Sunday. |
| `--trend N` | `0.0` | Changes activity over time. Use a value from `-1.0` to `1.0`; positive values increase activity and negative values decrease it. |
| `--remote URL` | none | Sets `origin` to this URL and pushes the selected branch. This performs a force push. |
| `--branch NAME` | `main` | Branch initialized and pushed by the script. |
| `--name NAME` | `Git User` | Git `user.name` configured in the target repository. |
| `--email ADDRESS` | `git@localhost` | Git `user.email` configured in the target repository. |

View the built-in help at any time:

```bash
python3 spoof.py --help
```

## SSH Setup for Remote Pushes

SSH is only needed when `--remote` uses an SSH URL such as `git@github.com:OWNER/REPOSITORY.git`. The script delegates authentication to Git and your local SSH configuration; it does not read `sshkey` or `sshkey.pub` directly.

### 1. Create a dedicated key

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -C "you@example.com" -f ~/.ssh/commit-spoof
chmod 600 ~/.ssh/commit-spoof
chmod 644 ~/.ssh/commit-spoof.pub
```

Choose a passphrase when prompted. The command creates a private key at `~/.ssh/commit-spoof` and a public key at `~/.ssh/commit-spoof.pub`.

### 2. Add the public key to your Git host

Display the public key and copy the complete single line:

```bash
cat ~/.ssh/commit-spoof.pub
```

Add it to the SSH keys section of your Git hosting account. Upload only the `.pub` file contents. Never upload or paste the private key.

### 3. Configure and test the key

Start an agent, add the private key, and tell SSH to use it for GitHub:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/commit-spoof
cat >> ~/.ssh/config <<'EOF'
Host github.com-commit-spoof
  HostName github.com
  User git
  IdentityFile ~/.ssh/commit-spoof
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
ssh -T git@github.com-commit-spoof
```

For hosts other than GitHub, replace the `HostName` and test hostname as appropriate. The first connection may ask you to confirm the host fingerprint; verify it against your provider's official documentation before accepting it.

Use the configured host alias in the remote URL:

```bash
git@github.com-commit-spoof:OWNER/REPOSITORY.git
```

Then pass that URL to the script:

```bash
python3 spoof.py \
  --repo-path ~/my-test-repo \
  --remote git@github.com-commit-spoof:OWNER/REPOSITORY.git \
  --branch main
```

Test SSH and repository access separately before running the generator:

```bash
ssh -T git@github.com-commit-spoof
git ls-remote git@github.com-commit-spoof:OWNER/REPOSITORY.git
```

Do not use `--remote` until you have reviewed the local history. It force-pushes the selected branch.

## Examples

Generate local synthetic activity for one year:

```bash
python3 spoof.py \
  --repo-path ~/my-test-repo \
  --days 365 \
  --probability 75 \
  --max-commits 8
```

Skip weekends and apply an increasing activity trend:

```bash
python3 spoof.py \
  --repo-path ~/my-test-repo \
  --days 500 \
  --probability 60 \
  --max-commits 10 \
  --no-weekends \
  --trend 0.8
```

Configure a custom identity without pushing:

```bash
python3 spoof.py \
  --repo-path ~/my-test-repo \
  --name "Your Name" \
  --email "you@example.com"
```

Push to an authorized remote only after inspecting the local history:

```bash
python3 spoof.py \
  --repo-path ~/my-test-repo \
  --remote git@github.com:OWNER/REPOSITORY.git \
  --branch main \
  --name "Your Name" \
  --email "you@example.com"
```

## How It Works

1. Resolves `--repo-path` to an absolute path.
2. Initializes the directory with `git init -b BRANCH` if it does not already contain `.git`.
3. Sets `user.name` and `user.email` in the target repository.
4. Chooses dates from the last `--days` days using UTC timestamps.
5. Decides randomly which days receive commits, reducing weekend activity when `--no-weekends` is enabled.
6. Creates one to three generated placeholder files per commit and appends a random number to each.
7. Runs `git add .` and commits with a random message and the selected commit date.
8. When `--remote` is supplied, replaces `origin` and runs `git push -u origin BRANCH --force`.

The script does not create realistic changes to an existing codebase, preserve a meaningful project history, or provide deterministic output through a seed option.

## Safety Notes

- Test with a disposable repository first.
- Make a backup before running against an existing repository.
- Omit `--remote` until the generated history has been reviewed.
- `--remote` replaces the existing `origin` URL and force-pushes the selected branch; this can overwrite remote history.
- The script stages all files with `git add .`, including unrelated untracked or modified files in the target repository.
- The configured identity changes repository-local Git configuration.
- Do not commit or upload `sshkey`; treat it as private key material. Generate a new key if access is needed and protect it with appropriate permissions.
- Never use generated history to misrepresent authorship, work performed, dates, security activity, or project progress.

## Troubleshooting

### Git commit fails

Check that Git is installed and that the target directory is writable. If the repository has no files staged after generation, inspect the command output and repository status.

### Push fails

Confirm the remote URL, branch name, authentication method, and permission to push. If the remote rejects a force push, do not bypass the protection without authorization.

### No commits are created

A low `--probability`, `--days 0`, or `--no-weekends` over a short weekend-only period can result in no generated commits. Increase the period or probability and try again in a disposable repository.

## License

No license file is included in this repository. Treat the project as unlicensed unless the owner provides separate terms.
