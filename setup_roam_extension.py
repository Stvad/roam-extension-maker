#!/usr/bin/env python3

import os
import subprocess
import sys
import shutil
import json
import argparse

CHECKPOINT_FILE = "roam_extension_setup_state.json"

def run_cmd(cmd, cwd=None):
    """
    Helper function to run shell commands with error handling.
    """
    print(f"\nRunning command: {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Command failed -> {cmd}")
        print(f"{e}")
        sys.exit(1)

def load_checkpoint():
    """
    Load the current stage checkpoint from file.
    Returns 0 if no checkpoint is found or if file is unreadable.
    """
    if not os.path.isfile(CHECKPOINT_FILE):
        return 0
    try:
        with open(CHECKPOINT_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_completed_stage", 0)
    except:
        return 0

def save_checkpoint(stage_number):
    """
    Save the last completed stage to the checkpoint file.
    """
    data = {"last_completed_stage": stage_number}
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f)

# ------------------------------------------------------------------------------
# SUB-COMMAND: SUBMIT
#   Creates a brand-new extension repo, forks roam-depot, publishes a new PR,
#   using 'master' as the default branch in your extension repo.
# ------------------------------------------------------------------------------

def stage_1_init_local_repo(args):
    print("\n=== Stage 1: Initialize local repository and create necessary files ===")

    # Create local folder if needed
    if not os.path.exists(args.extension_repo_name):
        os.makedirs(args.extension_repo_name)

    os.chdir(args.extension_repo_name)

    # Create extension.js either from file or from code
    if args.extension_file_path:
        if not os.path.isfile(args.extension_file_path):
            print(f"\nERROR: File '{args.extension_file_path}' does not exist.")
            sys.exit(1)
        print(f"Copying {args.extension_file_path} to extension.js")
        shutil.copyfile(args.extension_file_path, "extension.js")
    else:
        extension_js_code = args.extension_js_code.strip()
        if not extension_js_code:
            # Provide a default minimal extension.js if none is pasted
            extension_js_code = """export default {
  onload: () => { console.log("Extension loaded!"); },
  onunload: () => { console.log("Extension unloaded!"); }
};"""
        with open("extension.js", "w") as f:
            f.write(extension_js_code + "\n")

    # Create a minimal README.md if needed
    if not os.path.isfile("README.md"):
        with open("README.md", "w") as f:
            f.write(f"# {args.extension_name}\n\n{args.extension_short_description}\n\n")
            f.write("## Installation\n\n")
            f.write("1. Go to Roam Marketplace\n")
            f.write(f"2. Search for \"{args.extension_name}\"\n")
            f.write("3. Install\n\n")
            f.write("## Usage\n\n```javascript\n")
            f.write("// This extension adds ...\n")
            f.write("```\n")

    # Initialize local git repo
    run_cmd("git init")

    # Force-checkout branch "master"
    run_cmd("git checkout -b master")

    run_cmd("git add .")
    run_cmd('git commit -m "Initial commit of extension files"')

def stage_2_create_github_repo(args):
    print("\n=== Stage 2: Create the GitHub repo and push ===")

    # Build the description
    extension_description = f"{args.extension_short_description} (by {args.extension_author})"

    # Create a public GitHub repo
    create_repo_cmd = (
        f'gh repo create {args.extension_repo_name} '
        f'--public '
        f'--description "{extension_description}" '
        f'--source . '
        f'--remote upstream'
    )
    run_cmd(create_repo_cmd)

    # Now push to 'master'
    run_cmd("git push -u upstream master")

def stage_3_fork_roam_depot():
    print("\n=== Stage 3: Fork roam-depot ===")
    run_cmd("gh repo fork Roam-Research/roam-depot --remote=false --clone=false || true")

def stage_4_clone_fork(args):
    print("\n=== Stage 4: Clone your roam-depot fork locally ===")
    os.chdir("..")  # step out of extension repo

    if not os.path.exists(args.depot_folder):
        clone_cmd = f"gh repo clone {args.github_username}/roam-depot {args.depot_folder}"
        run_cmd(clone_cmd)

