import copy
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services import semantic_evaluation as ai
from services.mobile_digest import build_mobile_digest
from test_maritime_v2 import paper


class PublicationGateTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads(ai.CONFIG.read_text(encoding='utf8'))
        self.p=paper(title='What Makes Synthetic Hard Negatives Work in Vision-Language Pretraining?')
        self.p.update(paper_id=self.p['arxiv_id'],published='2026-10-15',publication_date='2026-10-15',
                      abstract='We propose SNAP, which generates intra-modal hard negatives without the matched positive for vision-language contrastive learning.',
                      resource_type='preprint',recommendation={'bucket':'general'},quality={'high_journal':False})

    def attach(self,p,direct,transfer,path=None,confidence=.9,decision='候选'):
        value={'paper_id':p['paper_id'],'task_type':'Representation learning','direct_relevance':direct,
               'transferability':transfer,'method_evidence':[{'quote_en':'generates intra-modal hard negatives without the matched positive',
               'interpretation_zh':'具体困难负样本构造','inference':False}],
               'transfer_path':path,'limitations':[],'decision':decision,'reason_zh':'摘要给出具体方法','confidence':confidence}
        p['semantic']={'paper_id':p['paper_id'],'fingerprint':ai.fingerprint(p,self.config),'evaluation':value}

    def test_specific_transfer_path_can_publish_without_maritime_word(self):
        path={'source_quote_en':'generates intra-modal hard negatives without the matched positive',
              'target_task':'cross_modal_matching','adaptation_zh':'将视觉语言配对输入改为船舶视觉与AIS轨迹配对，并调整对比训练目标','inference':True}
        self.attach(self.p,2,4,path)
        self.assertEqual(ai.ranking_info(self.p)['path'],'transfer')
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(len(build_mobile_digest(Path(d),{'papers':{self.p['paper_id']:self.p},'days':{}},date(2026,10,15))['papers']),1)

    def test_vague_transfer_and_unassessed_do_not_fill_five(self):
        self.attach(self.p,2,4,None)
        self.assertFalse(ai.ranking_info(self.p)['eligible'])
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);lib={'papers':{self.p['paper_id']:self.p},'days':{}}
            self.assertEqual(build_mobile_digest(root,lib,date(2026,10,15))['papers'],[])
            self.p.pop('semantic')
            self.assertEqual(build_mobile_digest(root,lib,date(2026,10,15))['papers'],[])
            self.assertIsNone(ai.ranking_info(self.p)['score'])

    def test_robot_manipulation_low_ai_does_not_get_rule_priority(self):
        p=copy.deepcopy(self.p)
        p['title']='SimpleTouch: Vision-Language-Action for Tactile Robotic Manipulation'
        p['recommendation']['bucket']='land'
        self.attach(p,1,1,None,decision='不推荐')
        self.assertFalse(ai.ranking_info(p)['eligible'])

    def test_direct_ship_and_radar_ais_survive_missing_api(self):
        for title in ('Maritime infrared ship detection','Radar AIS target association'):
            p=copy.deepcopy(self.p);p['title']=title;p.pop('semantic',None)
            self.assertTrue(ai.ranking_info(p)['eligible'])
            self.assertIsNone(ai.ranking_info(p)['score'])

    def test_old_cache_version_is_invalid(self):
        old=copy.deepcopy(self.p);old['semantic']={'fingerprint':'old-schema','evaluation':{}}
        self.assertIsNone(ai.current_evaluation(old))


if __name__=='__main__':unittest.main()
