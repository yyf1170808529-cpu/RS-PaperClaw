import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services.mobile_digest import render_mobile_page, refresh_mobile_pages, build_mobile_digest


def paper(key,title):
    return {'paper_id':key,'title':title,'source':'arXiv','level':'方法值得关注','reason':'摘要证据',
            'abstract':'Full original abstract for '+title,'abstract_zh':'中文','original_url':'https://arxiv.org/abs/'+key,
            'reading_url':'https://example.org/maritime.html?paper='+key}


class MobilePromptTests(unittest.TestCase):
    def test_future_digest_keeps_prompt_metadata_for_every_selected_paper(self):
        from datetime import date
        import test_maritime_v3_7 as fixtures
        from services import semantic_evaluation as ai
        fixture=fixtures.DailyStrictTests();fixture.config=ai.settings()
        selected=[fixture.make(f'2610.{31000+i}','2026-10-20') for i in range(5)]
        with tempfile.TemporaryDirectory() as directory:
            payload=build_mobile_digest(Path(directory),{'papers':{p['paper_id']:p for p in selected}},date(2026,10,20))
            self.assertEqual(len(payload['papers']),5)
            for saved in payload['papers']:
                original=next(p for p in selected if p['paper_id']==saved['paper_id'])
                for field in ('authors','published','arxiv_url','pdf_url','abstract'):
                    self.assertEqual(saved[field],original[field])
            page=(Path(directory)/'docs/maritime-daily.html').read_text(encoding='utf8')
            self.assertEqual(page.count('data-prompt-paper='),5)

    def test_archives_enrich_only_matching_identity_and_keep_original_full_abstract(self):
        a=paper('2610.01750','FFBL-Coop');b=paper('doi:10.1234/snap','SNAP')
        master={a['paper_id']:{**a,'authors':['Alice','Bob'],'published':'2026-10-02','pdf_url':'https://arxiv.org/pdf/2610.01750','abstract':'Newer text must not replace archived text'},
                '2610.09700':{**b,'authors':['Carol'],'published':'2026-10-13','doi':'10.1234/snap','arxiv_url':'https://arxiv.org/abs/2610.09700','reading':{'analysis':'PRIVATE'}}}
        payload={'date':'2026-10-20','papers':[a,b]}
        text=render_mobile_page(payload,{b['paper_id']:'2610.09700'},master)
        data=json.loads(re.search(r'<script id="daily-prompt-data" type="application/json">(.*?)</script>',text).group(1))
        self.assertEqual(text.count('data-prompt-paper='),2)
        self.assertEqual(data['papers'][0]['authors'],['Alice','Bob'])
        self.assertEqual(data['papers'][1]['authors'],['Carol'])
        self.assertEqual(data['papers'][0]['abstract'],a['abstract'])
        self.assertEqual(data['papers'][1]['doi'],'10.1234/snap')
        template=(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts/prompts/maritime_analysis.md').read_text(encoding='utf8')
        self.assertEqual(data['prompt_template'],template)
        self.assertNotIn('PRIVATE',text)

    def test_missing_archive_identity_does_not_borrow_another_papers_metadata(self):
        a=paper('2610.01750','Missing')
        text=render_mobile_page({'date':'2026-10-20','papers':[a]},papers={'2610.09700':{'authors':['Wrong author'],'pdf_url':'https://wrong.org/p.pdf'}})
        self.assertNotIn('Wrong author',text);self.assertNotIn('wrong.org',text)
        self.assertIn('data-prompt-paper="2610.01750"',text)

    def test_rebuild_saved_pages_preserves_json_and_relative_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'docs/maritime-data/mobile';folder.mkdir(parents=True)
            payload={'date':'2026-10-20','papers':[paper('2610.01750','Title </script>')],'publication_status':'complete'}
            saved=json.dumps(payload)
            for name in ('2026-10-20.json','latest.json'):(folder/name).write_text(saved,encoding='utf8')
            self.assertEqual(refresh_mobile_pages(root,{'papers':{}}),1)
            self.assertEqual((folder/'2026-10-20.json').read_text(encoding='utf8'),saved)
            self.assertEqual((folder/'latest.json').read_text(encoding='utf8'),saved)
            page=(folder/'2026-10-20.html').read_text(encoding='utf8')
            for script in ('maritime_favorites.js','maritime_prompt.js','maritime_daily_prompt.js'):
                self.assertIn('src="../../'+script,page)
            self.assertNotIn('Title </script>',page)
            self.assertIn('data-prompt-paper=',(root/'docs/maritime-daily.html').read_text(encoding='utf8'))


if __name__=='__main__':unittest.main()
