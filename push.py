import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REMOTE = "origin"


def run(cmd, desc, capture=False):
    print(f"[PUSH] {desc}")
    print(f"  {' '.join(cmd)}")
    if capture:
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] {desc} failed!")
            if result.stdout.strip():
                print(result.stdout.strip())
            if result.stderr.strip():
                print(result.stderr.strip())
            sys.exit(1)
        return result.stdout.strip()
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"[ERROR] {desc} failed!")
        sys.exit(1)
    return ""

def cleanup():
    run(["git", "rm", "-r", "--cached", "."], "Cleaning git index", capture=False)

def check_identity():
    name = run(["git", "config", "user.name"], "Checking user.name", capture=True)
    email = run(["git", "config", "user.email"], "Checking user.email", capture=True)
    if not name or not email:
        print("[ERROR] git user.name / user.email not configured.")
        print('  git config user.name "Your Name"')
        print('  git config user.email "you@example.com"')
        sys.exit(1)
    print(f"[PUSH] identity: {name} <{email}>")


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else "update"

    cleanup()

    check_identity()

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                 "Reading current branch", capture=True)
    if not branch or branch == "HEAD":
        print("[ERROR] Detached HEAD, cannot push.")
        sys.exit(1)
    print(f"[PUSH] branch: {branch}")

    run(["git", "add", "-A"], "Staging changes")

    status = run(["git", "status", "--porcelain"], "Checking staged changes",
                 capture=True)
    if status:
        run(["git", "commit", "-m", msg], f'Committing: "{msg}"')
    else:
        print("[PUSH] nothing to commit, working tree clean")

    run(["git", "push", "-u", REMOTE, branch], f"Pushing to {REMOTE}/{branch}")

    head = run(["git", "rev-parse", "--short", "HEAD"], "Reading HEAD", capture=True)
    print(f"\n[DONE] pushed {branch} @ {head} -> {REMOTE}")


if __name__ == "__main__":
    main()