def stage_5_create_metadata_file(args):
    print("\n=== Stage 5: Create extension metadata file in roam-depot fork ===")

    # Capture current commit of the extension
    os.chdir(f"./{args.extension_repo_name}")
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()

    # Go to roam-depot
    os.chdir(f"../{args.depot_folder}")

    metadata_dir = f"extensions/{args.github_username}"
    os.makedirs(metadata_dir, exist_ok=True)
    metadata_file = f"{metadata_dir}/{args.extension_repo_name}.json"

    # Build tags array
    if args.extension_tags:
        tags_list = [t.strip() for t in args.extension_tags.split(",") if t.strip()]
        tags_json = "[" + ", ".join(f'"{t}"' for t in tags_list) + "]"
    else:
        tags_json = "[]"

    # Build JSON lines
    lines = [
        "{",
        f'  "name": "{args.extension_name}",',
        f'  "short_description": "{args.extension_short_description}",',
        f'  "author": "{args.extension_author}",',
        f'  "tags": {tags_json},',
        f'  "source_url": "https://github.com/{args.github_username}/{args.extension_repo_name}",',
        f'  "source_repo": "https://github.com/{args.github_username}/{args.extension_repo_name}.git",',
        f'  "source_commit": "{source_commit}"'
    ]
    if args.stripe_account:
        lines.append(f'  ,"stripe_account": "{args.stripe_account}"')
    lines.append("}")

    with open(metadata_file, "w") as f:
        f.write("\n".join(lines) + "\n")

    run_cmd(f'git add "{metadata_file}"')
    run_cmd(f'git commit -m "Add {args.extension_repo_name} metadata for Roam extension"')
    run_cmd("git push")

def stage_6_create_pr(args):
    print("\n=== Stage 6: Create Pull Request to Roam-Research/roam-depot ===")

    pr_title = f"Add {args.extension_name} extension"
    pr_body = (
        f"This PR adds a new extension [{args.extension_name}](https://github.com/{args.github_username}/{args.extension_repo_name})."
    )
    # Note: We base on 'main' in roam-depot, but head is your 'master'
    create_pr_cmd = (
        f'gh pr create '
        f'--title "{pr_title}" '
        f'--body "{pr_body}" '
        f'--base main '
        f'--head "{args.github_username}:master" '
        f'--repo Roam-Research/roam-depot'
    )
    run_cmd(create_pr_cmd)

def command_submit(args):
    """
    SUBCOMMAND: 'submit'
    Executes the multi-stage flow to create a new extension PR using 'master' as your repo's branch.
    """
    if args.reset and os.path.isfile(CHECKPOINT_FILE):
        print("Resetting the checkpoint. Starting from stage 0.")
        os.remove(CHECKPOINT_FILE)

    current_stage = load_checkpoint()

    # === STAGE 1 ===
    if current_stage < 1:
        stage_1_init_local_repo(args)
        save_checkpoint(1)
        current_stage = 1
    else:
        print("\nSkipping Stage 1 (already completed).")

    # === STAGE 2 ===
    if current_stage < 2:
        stage_2_create_github_repo(args)
        save_checkpoint(2)
        current_stage = 2
    else:
        print("\nSkipping Stage 2 (already completed).")

    # === STAGE 3 ===
    if current_stage < 3:
        stage_3_fork_roam_depot()
        save_checkpoint(3)
        current_stage = 3
    else:
        print("\nSkipping Stage 3 (already completed).")

    # === STAGE 4 ===
    if current_stage < 4:
        stage_4_clone_fork(args)
        save_checkpoint(4)
        current_stage = 4
    else:
        print("\nSkipping Stage 4 (already completed).")

    # === STAGE 5 ===
    if current_stage < 5:
        stage_5_create_metadata_file(args)
        save_checkpoint(5)
        current_stage = 5
    else:
        print("\nSkipping Stage 5 (already completed).")

    # === STAGE 6 ===
    if current_stage < 6:
        stage_6_create_pr(args)
        save_checkpoint(6)
        current_stage = 6
    else:
        print("\nSkipping Stage 6 (already completed).")

    print("\nAll stages completed successfully!")
    print("Your Pull Request should now be open. Once merged, your extension will appear in the Marketplace.")

# ------------------------------------------------------------------------------
# SUB-COMMAND: UPDATE
#   Commits/pushes new code changes in extension repo, updates commit hash in
#   roam-depot fork, and pushes to the same branch to update the open PR.
#   (Your extension uses 'master'.)
# ------------------------------------------------------------------------------

def update_extension_code(args):
    """
    1. Go to extension repo, commit & push any new changes (to 'master').
    2. Grab new commit hash.
    3. Update roam-depot fork’s metadata JSON, push changes (still to your fork's 'master').
    """
    repo_dir = args.extension_repo_name
    if not os.path.isdir(repo_dir):
        print(f"\nERROR: Directory '{repo_dir}' not found. Have you run 'submit' first?")
        sys.exit(1)

    # 1. Commit & push new changes in extension repo
    os.chdir(repo_dir)

    run_cmd("git add .")
    try:
        run_cmd('git commit -m "Update extension code"')
    except SystemExit:
        print("No new code changes found. Skipping commit.")

    run_cmd("git push -u upstream master")

    # 2. Get the new commit hash
    new_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()

    # 3. Update roam-depot fork
    os.chdir("..")
    depot_folder = args.depot_folder
    if not os.path.isdir(depot_folder):
        print(f"\nERROR: Directory '{depot_folder}' not found. Did you run 'submit' to clone your fork?")
        sys.exit(1)

    os.chdir(depot_folder)
    run_cmd("git pull")  # pull latest from your fork’s 'master'

    # Locate metadata file
    metadata_dir = f"extensions/{args.github_username}"
    metadata_file = f"{metadata_dir}/{args.extension_repo_name}.json"

    if not os.path.isfile(metadata_file):
        print(f"\nERROR: Metadata file '{metadata_file}' not found. Did you run 'submit' first?")
        sys.exit(1)

    # Update source_commit line
    with open(metadata_file, "r") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if '"source_commit"' in line:
            new_lines.append(f'  "source_commit": "{new_commit}"\n')
        else:
            new_lines.append(line)

    with open(metadata_file, "w") as f:
        f.writelines(new_lines)

    run_cmd(f'git add "{metadata_file}"')
    run_cmd(f'git commit -m "Update source_commit to {new_commit}"')
    run_cmd("git push")

    print("\nUpdate complete! Your existing PR should now reflect the new commit hash.")

