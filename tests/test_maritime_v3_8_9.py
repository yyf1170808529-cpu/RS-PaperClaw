import unittest,sys,tempfile,json
from pathlib import Path
from unittest.mock import patch
from datetime import date
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services import adaptive_discovery as a
from services.domain_exclusion import exclusion
class RecoveryTests(unittest.TestCase):
 def test_shortage_rounds(self):
  for initial,counts in [(5,[]),(4,[5]),(2,[5]),(2,[4,4]),(0,[0,0])]:
   with self.subTest(initial=initial),tempfile.TemporaryDirectory() as d:
    values=iter([initial,initial]+sum(([initial,n] for n in counts),[]));last=[initial]
    def count(*args):
     try:last[0]=next(values)
     except StopIteration:pass
     return last[0]
    args=SimpleNamespace(root=Path(d),translation_timeout=1,timeout=1,no_ai=True)
    with patch.object(a,'complete_count',side_effect=count),patch.object(a,'jobs_for',return_value=[]),patch('services.semantic_evaluation.daily_evaluate',return_value={}),patch('services.selected_translation.translate_selected',return_value={}):
     rows=a.recover(args,{'papers':{}},{},date(2026,11,8),lambda:None)
    self.assertEqual(len(rows),len(counts))
 def test_cursor_changes_between_runs_and_domain_gates(self):
  lib={'papers':{}};v={'journals':[]};c=a.settings();one=a.jobs_for(Path('.'),lib,v,0,c);two=a.jobs_for(Path('.'),lib,v,0,c);self.assertNotEqual(one,two)
  for title in ['Perception-Aware Communication Middleware for Distributed Visual Perception','Benchmarking 4D Radar for Ego-Trajectory Planning']:self.assertTrue(exclusion({'title':title}))
 def test_anonymous_openalex_has_no_cursor(self):
  from clients.scholarly_client import fetch_openalex
  with patch('clients.scholarly_client.openalex_key',return_value=None),patch('clients.scholarly_client.json_request',return_value={'results':[],'meta':{}}) as request:
   self.assertEqual(fetch_openalex('2026-01-01','2026-11-08','vision',None),([],True));self.assertNotIn('cursor',request.call_args.args[1])
