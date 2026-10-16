import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/rs-paper-pipeline/scripts'))
from services.mobile_digest import render_mobile_page


class FavoritePageTests(unittest.TestCase):
    def test_render_saved_picks_uses_shared_versioned_module_and_public_snapshots_only(self):
        paper={'paper_id':'2610.01750','title':'Title </script><script>bad()</script>',
               'source':'arXiv','level':'方法值得关注','ai_score':47,'selection_source':'近期候选',
               'reason':'摘要证据','abstract':'English','abstract_zh':'中文摘要','original_url':'https://arxiv.org/abs/2610.01750',
               'reading_url':'https://example.org/maritime.html?paper=2610.01750','note':'PRIVATE_TEST_NOTE'}
        with patch('services.mobile_digest.select_daily',side_effect=AssertionError('Must not reselect')),patch('clients.deepseek_client.complete',side_effect=AssertionError('Must not call API')):
            html=render_mobile_page({'date':'2026-10-15','papers':[paper]},{'doi:10.1234/a':'2610.01750'})
        self.assertIn('maritime_favorites.js?v=3.7.2.2',html)
        self.assertIn('data-favorite-paper="2610.01750"',html)
        self.assertIn('doi:10.1234/a',html)
        self.assertNotIn('PRIVATE_TEST_NOTE',html)
        self.assertNotIn('</script><script>bad()',html)
        self.assertNotIn('localStorage',html)
        self.assertIn('view=favorites&amp;v=3.7.2.2">我的收藏</a>',html)
        self.assertIn('收藏模块加载中',html)

    def test_reading_page_loads_same_version_before_library_script(self):
        html=(Path(__file__).resolve().parents[1]/'docs/maritime.html').read_text(encoding='utf8')
        self.assertLess(html.index('maritime_favorites.js?v=3.7.2.2'),html.index('maritime.js?v=3.7.2.2'))
        self.assertIn('id="favorite-tools"',html)
        self.assertIn('view=favorites&amp;v=3.7.2.2">我的收藏</a>',html)


if __name__=='__main__':unittest.main()