# ------------------------------------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Set up or update a Roam extension PR with a resumable multi-stage workflow. Uses 'master' as your extension repo's branch."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # SUBCOMMAND: SUBMIT
    submit_parser = subparsers.add_parser("submit", help="Submit a brand-new extension PR to roam-depot, using 'master' branch.")
    submit_parser.add_argument("--reset", action="store_true", help="Reset the checkpoint and start from stage 0.")

    # Extension arguments
    submit_parser.add_argument("--extension-repo-name", help="Name of the new GitHub repo", required=False)
    submit_parser.add_argument("--extension-name", help="Human-readable name", required=False)
    submit_parser.add_argument("--extension-short-description", help="Short description", required=False)
    submit_parser.add_argument("--extension-author", help="Author name", required=False)
    submit_parser.add_argument("--extension-tags", default="", help="Comma-separated tags (e.g. 'test,print')")
    submit_parser.add_argument("--stripe-account", default="", help="Optional Stripe account ID.")
    submit_parser.add_argument("--extension-file-path", default="", help="Path to local extension.js file.")
    submit_parser.add_argument("--extension-js-code", default="", help="Inline extension.js code if no file is used.")
    submit_parser.add_argument("--depot-folder", default="roam-depot", help="Name of local fork folder for roam-depot.")

    # SUBCOMMAND: UPDATE
    update_parser = subparsers.add_parser("update", help="Update existing extension PR with new code changes. (Your repo uses 'master'.)")
    update_parser.add_argument("--extension-repo-name", help="Name of your extension's local folder/repo", required=True)
    update_parser.add_argument("--depot-folder", default="roam-depot", help="Local folder name of your roam-depot fork.")

    args = parser.parse_args()

    # AUTO-DETECT GITHUB USERNAME VIA GH CLI (needed for both 'submit' and 'update')
    try:
        detected_username = subprocess.check_output(["gh", "api", "user", "-q", ".login"]).decode().strip()
    except:
        print("ERROR: Could not detect your GitHub username via `gh api user -q .login`.")
        print("Make sure you are logged in: `gh auth login`.")
        sys.exit(1)

    setattr(args, "github_username", detected_username)
    print(f"Detected GitHub username: {args.github_username}")

    if args.command == "submit":
        # Prompt for missing fields
        if not args.extension_repo_name:
            args.extension_repo_name = input("Extension repository name (e.g. my-roam-extension): ").strip()
            if not args.extension_repo_name:
                print("ERROR: extension_repo_name is required.")
                sys.exit(1)

        if not args.extension_name:
            args.extension_name = input("Human-readable extension name (e.g. My Roam Extension): ").strip()
            if not args.extension_name:
                print("ERROR: extension_name is required.")
                sys.exit(1)

        if not args.extension_short_description:
            args.extension_short_description = input("Short description: ").strip()
            if not args.extension_short_description:
                print("ERROR: extension_short_description is required.")
                sys.exit(1)

        if not args.extension_author:
            args.extension_author = input("Author name: ").strip()
            if not args.extension_author:
                print("ERROR: extension_author is required.")
                sys.exit(1)

        if not args.extension_file_path and not args.extension_js_code:
            print("\nNo extension.js file or code provided. Paste your extension.js code below.")
            print("When finished, press Ctrl+D (macOS/Linux) or Ctrl+Z (Windows) on a new line, then Enter.\n")
            try:
                pasted_code = sys.stdin.read()
            except KeyboardInterrupt:
                print("\nCanceled by user.")
                sys.exit(0)
            if pasted_code.strip():
                args.extension_js_code = pasted_code.strip()
            else:
                # Provide a default minimal extension.js if none is pasted
                args.extension_js_code = """export default {
  onload: () => { console.log("Extension loaded!"); },
  onunload: () => { console.log("Extension unloaded!"); }
};"""

        # Run the multi-stage submit flow
        command_submit(args)

    elif args.command == "update":
        # Run the update flow
        update_extension_code(args)

if __name__ == "__main__":
    main()
