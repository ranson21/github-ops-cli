import os
import re
import json
import subprocess
from datetime import datetime
from typing import Optional, Tuple, Dict
import requests


class GitHubOps:
    def __init__(self, github_token: str, repo_owner: str, repo_name: str):
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.api_base = "https://api.github.com"

        # Configure git globally for HTTPS with token
        self._configure_git()

    def _configure_git(self):
        """Configure git globally to use HTTPS with token authentication."""
        commands = [
            # Configure HTTPS instead of SSH
            [
                "git",
                "config",
                "--global",
                "url.https://github.com/.insteadOf",
                "git@github.com:",
            ],
            # Configure authentication
            [
                "git",
                "config",
                "--global",
                "credential.helper",
                "store",
            ],
            ["git", "config", "--global", "user.email", "cloudbuild@example.com"],
            ["git", "config", "--global", "user.name", "Cloud Build"],
        ]

        # Write credentials to the store
        credential_file = os.path.expanduser("~/.git-credentials")
        with open(credential_file, "w") as f:
            f.write(f"https://oauth2:{self.github_token}@github.com\n")

        for cmd in commands:
            subprocess.run(cmd, check=True)

    def get_latest_version(self) -> str:
        """Get the latest release version from GitHub."""
        url = (
            f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
        )
        response = requests.get(url, headers=self.headers)

        if response.status_code == 404:
            return "v0.0.0"

        response.raise_for_status()
        return response.json()["tag_name"]

    def get_pr_info(self, pr_number: int) -> Dict:
        """Get PR information including labels."""
        url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}?state=all"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def determine_version_type(self, pr_labels: list) -> str:
        """Determine version type based on PR labels."""
        label_mapping = {
            "semver:major": "major",
            "semver:minor": "minor",
            "semver:patch": "patch",
        }

        for label in pr_labels:
            label_name = label["name"]
            if label_name in label_mapping:
                return label_mapping[label_name]

        return "timestamp"

    def bump_version(self, current_version: str, bump_type: str) -> str:
        """Bump version based on type."""
        print(f"Bumping version: current={current_version}, type={bump_type}")
        current = current_version.lstrip("v")
        print(f"Stripped version: {current}")

        if not bump_type:
            print("No bump type specified, defaulting to timestamp")
            bump_type = "timestamp"

        if bump_type == "timestamp":
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_version = f"v{current}-{timestamp}"
            print(f"Created timestamp version: {new_version}")
            return new_version

        try:
            if "-" in current:
                # Handle versions with timestamps by removing timestamp part
                current = current.split("-")[0]
                print(f"Removed timestamp: {current}")

            major, minor, patch = map(int, current.split("."))
            print(f"Parsed version: major={major}, minor={minor}, patch={patch}")

            if bump_type == "major":
                major += 1
                minor = patch = 0
            elif bump_type == "minor":
                minor += 1
                patch = 0
            elif bump_type == "patch":
                patch += 1
            else:
                print(f"Unknown bump type '{bump_type}', performing patch bump")
                patch += 1

            new_version = f"v{major}.{minor}.{patch}"
            print(f"Created new version: {new_version}")
            return new_version

        except ValueError as e:
            print(f"Error parsing version: {e}")
            print("Falling back to v0.0.0 with timestamp")
            return f"v0.0.0-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def create_release(
        self, version: str, is_draft: bool = False, skip_asset: bool = False
    ) -> int:
        """Create a new GitHub release and optionally upload assets.

        Args:
            version (str): The version tag for the release
            is_draft (bool): Whether to create as a draft release
            skip_asset (bool): Whether to skip creating and uploading the release asset

        Returns:
            int: The release ID
        """
        # Create the release first
        url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/releases"
        data = {
            "tag_name": version,
            "name": f"Release {version}",
            "body": f"Release version {version}",
            "draft": is_draft,
            "prerelease": False,
        }

        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        release_id = response.json()["id"]

        # Upload the release asset if not skipped
        if not skip_asset:
            try:
                print("Uploading release.tar.gz to release")
                self.upload_release_asset(
                    release_id=release_id,
                    file_path="release.tar.gz",
                    file_name="release.tar.gz",
                )
                print("Successfully uploaded release.tar.gz")
            except Exception as e:
                print(f"Error uploading release asset: {str(e)}")
                raise

        return release_id

    def upload_release_asset(
        self, release_id: int, file_path: str, file_name: str
    ) -> None:
        """Upload an asset to a release."""
        # Use the uploads.github.com endpoint for assets
        url = f"https://uploads.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/{release_id}/assets"
        params = {"name": file_name}
        headers = {
            "Authorization": f"token {self.github_token}",
            "Content-Type": "application/gzip",
            "Accept": "application/vnd.github.v3+json",
        }

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Release asset file not found: {file_path}")

        print(f"Uploading {file_path} to {url}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Directory contents: {os.listdir('.')}")

        try:
            with open(file_path, "rb") as f:
                response = requests.post(url, headers=headers, params=params, data=f)

            # Print detailed error information if the request fails
            if response.status_code != 201:
                print(f"Upload failed with status code: {response.status_code}")
                print(f"Response body: {response.text}")
                response.raise_for_status()

            result = response.json()
            print(f"Asset uploaded successfully. URL: {result['browser_download_url']}")

        except Exception as e:
            print(f"Exception during upload: {str(e)}")
            if "response" in locals():
                print(f"Response status code: {response.status_code}")
                print(f"Response body: {response.text}")
            raise

    def update_submodule(
        self, parent_repo: str, submodule_path: str, new_version: str
    ) -> str:
        """Update submodule in parent repository and create PR."""
        print(
            f"Updating submodule: repo={parent_repo}, path={submodule_path}, version={new_version}"
        )

        # Clone parent repo using HTTPS
        repo_url = f"https://github.com/{self.repo_owner}/{parent_repo}.git"
        print(f"Cloning parent repo from {repo_url}")
        subprocess.run(["git", "clone", repo_url, "parent-repo"], check=True)

        # Move into parent repo directory
        os.chdir("parent-repo")
        print(f"Changed directory to: {os.getcwd()}")

        # Make sure the submodule directory exists
        if not os.path.exists(submodule_path):
            print(f"Creating directory structure for {submodule_path}")
            os.makedirs(os.path.dirname(submodule_path), exist_ok=True)

        # Initialize and update only the specific submodule
        print(f"Initializing submodule: {submodule_path}")
        subprocess.run(["git", "submodule", "init", "--", submodule_path], check=True)

        print(f"Updating submodule: {submodule_path}")
        subprocess.run(
            ["git", "submodule", "update", "--init", "--", submodule_path], check=True
        )

        # If submodule doesn't exist yet, add it
        if not os.path.exists(os.path.join(submodule_path, ".git")):
            print(f"Adding new submodule at {submodule_path}")
            submodule_url = f"https://github.com/{self.repo_owner}/{self.repo_name}.git"
            subprocess.run(
                ["git", "submodule", "add", submodule_url, submodule_path], check=True
            )

        # Create branch and update submodule
        branch_name = f"update-{self.repo_name}-{new_version}"
        print(f"Creating branch: {branch_name}")
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)

        # Update submodule to specific version
        print(f"Updating submodule to version {new_version}")
        os.chdir(submodule_path)
        print(f"Changed directory to: {os.getcwd()}")

        # Get old commit before update
        try:
            old_commit = (
                subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
            )
            print(f"Current commit: {old_commit}")
        except subprocess.CalledProcessError:
            old_commit = "initial"
            print("No previous commit found (new submodule)")

        # Fetch and checkout the new version
        subprocess.run(["git", "fetch", "origin"], check=True)
        subprocess.run(["git", "checkout", new_version], check=True)

        # Get new commit after update
        new_commit = (
            subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        )
        print(f"New commit: {new_commit}")

        # Return to parent repo root
        os.chdir("../../..")
        print(f"Changed directory to: {os.getcwd()}")

        # Stage and commit changes
        print("Staging changes")
        subprocess.run(["git", "add", submodule_path], check=True)

        print("Committing changes")
        commit_message = f"chore: update {self.repo_name} submodule to {new_version}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)

        print("Pushing changes")
        subprocess.run(["git", "push", "origin", branch_name], check=True)

        # Create PR
        print("Creating pull request")
        return self.create_submodule_pr(
            parent_repo, branch_name, new_version, old_commit, new_commit
        )

    def create_submodule_pr(
        self,
        parent_repo: str,
        branch_name: str,
        version: str,
        old_commit: str,
        new_commit: str,
    ) -> int:
        """Create and optionally auto-merge PR for submodule update."""
        url = f"{self.api_base}/repos/{self.repo_owner}/{parent_repo}/pulls"
        data = {
            "title": f"Update {self.repo_name} submodule to {version}",
            "body": f"This PR updates the {self.repo_name} submodule from commit `{old_commit}` to `{new_commit}`\n\nVersion: {version}",
            "head": branch_name,
            "base": "master",
        }

        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        pr_number = response.json()["number"]

        # Add semver:patch label to the PR
        labels_url = f"{self.api_base}/repos/{self.repo_owner}/{parent_repo}/issues/{pr_number}/labels"
        labels_data = {"labels": ["semver:patch"]}
        label_response = requests.post(
            labels_url, headers=self.headers, json=labels_data
        )
        if label_response.status_code == 200:
            print(f"Successfully added semver:patch label to PR #{pr_number}")
        else:
            print(f"Failed to add label to PR #{pr_number}")
            print(f"Status code: {label_response.status_code}")
            print(f"Response: {label_response.text}")

        # Auto-merge the PR
        merge_url = f"{self.api_base}/repos/{self.repo_owner}/{parent_repo}/pulls/{pr_number}/merge"
        merge_data = {
            "merge_method": "merge",
            "commit_title": f"chore: update {self.repo_name} submodule to {version} (#{pr_number})",
            "commit_message": f"Update {self.repo_name} submodule from commit `{old_commit}` to `{new_commit}`\n\nVersion: {version}",
        }

        print(f"Attempting to merge PR #{pr_number}")
        merge_response = requests.put(merge_url, headers=self.headers, json=merge_data)

        if merge_response.status_code == 200:
            print(f"Successfully merged PR #{pr_number}")
        else:
            print(f"Failed to merge PR #{pr_number}")
            print(f"Status code: {merge_response.status_code}")
            print(f"Response: {merge_response.text}")

        return pr_number
