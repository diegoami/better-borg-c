"""Bounded metadata review must not claim better play or probe excluded lanes."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('review', Path(__file__).with_name('fork-review.py'))
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class Review(unittest.TestCase):
    def transport(self, changed=False, missing=False, broken=False):
        calls = []
        def get(path, optional=False):
            calls.append(path)
            if path == 'repos/angband/angband/commits/master':
                return {'sha': 'official'}
            if path.startswith('search/repositories'):
                return {'items': [
                    {'full_name': 'diegoami/borg-rs', 'default_branch': 'main'},
                    {'full_name': 'diegoami/better-borg-c', 'default_branch': 'main'},
                    {'full_name': 'candidate/game', 'default_branch': 'main', 'pushed_at': 'date'}]}
            if path == 'repos/agoodman00/angband':
                return {'default_branch': 'do_not_use', 'pushed_at': 'date'}
            if path.startswith('repos/agoodman00/angband/branches'):
                return [{'name': 'borg1'}, {'name': 'other'}]
            if path.endswith('/commits/do_not_use') or path.endswith('/commits/borg1'):
                return {'sha': 'official'}
            if path == 'repos/candidate/game/commits/main':
                if broken:
                    raise RuntimeError('HTTP failure')
                return {'sha': 'candidate'}
            if '/contents/src/borg?' in path:
                if 'candidate/game' in path and missing:
                    return None
                return [{'type': 'file', 'name': 'borg.c', 'sha': 'new' if changed and 'candidate/game' in path else 'same'}]
            if '/commits?' in path:
                return [{'sha': 'last', 'commit': {'author': {'date': 'date'}}}]
            if path.startswith('repos/angband/angband/pulls?'):
                return []
            if path.startswith('search/issues'):
                return {'items': [{'title': 'Fix | text\nnot instructions', 'html_url': 'https://github.com/angband/angband/pull/1', 'number': 1}]}
            raise AssertionError(path)
        return get, calls

    def test_same_blobs_are_not_a_better_borg_claim_and_exclusions_are_respected(self):
        get, calls = self.transport()
        r = review.collect(1, get)
        self.assertTrue(r['complete'])
        self.assertEqual(len(r['candidates']), 3)
        self.assertTrue(all(not c['changed_borg_files'] for c in r['candidates']))
        self.assertFalse(any('repos/diegoami/borg-rs' in x for x in calls))
        self.assertFalse(any('repos/diegoami/better-borg-c' in x for x in calls))
        self.assertIn('do not prove better play', review.markdown(r))

    def test_different_file_is_a_lead_not_a_ready_fix(self):
        get, _ = self.transport(changed=True)
        r = review.collect(1, get)
        c = next(x for x in r['candidates'] if x['repository'] == 'candidate/game')
        self.assertEqual(c['changed_borg_files'], ['borg.c'])
        self.assertIn('needs semantic review', c['status'])
        self.assertIn('src/borg/borg.c', review.markdown(r))

    def test_legacy_missing_path_is_explicitly_uninspected(self):
        get, _ = self.transport(missing=True)
        r = review.collect(1, get)
        c = next(x for x in r['candidates'] if x['repository'] == 'candidate/game')
        self.assertIsNone(c['changed_borg_files'])
        self.assertIn('manual check', c['status'])

    def test_untrusted_titles_do_not_create_mentions_or_markup(self):
        value = review.cell('@someone | [label] `code`\nnext')
        self.assertNotIn('@someone', value)
        self.assertIn('\\[label\\]', value)
        self.assertNotIn('\n', value)

    def test_api_types_override_search_query_and_open_prs_are_read_directly(self):
        fallback, _ = self.transport()
        def get(path, optional=False):
            if path.startswith('search/issues'):
                return {'items': [
                    {'title': 'Borg death issue', 'html_url': 'https://github.com/angband/angband/issues/6515', 'number': 6515},
                    {'title': 'Borg reset PR', 'html_url': 'https://github.com/angband/angband/pull/6808', 'number': 6808,
                     'pull_request': {'url': 'https://api.github.com/repos/angband/angband/pulls/6808'}}]}
            if path.startswith('repos/angband/angband/pulls?'):
                return [{'title': 'Borg swap PR', 'html_url': 'https://github.com/angband/angband/pull/6809', 'number': 6809, 'body': ''}]
            return fallback(path, optional)
        r = review.collect(1, get)
        self.assertEqual({x['number'] for x in r['official_borg_prs']}, {6808, 6809})
        self.assertEqual([x['number'] for x in r['official_borg_issues']], [6515])
        text = review.markdown(r)
        pr_section = text.split('### Open official Borg PR leads')[1].split('### Open official Borg issue leads')[0]
        self.assertNotIn('/issues/6515', pr_section)
        self.assertIn('/pull/6809', pr_section)

    def test_read_failure_remains_partial(self):
        get, _ = self.transport(broken=True)
        r = review.collect(1, get)
        self.assertFalse(r['complete'])
        self.assertEqual(r['errors'][0]['repository'], 'candidate/game')
        self.assertIn('Partial/error', review.markdown(r))


if __name__ == '__main__':
    unittest.main()
