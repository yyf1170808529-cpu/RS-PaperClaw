import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/rs-paper-pipeline/scripts'))
from services import maritime as m, maritime_v2 as v, maritime_reading as reading, maritime_update as update
from clients import scholarly_client as scholarly, publisher_abstract as publisher
from test_maritime_v2 import paper


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.rules=m.load_maritime_assets()
        self.formal={**paper(title='Maritime object detection'), 'arxiv_id':None, 'paper_id':'doi:10.1234/test', 'doi':'10.1234/test',
                     'venue':'Test Journal','venue_type':'journal','publication_status':'published','metadata_source':['Crossref'],
                     'publication_evidence':{'source':'Crossref','url':'https://api.crossref.org/works/10.1234/test','type':'journal-article'}}

    def test_regular_arxiv_path_and_other_sources_use_same_merge(self):
        for source in ['arxiv','crossref','openalex']:
            pre=paper(title='Maritime object detection')
            pre.update(paper_id=pre['arxiv_id'],reading={'state':'已精读','analysis':'keep'},translation={'status':'manual','zh':'保留'})
            lib={'schema_version':2,'papers':{pre['paper_id']:copy.deepcopy(pre)},'days':{}}
            if source=='arxiv':
                lib['papers']={self.formal['paper_id']:{**self.formal,'reading':pre['reading'],'translation':pre['translation']}}
                m.merge_candidates(lib,[pre],['2026-10-10'],self.rules,['A'])
            else:
                record={**self.formal,'metadata_source':[source.title() if source=='crossref' else 'OpenAlex']}
                v.merge_records(lib,[record],self.rules)
            self.assertEqual(len(lib['papers']),1)
            saved=next(iter(lib['papers'].values()))
            self.assertEqual(saved['publication_status'],'published')
            self.assertEqual(saved['reading']['analysis'],'keep')
            self.assertEqual(saved['translation']['zh'],'保留')
            self.assertTrue(saved['arxiv_id'])
            self.assertEqual(saved['doi'],'10.1234/test')

    def test_publisher_identity_license_and_not_description_or_other_article(self):
        text='This is the exact scientific abstract about maritime perception and sensor fusion. '*3
        node={'@type':'ScholarlyArticle','identifier':'https://doi.org/10.1234/test','headline':self.formal['title'],
              'abstract':text,'license':'https://creativecommons.org/licenses/by/4.0/'}
        page=lambda n:'<script type="application/ld+json">'+json.dumps(n)+'</script>'
        result=publisher.extract_metadata(page(node),self.formal)
        self.assertTrue(result['public_allowed'])
        self.assertEqual(result['abstract'],text.strip())
        self.assertFalse(publisher.extract_metadata(page({**node,'license':'All rights reserved'}),self.formal)['public_allowed'])
        self.assertFalse(publisher.extract_metadata(page({**node,'license':'Not licensed under https://creativecommons.org/licenses/by/4.0/'}),self.formal)['public_allowed'])
        for change in [{'identifier':'10.1234/other'},{'headline':'Another article'},{'abstract':'','description':text}]:
            with self.assertRaises(ValueError):publisher.extract_metadata(page({**node,**change}),self.formal)

    @patch.object(scholarly,'openalex_key',return_value=None)
    @patch.object(scholarly.urllib.request,'urlopen')
    def test_anonymous_budget_pauses_after_one_request_across_calls(self, urlopen, key):
        body=json.dumps({'message':'Insufficient budget; shared IP anonymous daily budget exhausted'}).encode()
        urlopen.side_effect=HTTPError('https://api.openalex.org/works',429,'Too Many Requests',{},io.BytesIO(body))
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(scholarly.OpenAlexLimited):scholarly.json_request('https://api.openalex.org/works',root=Path(root),retries=5)
            with self.assertRaises(scholarly.OpenAlexLimited):scholarly.json_request('https://api.openalex.org/works',root=Path(root),retries=5)
            self.assertEqual(urlopen.call_count,1)
            text=(Path(root)/'papers/maritime/private/openalex-cooldown.json').read_text()
            self.assertIn('budget_exhausted',text)

    @patch.object(scholarly,'openalex_key',return_value='secret-free-key')
    @patch.object(scholarly.urllib.request,'urlopen')
    def test_free_key_sent_in_header_not_url_or_cache(self, urlopen, key):
        response=unittest.mock.MagicMock()
        response.__enter__.return_value=response
        response.read.return_value=b'{}'
        # json.load uses read on this response.
        urlopen.return_value=response
        with tempfile.TemporaryDirectory() as root:
            scholarly.json_request('https://api.openalex.org/works',root=Path(root))
            req=urlopen.call_args.args[0]
            self.assertEqual(req.get_header('Authorization'),'Bearer secret-free-key')
            self.assertNotIn('secret-free-key',req.full_url)
            for p in Path(root).rglob('*.json'):self.assertNotIn('secret-free-key',p.read_text())

    def test_history_priority_and_no_model_call_for_missing_or_cached(self):
        a={**paper(),'paper_id':'a','assessment':{'level':'high'},'quality':{'high_journal':True}}
        b={**paper(),'paper_id':'b','assessment':{'level':'general'},'quality':{}}
        self.assertEqual(reading.translation_order({'papers':{'a':a,'b':b}})[0],'a')
        lib={'papers':{'a':{**a,'abstract':''},'b':{**b,'translation':{'status':'manual','zh':'保留'}}}}
        with patch.object(update,'_translation_worker',side_effect=AssertionError('Model should not run')):
            counts=update.translate_budget(lib,['a','b'],25,10,lambda:None,retry_failed=False)
        self.assertEqual(counts['missing_english'],1)
        self.assertEqual(counts['manual'],1)

    def test_suspected_duplicates_not_forced_and_audit_repeat_safe(self):
        a={**self.formal,'arxiv_id':'2610.00001','paper_id':'2610.00001'}
        b={**self.formal,'doi':'10.1234/another','paper_id':'doi:10.1234/another'}
        lib={'papers':{'2610.00001':a,b['paper_id']:b},'days':{}}
        result=v.deduplicate_library(lib,self.rules)
        self.assertEqual(result['merged'],0)
        self.assertEqual(len(result['suspected']),1)
        self.assertEqual(v.deduplicate_library(lib,self.rules)['merged'],0)

    def test_openalex_null_title_and_author_do_not_crash_or_merge_by_title(self):
        record=scholarly.openalex_paper({'id':'https://openalex.org/W123','title':None,'display_name':None,
                                      'authorships':[{'author':{'display_name':None}}]})
        self.assertEqual(record['title'],'')
        self.assertEqual(record['authors'],[''])
        self.assertEqual(v.normalized_identity(None),'')
        self.assertFalse(v.same_title_authors({**self.formal,'authors':[None]},self.formal))
        lib={'papers':{self.formal['paper_id']:copy.deepcopy(self.formal)},'days':{}}
        v.merge_records(lib,[record],self.rules)
        self.assertEqual(len(lib['papers']),2)


if __name__=='__main__':unittest.main()
