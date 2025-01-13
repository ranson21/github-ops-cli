import os
import argparse
import re
import requests
from github_ops import GitHubOps
from typing import Optional


def write_version_to_file(version: str, filename: str) -> None:
    """Write version string to a file"""
    workspace_path = os.path.join(os.getcwd(), filename)
    print(f"Writing version {version} to {workspace_path}")
    with open(workspace_path, "w") as f:
        f.write(version)


def str2bool(v):
    """Convert string to boolean value"""
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def parse_pr_number(value):
    """Parse PR number, returning None for empty or invalid values"""
    if not value:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def get_pr_from_merge_commit(self, commit_sha: str) -> Optional[int]:
    """Extract PR number from merge commit message."""
    try:
        print(f"Attempting to find PR for commit: {commit_sha}")

        # First try the pulls endpoint with explicit pagination
        url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/commits/{commit_sha}/pulls"
        print(f"Checking pulls endpoint: {url}")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        pulls_data = response.json()

        if pulls_data:
            pr_number = pulls_data[0]["number"]
            print(f"Found PR #{pr_number} from pulls API")
            return pr_number

        # If that doesn't work, try the commit endpoint
        url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/commits/{commit_sha}"
        print(f"Checking commit endpoint: {url}")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        commit_data = response.json()

        commit_message = commit_data["commit"]["message"]
        print(f"Commit message: {commit_message}")

        # Try different merge commit message patterns
        patterns = [
            r"Merge pull request #(\d+)",
            r"Pull request #(\d+)",
            r"#(\d+) from",
            r"PR-(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, commit_message)
            if match:
                pr_number = int(match.group(1))
                print(
                    f"Found PR #{pr_number} from commit message using pattern: {pattern}"
                )
                return pr_number

    except Exception as e:
        print(f"Error getting PR from merge commit: {str(e)}")
        if "response" in locals():
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")

    print("Could not find PR number from commit")
    return None


def create_parser():
    """Create parser that handles both positional and named arguments"""
    parser = argparse.ArgumentParser(description="GitHub Operations CLI")

    # Create parent parser for shared optional arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-t", "--github-token", help="GitHub token")
    parent_parser.add_argument(
        "-p", "--pr-number", type=parse_pr_number, help="PR number"
    )
    parent_parser.add_argument("-v", "--version-type", help="Version bump type")
    parent_parser.add_argument("-c", "--current-version", help="Current version")

    # Add mutually exclusive group for release type
    release_type = parent_parser.add_mutually_exclusive_group()
    release_type.add_argument(
        "-d", "--is-draft", type=str2bool, default=None, help="Create draft release"
    )
    release_type.add_argument(
        "-r",
        "--is-prod",
        type=str2bool,
        default=None,
        help="Create production (non-draft) release",
    )

    parent_parser.add_argument(
        "-s",
        "--skip-asset",
        action="store_true",
        help="Skip creating and uploading release asset",
    )
    parent_parser.add_argument("-r", "--parent-repo", help="Parent repository name")
    parent_parser.add_argument("-m", "--submodule-path", help="Submodule path")
    parent_parser.add_argument(
        "-i",
        "--is-merge",
        type=str2bool,
        default=False,
        help="Whether this is a merge operation",
    )

    # Create mutually exclusive group for action specification
    action_group = parser.add_mutually_exclusive_group(required=True)

    # Add positional action argument
    action_group.add_argument(
        "action",
        nargs="?",
        choices=["get-version", "bump-version", "create-release", "update-submodule"],
        help="Action to perform (positional)",
    )
    # Add named action argument
    action_group.add_argument(
        "-a",
        "--action",
        dest="named_action",
        choices=["get-version", "bump-version", "create-release", "update-submodule"],
        help="Action to perform (named)",
    )

    # Create mutually exclusive groups for repo owner and name
    owner_group = parser.add_mutually_exclusive_group(required=True)
    owner_group.add_argument(
        "repo_owner", nargs="?", help="Repository owner (positional)"
    )
    owner_group.add_argument(
        "-o", "--repo-owner", dest="named_owner", help="Repository owner (named)"
    )

    name_group = parser.add_mutually_exclusive_group(required=True)
    name_group.add_argument("repo_name", nargs="?", help="Repository name (positional)")
    name_group.add_argument(
        "-n", "--repo-name", dest="named_name", help="Repository name (named)"
    )

    # Add all optional arguments
    for action in parent_parser._actions:
        parser._add_action(action)

    return parser


def parse_args(args=None):
    """Parse args supporting both styles"""
    parser = create_parser()

    # If no args provided, use sys.argv[1:]
    if args is None:
        import sys

        args = sys.argv[1:]

    # Parse arguments
    parsed_args = parser.parse_args(args)

    # Consolidate named and positional arguments
    parsed_args.action = parsed_args.action or parsed_args.named_action
    parsed_args.repo_owner = parsed_args.repo_owner or parsed_args.named_owner
    parsed_args.repo_name = parsed_args.repo_name or parsed_args.named_name

    # Clean up namespace
    del parsed_args.named_action
    del parsed_args.named_owner
    del parsed_args.named_name

    return parsed_args


def main():
    args = parse_args()

    # Get token from args or environment
    github_token = args.github_token or os.environ.get("GITHUB_TOKEN")
    if not github_token:
        raise ValueError(
            "GitHub token must be provided either via --github-token or GITHUB_TOKEN environment variable"
        )

    ops = GitHubOps(github_token, args.repo_owner, args.repo_name)

    print(f"Current working directory: {os.getcwd()}")

    if args.action == "get-version":
        version = ops.get_latest_version()
        write_version_to_file(version, "current_version.txt")
        print(f"Latest version {version} written to current_version.txt")

    elif args.action == "bump-version":
        if not args.current_version:
            raise ValueError("current-version is required for bump-version")

        # Debug all relevant environment variables
        print("Environment variables:")
        print(f"COMMIT_SHA: {os.environ.get('COMMIT_SHA')}")
        print(f"_COMMIT_SHA: {os.environ.get('_COMMIT_SHA')}")
        print(f"Version type: {args.version_type}")
        print(f"Is merge: {os.environ.get('_IS_MERGE')}")

        # Get PR number from args, environment variable, or commit SHA
        pr_number = args.pr_number
        if pr_number is None:
            env_pr_number = os.environ.get("_PR_NUMBER")
            pr_number = parse_pr_number(env_pr_number)

        # is_merge = str2bool(os.environ.get("_IS_MERGE", "false"))
        # Fix the is_merge check
        is_merge = args.is_merge  # This will now come from the --is-merge flag
        print(f"Is merge operation: {is_merge}")

        if is_merge and not pr_number:
            # Try to get PR number from merge commit
            commit_sha = (
                args.version_type
            )  # We're using _PR_TYPE to pass commit SHA in merge
            if commit_sha:
                print(f"Looking up PR number from merge commit: {commit_sha}")
                pr_number = get_pr_from_merge_commit(ops, commit_sha)
                if pr_number:
                    print(f"Found PR #{pr_number} from merge commit")

        print(f"PR Number: {pr_number}")

        # Determine version type from PR labels if PR number is available
        version_type = args.version_type
        if pr_number:
            try:
                pr_info = ops.get_pr_info(pr_number)
                labels = pr_info.get("labels", [])
                print(f"PR Labels: {[label['name'] for label in labels]}")
                version_type = ops.determine_version_type(labels)
                print(f"Determined version type from labels: {version_type}")
            except Exception as e:
                print(f"Error getting PR info: {e}")
                print("Falling back to provided version type")

        if not version_type:
            version_type = "timestamp"
        print(f"Using version type: {version_type}")

        try:
            with open("current_version.txt", "r") as f:
                current_version = f.read().strip()
            print(f"Read current version: {current_version}")
        except FileNotFoundError:
            print("Warning: current_version.txt not found, using argument value")
            current_version = args.current_version

        new_version = ops.bump_version(current_version, version_type)
        write_version_to_file(new_version, "new_version.txt")
        print(f"New version {new_version} written to new_version.txt")

    elif args.action == "create-release":
        try:
            with open("new_version.txt", "r") as f:
                version = f.read().strip()
            print(f"Read version from new_version.txt: {version}")
        except FileNotFoundError:
            print("Warning: new_version.txt not found, using argument value")
            version = args.current_version

        # Determine draft status
        is_draft = True  # Default to draft
        if args.is_draft is not None:
            is_draft = args.is_draft
        elif args.is_prod is not None:
            is_draft = not args.is_prod

        release_id = ops.create_release(version, is_draft, args.skip_asset)
        print(f"Created release with ID: {release_id}")

    elif args.action == "update-submodule":
        if not args.is_merge:
            print("Skipping submodule update as this is not a merge operation")
            return

        try:
            with open("new_version.txt", "r") as f:
                version = f.read().strip()
            print(f"Read version from new_version.txt: {version}")
        except FileNotFoundError:
            print("Warning: new_version.txt not found, using argument value")
            version = args.current_version

        if not all([args.parent_repo, args.submodule_path]):
            raise ValueError(
                "parent-repo and submodule-path are required for update-submodule"
            )
        pr_number = ops.update_submodule(args.parent_repo, args.submodule_path, version)
        print(f"Created PR #{pr_number} for submodule update")


if __name__ == "__main__":
    main()
