# GUIDE: Installing Ghostclaw

This guide explains how to install and integrate the **Ghostclaw** skill into your OpenClaw environment.

## Prerequisites

- **OpenClaw** installed on your system.
- **Node.js** and **npm**.
- **Python 3.8+** (required to run Ghostclaw's core analyzer).

## Installation Methods

### Method 1: ClawHub (Recommended)

Ghostclaw is available on ClawHub. You can install it using the `clawdhub`:

```bash
clawdhub install ghostclaw
```

### Method 2: NPX Skills CLI

You can also install via the generic skills manager:

```bash
npx skills add Ev3lynx727/ghostclaw
```

### Method 3: Build from source

If you want to contribute or run from the latest source code:

```bash
git clone https://github.com/Ev3lynx727/ghostclaw.git
cd ghostclaw
# Install dependencies
pip install .
# Or for development
pip install -e .
```

## Configuration

Once installed, Ghostclaw is located in your OpenClaw skills directory (usually `~/.openclaw/skills/ghostclaw`).

### Setting up Repositories to Watch

Add your repository paths to `scripts/repos.txt`:

```text
/path/to/your/project-a
/path/to/your/project-b
```

### GitHub Integration (Optional)

To allow Ghostclaw to open Pull Requests, set your `GH_TOKEN`:

```bash
export GH_TOKEN=your_github_token_here
```

## Usage

### 1. Ad-hoc Review

Ask your agent:
> "ghostclaw, review the current repository for architectural issues"

### 3. Comparing Trends

View health trends across multiple repositories:

```bash
./scripts/compare.sh --repos-file scripts/repos.txt
```

## Troubleshooting

- **Python not found**: Ensure `python3` is in your PATH.
- **ClawHub Errors**: Ensure you have the latest version of `clawhub-cli`.
- **Permission issues**: Check that `~/.openclaw` is writable.
