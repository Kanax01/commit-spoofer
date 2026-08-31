#!/usr/bin/env python3
import argparse
import getpass
import os
import platform
import random
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from subprocess import Popen, PIPE
from urllib.parse import urlparse

def run_cmd(cmd, cwd=None, check=True, capture=True, env=None):
    proc = Popen(cmd, shell=False, cwd=cwd, stdout=PIPE, stderr=PIPE, env=env)
    out, err = proc.communicate()
    if check and proc.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{err.decode()}")
    return out.decode().strip() if capture else None

def run_cmd_result(cmd, cwd=None):
    try:
        proc = Popen(cmd, shell=False, cwd=cwd, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        return proc.returncode, out.decode(), err.decode()
    except FileNotFoundError:
        return 127, '', f'Command not found: {cmd[0]}'

def run_cmd_interactive(cmd, cwd=None):
    try:
        return Popen(cmd, shell=False, cwd=cwd).wait()
    except FileNotFoundError:
        return 127

def prompt_input(message, default=None):
    if default:
        response = input(f"{message} [{default}]: ").strip()
        return response or default
    return input(f"{message}: ").strip()

def prompt_yes_no(message, default=True):
    suffix = "Y/n" if default else "y/N"
    response = input(f"{message} [{suffix}]: ").strip().lower()
    if not response:
        return default
    return response in ('y', 'yes')

def is_ssh_remote(url):
    return url.startswith('git@') or url.startswith('ssh://')

def parse_ssh_remote(url):
    if url.startswith('git@'):
        match = re.match(r'git@([^:]+):(.+)', url)
        if match:
            return match.group(1), match.group(2)
    if url.startswith('ssh://'):
        parsed = urlparse(url)
        if parsed.hostname:
            return parsed.hostname, parsed.path.lstrip('/')
    return None, None

def ssh_dir():
    return os.path.join(os.path.expanduser('~'), '.ssh')

def default_key_name():
    return 'commit-spoof'

def windows_spofer_base():
    return os.path.join(os.path.expanduser('~'), 'spofer')

def repo_name_from_remote(remote):
    if not remote:
        return 'repo'
    if remote.startswith('git@') and ':' in remote:
        repo = remote.rsplit(':', 1)[1]
    else:
        repo = remote.rstrip('/').split('/')[-1]
    if repo.endswith('.git'):
        repo = repo[:-4]
    return repo or 'repo'

def resolve_repo_path(path, remote=None):
    if not path:
        path = repo_name_from_remote(remote)

    if platform.system() == 'Windows':
        normalized = path.replace('\\', '/')
        if re.match(r'^[A-Za-z]:', path):
            return os.path.abspath(path)
        if normalized.startswith('/home/'):
            relative = normalized[len('/home/'):]
        elif normalized.startswith('/'):
            relative = normalized.lstrip('/')
        else:
            relative = normalized.lstrip('/')
        resolved = os.path.join(windows_spofer_base(), *relative.split('/'))
        return os.path.abspath(resolved)

    return os.path.abspath(os.path.expanduser(path))

def host_alias_for(hostname, key_name):
    return f'{hostname}-{key_name}'

def rewrite_ssh_remote(url, host_alias):
    hostname, repo_path = parse_ssh_remote(url)
    if not hostname or not repo_path:
        return url
    return f'git@{host_alias}:{repo_path}'

def set_private_key_permissions(key_path):
    if platform.system() == 'Windows':
        return
    os.chmod(key_path, 0o600)
    pub_path = f'{key_path}.pub'
    if os.path.exists(pub_path):
        os.chmod(pub_path, 0o644)

def ensure_ssh_directory():
    directory = ssh_dir()
    os.makedirs(directory, exist_ok=True)
    if platform.system() != 'Windows':
        os.chmod(directory, 0o700)
    return directory

def read_file(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(content)

def upsert_ssh_config(host_alias, hostname, identity_file):
    config_path = os.path.join(ssh_dir(), 'config')
    identity_file = identity_file.replace('\\', '/')
    block = (
        f'Host {host_alias}\n'
        f'  HostName {hostname}\n'
        f'  User git\n'
        f'  IdentityFile {identity_file}\n'
        f'  IdentitiesOnly yes\n'
    )
    if os.path.exists(config_path):
        content = read_file(config_path)
        pattern = re.compile(
            rf'^Host\s+{re.escape(host_alias)}\s*$.*?(?=^Host\s|\Z)',
            re.MULTILINE | re.DOTALL
        )
        if pattern.search(content):
            content = pattern.sub(lambda _: block + '\n', content)
        else:
            if content and not content.endswith('\n'):
                content += '\n'
            content += '\n' + block
        write_file(config_path, content)
    else:
        write_file(config_path, block)
    if platform.system() != 'Windows':
        os.chmod(config_path, 0o600)

def ssh_connection_works(host_alias):
    returncode, out, err = run_cmd_result([
        'ssh', '-T',
        '-o', 'BatchMode=yes',
        '-o', 'StrictHostKeyChecking=accept-new',
        f'git@{host_alias}'
    ])
    combined = f'{out}{err}'.lower()
    if 'successfully authenticated' in combined:
        return True
    return returncode == 0

def locate_gh():
    gh = shutil.which('gh')
    if gh:
        return gh
    if platform.system() == 'Windows':
        for candidate in (
            os.path.join(os.environ.get('ProgramFiles', ''), 'GitHub CLI', 'gh.exe'),
            os.path.join(os.environ.get('LocalAppData', ''), 'Programs', 'GitHub CLI', 'gh.exe'),
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
    return None

def gh_install_command():
    system = platform.system()
    if system == 'Windows':
        if shutil.which('winget'):
            return 'winget', [
                'winget', 'install', '--id', 'GitHub.cli', '-e',
                '--accept-source-agreements', '--accept-package-agreements',
            ]
        if shutil.which('choco'):
            return 'Chocolatey', ['choco', 'install', 'gh', '-y']
    if system == 'Darwin' and shutil.which('brew'):
        return 'Homebrew', ['brew', 'install', 'gh']
    if shutil.which('apt-get'):
        return 'apt', ['sudo', 'apt-get', 'install', '-y', 'gh']
    if shutil.which('dnf'):
        return 'dnf', ['sudo', 'dnf', 'install', '-y', 'gh']
    if shutil.which('pacman'):
        return 'pacman', ['sudo', 'pacman', '-S', '--noconfirm', 'github-cli']
    if shutil.which('apk'):
        return 'apk', ['sudo', 'apk', 'add', 'github-cli']
    return None

def ensure_gh():
    gh = locate_gh()
    if gh:
        return gh
    if not sys.stdin.isatty():
        return None

    install_plan = gh_install_command()
    if not install_plan:
        print(
            'GitHub CLI (gh) is not installed and no supported package manager was found '
            '(winget, apt, dnf, pacman, apk, brew).'
        )
        return None

    manager, cmd = install_plan
    if not prompt_yes_no(f'GitHub CLI (gh) is not installed. Install it with {manager}', default=True):
        return None

    print(f'Installing GitHub CLI with {manager}...', flush=True)
    if run_cmd_interactive(cmd) != 0:
        print(f'Failed to install GitHub CLI with {manager}.')
        return None

    gh = locate_gh()
    if not gh:
        print('GitHub CLI was installed but is not on PATH yet. Open a new terminal and retry.')
        return None

    print('GitHub CLI installed successfully.', flush=True)
    return gh

def ensure_gh_authenticated(gh):
    returncode, _, _ = run_cmd_result([gh, 'auth', 'status'])
    if returncode == 0:
        return True
    if not sys.stdin.isatty():
        return False

    print('GitHub CLI is installed but not signed in.')
    if not prompt_yes_no('Sign in to GitHub now with gh auth login', default=True):
        return False

    if run_cmd_interactive([gh, 'auth', 'login']) != 0:
        print('GitHub sign-in failed or was cancelled.')
        return False

    returncode, _, _ = run_cmd_result([gh, 'auth', 'status'])
    return returncode == 0

def try_add_key_with_gh(pub_key_path, title):
    gh = ensure_gh()
    if not gh:
        return False
    if not ensure_gh_authenticated(gh):
        return False
    returncode, _, err = run_cmd_result([
        gh, 'ssh-key', 'add', pub_key_path, '--title', title
    ])
    if returncode != 0:
        print(f'Could not add SSH key with gh: {err.strip()}')
        return False
    print('SSH public key added to your GitHub account with gh.')
    return True

def host_key_upload_instructions(hostname):
    hosts = {
        'github.com': 'https://github.com/settings/ssh/new',
        'gitlab.com': 'https://gitlab.com/-/user_settings/ssh_keys',
        'bitbucket.org': 'https://bitbucket.org/account/settings/ssh-keys/',
    }
    url = hosts.get(hostname, f'your {hostname} account SSH key settings')
    return (
        f'Add the public key above to {url}.\n'
        'Upload only the .pub file contents. Never share the private key.'
    )

def generate_ssh_key(key_path, email, passphrase):
    cmd = [
        'ssh-keygen', '-t', 'ed25519',
        '-C', email,
        '-f', key_path,
        '-N', passphrase
    ]
    run_cmd(cmd, capture=False)
    set_private_key_permissions(key_path)

def start_ssh_agent_and_add(key_path):
    if platform.system() == 'Windows':
        return
    run_cmd_result(['ssh-add', key_path])

def ensure_ssh_setup(remote_url, email):
    if not sys.stdin.isatty():
        sys.exit(
            'SSH setup requires an interactive terminal. '
            'Configure SSH manually or run without --remote.'
        )

    hostname, _ = parse_ssh_remote(remote_url)
    if not hostname:
        sys.exit(f'Could not parse SSH remote URL: {remote_url}')

    key_name = default_key_name()
    key_path = os.path.join(ssh_dir(), key_name)
    pub_key_path = f'{key_path}.pub'
    alias = host_alias_for(hostname, key_name)
    configured_remote = rewrite_ssh_remote(remote_url, alias)

    ensure_ssh_directory()
    upsert_ssh_config(alias, hostname, key_path)

    if os.path.exists(key_path):
        if ssh_connection_works(alias):
            print(f'Using existing SSH key at {key_path}')
            return configured_remote
        if not prompt_yes_no(
            f'An SSH key already exists at {key_path} but authentication failed. '
            'Continue setup with this key',
            default=True
        ):
            sys.exit('SSH setup cancelled.')
        if os.path.exists(pub_key_path):
            print('\nExisting public key:\n')
            print(read_file(pub_key_path).strip())
            print()
            print(host_key_upload_instructions(hostname))
            print()
            input('Press Enter after verifying the public key is on your Git host...')

    if not os.path.exists(key_path):
        print('\nSSH key setup is required for the remote URL.')
        if email == 'git@localhost':
            key_email = prompt_input('Email for SSH key comment')
        else:
            key_email = email
            print(f'Using {key_email} for SSH key comment.')
        use_passphrase = prompt_yes_no('Protect the SSH key with a passphrase', default=False)
        passphrase = getpass.getpass('SSH key passphrase: ') if use_passphrase else ''
        if use_passphrase and not passphrase:
            sys.exit('Passphrase cannot be empty when passphrase protection is enabled.')

        print(f'\nGenerating SSH key at {key_path} ...')
        generate_ssh_key(key_path, key_email, passphrase)
        if passphrase:
            start_ssh_agent_and_add(key_path)

        public_key = read_file(pub_key_path).strip()
        print('\nPublic key (add this to your Git host):\n')
        print(public_key)
        print()

        added_with_gh = False
        if hostname == 'github.com':
            added_with_gh = try_add_key_with_gh(pub_key_path, f'commit-spoof ({key_email})')

        if not added_with_gh:
            print(host_key_upload_instructions(hostname))
            print()
            input('Press Enter after adding the public key to your Git host...')

    print('Testing SSH connection...')
    attempts = 0
    while attempts < 3:
        if ssh_connection_works(alias):
            print('SSH authentication succeeded.')
            return configured_remote
        attempts += 1
        if attempts >= 3:
            break
        print('SSH authentication failed.')
        if not prompt_yes_no('Try again', default=True):
            sys.exit(
                'SSH authentication failed. Verify the public key is uploaded '
                'and that you have access to the repository.'
            )
        input('Press Enter after fixing SSH access...')

    sys.exit(
        'SSH authentication failed. Verify the public key is uploaded '
        'and that you have access to the repository.'
    )

def should_commit_day(day, base_probability, trend_factor, day_of_week):
    if day_of_week >= 5:
        base_probability = base_probability * 0.3
    adjusted = base_probability + (trend_factor * random.uniform(-0.15, 0.15))
    adjusted = max(0, min(100, adjusted))
    return random.random() * 100 < adjusted

def get_commit_count(day, max_commits, trend_factor):
    if max_commits <= 1:
        return 1
    base = random.randint(1, max_commits)
    if trend_factor > 0:
        base = min(max_commits, base + int(random.uniform(0, trend_factor * 2)))
    elif trend_factor < 0:
        base = max(1, base + int(random.uniform(trend_factor * 2, 0)))
    return max(1, min(max_commits, base))

def generate_commits(repo_path, start_date, total_days, probability, max_commits, no_weekends, trend):
    commit_count = 0
    commit_messages = [
        "Update core functionality",
        "Refactor module structure",
        "Fix edge case handling",
        "Add validation layer",
        "Optimize query execution",
        "Remove deprecated methods",
        "Bump dependency versions",
        "Improve test coverage",
        "Adjust configuration values",
        "Patch security issue",
        "Update documentation",
        "Implement rate limiting",
        "Add logging statements",
        "Clean up imports",
        "Fix type annotations",
        "Restructure project layout",
        "Add error recovery",
        "Update build process",
        "Improve error messages",
        "Sync with upstream"
    ]
    
    file_names = [
        "core.py", "utils.py", "models.py", "views.py",
        "handlers.py", "middleware.py", "config.py",
        "constants.py", "validators.py", "services.py",
        "repositories.py", "factories.py", "adapters.py",
        "serializers.py", "decorators.py", "exceptions.py",
        "mixins.py", "signals.py", "tasks.py", "commands.py"
    ]
    
    for day_offset in range(total_days):
        current_day = start_date + timedelta(days=day_offset)
        weekday = current_day.weekday()
        if no_weekends and weekday >= 5:
            continue
        
        trend_factor = trend * (day_offset / total_days) if total_days > 0 else 0
        
        if not should_commit_day(current_day, probability, trend_factor, weekday):
            continue
        
        commits_today = get_commit_count(current_day, max_commits, trend_factor)
        commit_times = []
        
        for _ in range(commits_today):
            hour = random.randint(9, 22)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            commit_time = current_day.replace(
                hour=hour,
                minute=minute,
                second=second,
                microsecond=0,
                tzinfo=timezone.utc
            )
            commit_times.append(commit_time)
        
        commit_times.sort()
        
        for commit_time in commit_times:
            selected_files = random.sample(file_names, random.randint(1, 3))
            for fname in selected_files:
                file_path = os.path.join(repo_path, fname)
                if not os.path.exists(file_path):
                    with open(file_path, 'w') as f:
                        f.write(f"# {fname}\n")
                with open(file_path, 'a') as f:
                    f.write(f"{random.randint(1, 9999)}\n")
            
            run_cmd(['git', 'add', '.'], cwd=repo_path)
            msg = random.choice(commit_messages)
            date_str = commit_time.strftime('%Y-%m-%d %H:%M:%S %z')
            commit_env = os.environ.copy()
            commit_env['GIT_AUTHOR_DATE'] = date_str
            commit_env['GIT_COMMITTER_DATE'] = date_str
            run_cmd([
                'git', '-c', 'commit.gpgsign=false',
                'commit',
                '-m', msg,
                '--date', date_str
            ], cwd=repo_path, env=commit_env)
            commit_count += 1
            if commit_count == 1 or commit_count % 25 == 0:
                print(
                    f'Created {commit_count} commits '
                    f'(latest: {commit_time.strftime("%Y-%m-%d %H:%M:%S UTC")})',
                    flush=True
                )

    print(f'Finished generating {commit_count} commits.', flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=365,
                        help='Number of days to generate (default: 365)')
    parser.add_argument('--probability', type=int, default=75,
                        help='Base probability of committing on a day (0-100, default: 75)')
    parser.add_argument('--max-commits', type=int, default=8,
                        help='Maximum commits per active day (default: 8)')
    parser.add_argument('--no-weekends', action='store_true',
                        help='Skip weekend days')
    parser.add_argument('--trend', type=float, default=0.0,
                        help='Trend factor (-1.0 to 1.0) affecting commit frequency over time')
    parser.add_argument('--repo-path', type=str, default=None,
                        help='Path to git repository (on Windows, relative and /home/... '
                             'paths are placed under %%USERPROFILE%%\\spofer)')
    parser.add_argument('--remote', type=str,
                        help='Remote URL to push to')
    parser.add_argument('--branch', type=str, default='main',
                        help='Branch name (default: main)')
    parser.add_argument('--name', type=str, default='Git User',
                        help='Git user.name')
    parser.add_argument('--email', type=str, default='git@localhost',
                        help='Git user.email')
    parser.add_argument('--skip-ssh-setup', action='store_true',
                        help='Skip automatic SSH key setup when using an SSH remote URL')
    parser.add_argument('--skip-gen', action='store_true',
                        help='Skip commit generation; only set up SSH and push existing history')
    
    args = parser.parse_args()
    
    if args.skip_gen and not args.remote:
        sys.exit('--skip-gen requires --remote')
    
    if args.probability < 0 or args.probability > 100:
        sys.exit('Probability must be between 0 and 100')
    if args.max_commits < 1 or args.max_commits > 50:
        sys.exit('Max commits must be between 1 and 50')
    if args.trend < -1.0 or args.trend > 1.0:
        sys.exit('Trend must be between -1.0 and 1.0')
    
    repo_path = resolve_repo_path(args.repo_path, args.remote)
    if platform.system() == 'Windows' and not args.repo_path:
        print(f'Using Windows repo path: {repo_path}', flush=True)
    elif platform.system() == 'Windows' and args.repo_path.replace('\\', '/').startswith('/home/'):
        print(f'Mapped /home/... path to: {repo_path}', flush=True)
    
    if not os.path.exists(repo_path):
        if args.skip_gen:
            sys.exit(f'No repository found at {repo_path}')
        os.makedirs(repo_path)
        run_cmd(['git', 'init', '-b', args.branch], cwd=repo_path)
    elif not os.path.exists(os.path.join(repo_path, '.git')):
        if args.skip_gen:
            sys.exit(f'No git repository found at {repo_path}')
        run_cmd(['git', 'init', '-b', args.branch], cwd=repo_path)
    
    run_cmd(['git', 'config', 'user.name', args.name], cwd=repo_path)
    run_cmd(['git', 'config', 'user.email', args.email], cwd=repo_path)
    run_cmd(['git', 'config', 'commit.gpgsign', 'false'], cwd=repo_path)
    
    if args.skip_gen:
        returncode, out, _ = run_cmd_result(['git', 'rev-list', '--count', 'HEAD'], cwd=repo_path)
        if returncode != 0 or out.strip() == '0':
            sys.exit(f'Repository at {repo_path} has no commits to push.')
        print(f'Skipping commit generation. Pushing {out.strip()} existing commits from {repo_path}.', flush=True)
    else:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=args.days)
        
        expected_commits = int(args.days * (args.probability / 100) * ((args.max_commits + 1) / 2))
        print(
            f'Generating commits in {repo_path} '
            f'(expect roughly {expected_commits} commits; this can take several minutes)...',
            flush=True
        )
        
        generate_commits(
            repo_path,
            start_date,
            args.days,
            args.probability,
            args.max_commits,
            args.no_weekends,
            args.trend
        )
    
    if args.remote:
        remote_url = args.remote
        if is_ssh_remote(remote_url) and not args.skip_ssh_setup:
            remote_url = ensure_ssh_setup(remote_url, args.email)
        run_cmd(['git', 'remote', 'remove', 'origin'], cwd=repo_path, check=False)
        run_cmd(['git', 'remote', 'add', 'origin', remote_url], cwd=repo_path)
        run_cmd(['git', 'push', '-u', 'origin', args.branch, '--force'], cwd=repo_path)
        print(f'Pushed {repo_path} to {args.remote}', flush=True)
    elif not args.skip_gen:
        print(f'Generated {args.days} days of commits in {repo_path}')

if __name__ == "__main__":
    main()
