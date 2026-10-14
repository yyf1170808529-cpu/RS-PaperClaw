import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services import abstract_quality as aq, maritime as m, maritime_v2 as v, maritime_sync as sync
from services.mobile_digest import build_mobile_digest
from test_maritime_v2 import paper

class RepairTests(unittest.TestCase):
    def polluted(self):
        return 'This paper studies distributed target tracking and data association with simulation. '*4+'References1. Dalian Maritime University, Ship Detection. 2024. https://doi.org/10.1234/a.2. B Author. 2023. https://doi.org/10.1234/b.3. C Author. 2022.'
    def test_structural_cut_and_one_references_word_not_cut(self):
        result=aq.inspect_abstract(self.polluted())
        self.assertEqual(result['status'],'cleaned')
        self.assertNotIn('Maritime',result['clean'])
        text='Our model references earlier tracking models and improves visual association. '*3
        self.assertEqual(aq.inspect_abstract(text)['clean'],text)
        self.assertEqual(aq.inspect_abstract('a'*6100)['status'],'review')
    def test_stale_machine_and_manual_preserved_idempotently(self):
        p={'abstract':self.polluted(),'translation':{'status':'machine','zh':'old references','english_hash':'old'}}
        aq.apply_quality(p)
        self.assertEqual(p['translation']['status'],'stale')
        self.assertEqual(p['translation']['zh'],'')
        snapshot=copy.deepcopy(p)
        aq.apply_quality(p)
        self.assertEqual(snapshot,p)
        p={'abstract':self.polluted(),'translation':{'status':'manual','zh':'user edits'}}
        aq.apply_quality(p)
        self.assertEqual(p['translation']['zh'],'user edits')
    def test_scene_and_journal_quality_are_independent(self):
        p=paper(title='Ship detection for coastal monitoring')
        lib={'papers':{p['arxiv_id']:p},'days':{}}
        v.normalize_library(lib,m.load_maritime_assets())
        self.assertEqual(p['application_bucket'],'water')
        self.assertNotEqual(p['recommendation']['bucket'],'water')
        p=paper(title='Distributed target tracking',abstract=self.polluted())
        lib={'papers':{p['arxiv_id']:p},'days':{}}
        v.normalize_library(lib,m.load_maritime_assets())
        self.assertNotEqual(p['application_bucket'],'water')
    def test_allowlist_excludes_private_and_code(self):
        cfg=json.loads((v.CONFIG_DIR/'publication.json').read_text())
        for path in ['papers/maritime/private/paper.pdf','.env','skills/a.py','docs/maritime.js','log.log']:
            self.assertFalse(sync.allowed(path,cfg))
        self.assertTrue(sync.allowed('docs/maritime-data/mobile/latest.json',cfg))

    def test_sync_stops_for_dirty_code_or_remote_updates_without_add_or_push(self):
        from types import SimpleNamespace
        config=(v.CONFIG_DIR/'publication.json').read_text(encoding='utf8')
        for dirty,advanced in [(' M skills/example.py\x00',False),('',True)]:
            calls=[]
            def run(command,**kwargs):
                args=command[1:]; calls.append(args)
                out=''
                if args[:2]==['remote','get-url']:out='https://github.com/yyf1170808529-cpu/RS-PaperClaw.git\n'
                elif args[:2]==['branch','--show-current']:out='main\n'
                elif args[:1]==['status']:out=dirty
                elif args[:1]==['rev-parse']:out='remote\n' if advanced and args[1].startswith('origin/') else 'local\n'
                return SimpleNamespace(returncode=0,stdout=out,stderr='')
            with tempfile.TemporaryDirectory() as directory,patch.dict('os.environ',{'RS_PROXY_URL':'','HTTPS_PROXY':''}),patch.object(sync.subprocess,'run',side_effect=run):
                root=Path(directory); target=root/'skills/rs-paper-pipeline/scripts/config/maritime/publication.json'
                target.parent.mkdir(parents=True);target.write_text(config,encoding='utf8')
                result=sync.sync(root,0)
            self.assertEqual(result['github_sync'],'stopped')
            self.assertFalse(any(a[0] in ('add','commit','push','reset','rebase') for a in calls))
    def test_digest_small_stable_and_previous_day_excluded(self):
        from datetime import date
        p=paper(title='Ship detection')
        p['published']=p['publication_date']='2026-10-13'
        p.update(paper_id=p['arxiv_id'],recommendation={'bucket':'water'},quality={'high_journal':True},resource_type='journal_article')
        lib={'papers':{p['paper_id']:p},'days':{}}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'docs').mkdir()
            first=build_mobile_digest(root,lib,date(2026,10,14))
            self.assertEqual(first,build_mobile_digest(root,lib,date(2026,10,14)))
            self.assertEqual(len(first['papers']),1)
            self.assertEqual(build_mobile_digest(root,lib,date(2026,10,15))['papers'],[])
            html=(root/'docs/maritime-daily.html').read_text(encoding='utf8')
            self.assertNotIn('library.json',html)
            self.assertIn('查看摘要',html)

if __name__=='__main__':unittest.main()
