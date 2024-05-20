import os
import argparse
import json
from pathlib import Path
from pygit2 import Repository
from git_ai.cmd.ai_repo import AIRepo
from git_ai.cmd.constants import AIRepoConstants
from git_ai.pygitutils.pygitutils import read_config

# Try fbi
# https://stackoverflow.com/questions/37304461/tensorflow-importing-data-from-a-tensorboard-tfevent-file


class AIDiff(AIRepoConstants):
    def __init__(self, repo):
        self.repo = repo

    def _check_value(self, values_dict_a, values_dict_b, value_key, cmp_func):
        changes = []
        added = []
        deleted = []

        for key, value in values_dict_a.items():
            if ((key in values_dict_b) and
               (not cmp_func(value[value_key], values_dict_b[key][value_key]))):
                changes.append(
                    (key, value[value_key], values_dict_b[key][value_key]))
            if key not in values_dict_b:
                deleted.append((key, value[value_key]))

        for key, value in values_dict_b.items():
            if key not in values_dict_a:
                added.append((key, value[value_key]))

        return changes, added, deleted

    def _compare_lists(self, xs, ys):
        return all([x == y for x, y in zip(xs, ys)])

    def diff_plots(self, metrics_a, metrics_b):
        changes, added, deleted = self._check_value(
            metrics_a,
            metrics_b,
            'values',
            lambda xs, ys: (len(xs) == len(ys)) and self._compare_lists(xs, ys)
        )

        return changes, added, deleted

    def diff_hparams(self, hparamsA, hparamsB):
        hparamsA_json = (json.loads(hparamsA) if hparamsA
                         else {})
        hparamsB_json = (json.loads(hparamsB) if hparamsB
                         else {})

        changes = []
        added = []
        deleted = []

        values_dict_a = {e['label']: e for e in hparamsA_json}
        values_dict_b = {e['label']: e for e in hparamsB_json}
        changes, added, deleted = self._check_value(
            values_dict_a,
            values_dict_b,
            'value',
            lambda x, y: x == y
        )

        return changes, added, deleted

    def print_change(self, change, type, identation):
        print("")
        if type == 'addition':
            key, new_value = change
            print(identation + "%s" % (key))
            print(identation + "+ %s" % str(new_value))
        if type == 'deletion':
            key, old_value = change
            print(identation + "%s" % (key))
            print(identation + "- %s" % str(old_value))
            pass
        if type == 'change':
            key, old_value, new_value = change
            print(identation + "%s" % (key))
            print(identation + "- %s" % str(old_value))
            print(identation + "+ %s" % str(new_value))

    def list_plots(self, commit_spec):
        commit = self.repo.get(commit_spec)
        if AIRepoConstants.METRICS_PATH not in commit.tree:
            return {}

        plots_folder = commit.tree / AIRepoConstants.METRICS_PATH    # type: ignore
        all_folders = {
            f.name.removesuffix('_header'):
                json.loads(plots_folder[f.name.removesuffix('_header')].data)
            for f in plots_folder if f.name.endswith('_header')}

        return all_folders

    def run(self, commitA, commitB, identation):
        if not commitB:
            # Reference to current head
            # TODO: This inverts the order of the commits. Can be confusing!
            this_commit = str(self.repo.head.target)
            that_commit = self.repo.resolve_refish(commitA)[0].hex
        else:
            this_commit = self.repo.resolve_refish(commitA)[0].hex
            that_commit = self.repo.resolve_refish(commitB)[0].hex

        print(identation + this_commit, that_commit)
        hparamsA = self.repo.list_file_contents(
            this_commit, self.HPARAMS_JSON_PATH)
        hparamsB = self.repo.list_file_contents(
            that_commit, self.HPARAMS_JSON_PATH)

        changes, added, deleted = self.diff_hparams(hparamsA, hparamsB)
        plots_a = self.list_plots(this_commit)
        plots_b = self.list_plots(that_commit)
        changes_plots, added_plots, deleted_plots = self.diff_plots(
            plots_a, plots_b
        )
        changes.extend(changes_plots)
        added.extend(added_plots)
        deleted.extend(deleted_plots)

        diff = self.repo.diff(this_commit, that_commit)
        text_diffs = [
            d for d in diff
            if ((not d.delta.is_binary) and
                (not Path(d.delta.new_file.path).is_relative_to(Path(self.GIT_AI_ROOT))) and
                (not Path(d.delta.old_file.path).is_relative_to(Path(self.GIT_AI_ROOT))))]

        for d in text_diffs:
            print(identation + d.text)

        for change in changes:
            self.print_change(change, 'change', identation)
        for add in added:
            self.print_change(add, 'addition', identation)
        for deletion in deleted:
            self.print_change(deletion, 'deletion', identation)

        # Check input repos
        this_config = read_config(self.repo, this_commit)
        that_config = read_config(self.repo, that_commit)
        if this_config:
            for path, input_repo in this_config.input_repos.items():
                input_repo_handle = AIRepo(Path(self.repo.workdir) / path)
                that_input_commit = that_config.get_input_repo(path).commit
                print("")
                print(input_repo.path)
                AIDiff(input_repo_handle).run(input_repo.commit,
                                              that_input_commit, identation + "    ")


def diff(args):
    parser = argparse.ArgumentParser(description='Git AI diff')
    parser.add_argument(
        'commitA',
        type=str,
        help=('First commit to be compared, if no other commit is specified,'
              '  compare this commit with HEAD'))
    parser.add_argument(
        'commitB',
        type=str,
        nargs='?',
        default='',
        help=('Second commit to be compared'))
    parsed_args = parser.parse_args(args[2:])
    repo = AIRepo(os.getcwd())
    AIDiff(repo).run(parsed_args.commitA, parsed_args.commitB, "")
