import abc
import os
import re
import time
from typing import Any

import github_action_utils as gha_utils  # type: ignore
import requests

from builders import (
    ChangelogBuilderBase,
    CommitMessageChangelogBuilder,
    PullRequestChangelogBuilder,
)
from config import (
    COMMIT_MESSAGE,
    MARKDOWN_FILE,
    PULL_REQUEST,
    RESTRUCTUREDTEXT_FILE,
    ActionEnvironment,
    Configuration,
)
from run_git import (
    checkout_pull_request_branch,
    configure_git_author,
    configure_git_safe_directory,
    create_new_git_branch,
    git_commit_changelog,
)
from utils import display_whats_new, get_request_headers


class ChangelogCIBase(abc.ABC):
    """Base Class for Changelog CI"""

    GITHUB_API_URL: str = "https://api.github.com"

    def __init__(self, config: Configuration, action_env: ActionEnvironment) -> None:
        self.config = config
        self.action_env = action_env

        self.release_version = self._get_release_version()
        self.builder: ChangelogBuilderBase = self._get_changelog_builder(
            config, action_env, self.release_version
        )

    @property
    def _open_file_mode(self) -> str:
        """Gets the mode that the changelog file should be opened in"""
        if os.path.exists(self.config.changelog_filename):
            # if the changelog file exists
            # opens it in read-write mode
            file_mode = "r+"
        else:
            # if the changelog file does not exist
            # opens it in read-write mode
            # but creates the file first also
            file_mode = "w+"

        return file_mode

    @abc.abstractmethod
    def _get_release_version(self) -> str:
        """Get the release version"""
        pass

    @staticmethod
    def _get_changelog_builder(
        config: Configuration, action_env: ActionEnvironment, release_version: str
    ) -> ChangelogBuilderBase:
        """Get changelog Builder"""
        if config.changelog_type == PULL_REQUEST:
            return PullRequestChangelogBuilder(config, action_env, release_version)
        elif config.changelog_type == COMMIT_MESSAGE:
            return CommitMessageChangelogBuilder(config, action_env, release_version)
        else:
            raise ValueError(f"Unknown changelog type: {config.changelog_type}")

    def _update_changelog_file(self, string_data: str) -> None:
        """Write changelog to the changelog file"""
        with open(self.config.changelog_filename, self._open_file_mode) as f:
            # read the existing data and store it in a variable
            body = f.read()
            # write at the top of the file
            f.seek(0, 0)
            f.write(string_data)

            if body:
                # re-write the existing data
                f.write("\n\n")
                f.write(body)

    def run(self) -> None:
        changelog_string = self.builder.build()
        self._update_changelog_file(changelog_string)

class ChangelogCIPullRequestEvent(ChangelogCIBase):
    """Generates, commits and/or comments changelog for pull request events"""

    def __init__(self, config: Configuration, action_env: ActionEnvironment) -> None:
        super().__init__(config, action_env)

    def _get_release_version(self) -> str:
        """Get release version number from the pull request title or user Input"""
        release_version = self.config.end_version
        return release_version


if __name__ == "__main__":
    user_configuration = Configuration.create(os.environ)
    action_environment = ActionEnvironment.from_env(os.environ)

    changelog_ci_class = ChangelogCIPullRequestEvent
    # Initialize the Changelog CI
    ci = changelog_ci_class(user_configuration, action_environment)
    # Run Changelog CI
    ci.run()

    display_whats_new()
