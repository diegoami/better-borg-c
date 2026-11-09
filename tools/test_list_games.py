"""list_games.py: collection listing, transcript filtering and replay commands."""
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('list_games_under_test', ROOT / 'list_games.py')
games = importlib.util.module_from_spec(spec)
spec.loader.exec_module(games)


class ListGames(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        art = self.root / 'artifacts/death-workflow'
        self.collection = art / 'collections/20990101T000000Z'
        (self.collection).mkdir(parents=True)
        (self.collection / 'collection.json').write_text('{}')
        self.dead = self.collection / 'game-001-seed-11'
        self.alive = self.collection / 'game-002-seed-12'
        for game, outcome, cause, turn in ((self.dead, 'death', 'a crow', 4199),
                                           (self.alive, 'wall_timeout', '(alive and well)', 900000)):
            (game / 'reports').mkdir(parents=True)
            (game / 'reports/summary.json').write_text(json.dumps(
                {'seed': int(game.name.rsplit('-', 1)[1]), 'outcome': outcome, 'cause': cause,
                 'character': 'Measure Test', 'turn': turn, 'level': 1, 'max_depth': 1}))
        case = self.root / 'docs/deaths/D0099-collected'
        case.mkdir(parents=True)
        (case / 'record.json').write_text(json.dumps(
            {'id': 'D0099', 'encounter_family': 'fam-1', 'attempts': [{'raw_directory': str(self.dead)}]}))
        (case / 'assessment.json').write_text('{}')
        branch = art / 'takeover/branches/B1'
        (branch / 'sessions/S1').mkdir(parents=True)
        (branch / 'branch.json').write_text(json.dumps({'original': str(self.dead), 'actual_turn': 3983}))
        (branch / 'sessions/S1/result.json').write_text(json.dumps({'outcome': 'saved'}))
        self.patches = [mock.patch.object(games.workflow, 'artifacts', return_value=art),
                        mock.patch.object(games.workflow, 'primary_root', return_value=self.root),
                        mock.patch.object(games.workflow, 'reviews', return_value={})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def run_main(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(games.main(list(argv)), 0)
        return out.getvalue()

    def test_latest_collection_lists_commands_and_links(self):
        text = self.run_main()
        self.assertIn('2 game(s)', text)
        rel = 'artifacts/death-workflow/collections/20990101T000000Z/game-001-seed-11'
        self.assertIn(f'./replay-borg.py {rel}   (opens at turn 4094', text)
        self.assertIn(f'./play-from-replay.py {rel} --from-turn <turn>|latest', text)
        self.assertIn('D0099 NOT reviewed; manual from 3983: saved', text)
        self.assertIn('--mark-reviewed D0099', text)
        self.assertIn('game-002-seed-12 --view-only', text)

    def test_pending_filters_to_unreviewed_deaths(self):
        data = json.loads(self.run_main('--pending', '--json'))
        self.assertEqual([e['case'] for e in data], ['D0099'])
        with mock.patch.object(games.workflow, 'reviews', return_value={'fam-1': {'reviewed': True}}):
            self.assertEqual(json.loads(self.run_main('--pending', '--json')), [])

    def test_transcript_file_selects_named_games(self):
        transcript = self.root / 'games_left.txt'
        transcript.write_text(f'Report:            {self.alive}/reports/summary.md\n')
        data = json.loads(self.run_main('--file', str(transcript), '--json'))
        self.assertEqual([e['seed'] for e in data], [12])


if __name__ == '__main__':
    unittest.main()
