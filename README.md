# Roam Extension Setup Script

This Python script automates creating and updating a Roam Research extension in Roam Depot. It:

1. **Creates** a new local Git repository for your extension (on the `master` branch).
2. **Publishes** it to GitHub (using GitHub CLI).
3. **Forks** the [roam-depot repository](https://github.com/Roam-Research/roam-depot) if needed.
4. **Adds** your extension’s metadata JSON file to your `roam-depot` fork.
5. **Opens** a Pull Request (PR) from your `master` branch to Roam’s `main` branch.
6. **Provides** an update mechanism so you can modify your extension’s code and update the same PR with a single command.

## Prerequisites

1. **Git** installed.
2. **Python 3** installed.
3. [**GitHub CLI**](https://cli.github.com/) installed and authenticated:

    ```bash
    gh auth login
    ```
4. A GitHub account.

## Usage

1. **Clone or copy** this script locally, then make it executable (on macOS/Linux):

    ```bash
    chmod +x setup_roam_extension.py
    ```

2. **Submit** your extension for the first time by running:

    ```bash
    python setup_roam_extension.py submit
    ```

- You’ll be prompted for required details such as repository name, extension name, description, etc.
- **GitHub username** is **auto-detected** via `gh api user -q .login`.
- A local folder named after your extension repository will be created.
- The new GitHub repo will be initialized on the `master` branch and pushed to GitHub.
- A metadata JSON file will be added to your fork of `roam-depot`.
- A PR to the official `roam-depot` is opened automatically.

3. **Edit** your extension code (`extension.js`, etc.) as needed.

4. **Update** an existing PR after making changes:

    ```bash
    python setup_roam_extension.py update --extension-repo-name “my-roam-extension”
    ```

- This will commit and push new code to `master`.
- It will update the **`source_commit`** in your metadata JSON to point to the latest commit.
- This automatically updates the **same** Pull Request, so no need to open a new one.

5. **Resume** after failures:
- The script uses a _checkpoint file_ (`roam_extension_setup_state.json`) to track progress.
- If a command fails (e.g., a branch mismatch), fix the issue, re-run `submit`, and the script will continue from the last successful stage.

6. **Reset** and start from scratch:

    ```bash
    python setup_roam_extension.py submit --reset
    ```
- This removes the checkpoint so the script starts at stage 0 again.

## Example Commands

### First-time Submit

    ```bash
    python setup_roam_extension.py submit 
    --extension-repo-name “roam-new-daypage-block” 
    --extension-name “Create a new Block on a Daily page Roam Shortcut” 
    --extension-short-description “Introduces a shortcut to create a new block on the current day’s page and open it in a sidebar.” 
    --extension-author “John Doe”
    ```
### Update an Existing Extension

    ```bash
    python setup_roam_extension.py update
    --extension-repo-name “roam-new-daypage-block”    
    ```

After your Pull Request is merged by the Roam team, your extension should appear in the Roam Marketplace!
