#!/usr/bin/env python3
import argparse
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from subprocess import Popen, PIPE
import tempfile
import json

def run_cmd(cmd, cwd=None, check=True, capture=True):
    proc = Popen(cmd, shell=False, cwd=cwd, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    if check and proc.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{err.decode()}")
    return out.decode().strip() if capture else None

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
    os.chdir(repo_path)
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
                if not os.path.exists(fname):
                    with open(fname, 'w') as f:
                        f.write(f"# {fname}\n")
                with open(fname, 'a') as f:
                    f.write(f"{random.randint(1, 9999)}\n")
            
            run_cmd(['git', 'add', '.'], cwd=repo_path)
            msg = random.choice(commit_messages)
            date_str = commit_time.strftime('%Y-%m-%d %H:%M:%S %z')
            run_cmd([
                'git', 'commit',
                '-m', msg,
                '--date', date_str
            ], cwd=repo_path)

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
    parser.add_argument('--repo-path', type=str, required=True,
                        help='Path to git repository')
    parser.add_argument('--remote', type=str,
                        help='Remote URL to push to')
    parser.add_argument('--branch', type=str, default='main',
                        help='Branch name (default: main)')
    parser.add_argument('--name', type=str, default='Git User',
                        help='Git user.name')
    parser.add_argument('--email', type=str, default='git@localhost',
                        help='Git user.email')
    
    args = parser.parse_args()
    
    if args.probability < 0 or args.probability > 100:
        sys.exit('Probability must be between 0 and 100')
    if args.max_commits < 1 or args.max_commits > 50:
        sys.exit('Max commits must be between 1 and 50')
    if args.trend < -1.0 or args.trend > 1.0:
        sys.exit('Trend must be between -1.0 and 1.0')
    
    repo_path = os.path.abspath(args.repo_path)
    
    if not os.path.exists(repo_path):
        os.makedirs(repo_path)
        run_cmd(['git', 'init', '-b', args.branch], cwd=repo_path)
    elif not os.path.exists(os.path.join(repo_path, '.git')):
        run_cmd(['git', 'init', '-b', args.branch], cwd=repo_path)
    
    run_cmd(['git', 'config', 'user.name', args.name], cwd=repo_path)
    run_cmd(['git', 'config', 'user.email', args.email], cwd=repo_path)
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=args.days)
    
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
        run_cmd(['git', 'remote', 'remove', 'origin'], cwd=repo_path, check=False)
        run_cmd(['git', 'remote', 'add', 'origin', args.remote], cwd=repo_path)
        run_cmd(['git', 'push', '-u', 'origin', args.branch, '--force'], cwd=repo_path)
    
    print(f"Generated {args.days} days of commits in {repo_path}")

if __name__ == "__main__":
    main()
