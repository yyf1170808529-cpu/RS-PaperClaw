"""Guard the two UTC schedules and their full/recovery routing."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import unittest


class MaritimeScheduleTests(unittest.TestCase):
    def test_utc_schedules_and_beijing_day_rollover(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    '.github/workflows/maritime-no-api.yml').read_text(encoding='utf-8')
        schedules = re.findall(r"^\s+- cron: '([^']+)'", workflow, re.MULTILINE)
        self.assertEqual(schedules, ['20 23 * * *', '20 4 * * *'])
        beijing = timezone(timedelta(hours=8))
        for cron, expected in zip(schedules, ['2026-10-20 07:20', '2026-10-19 12:20']):
            minute, hour, *_ = cron.split()
            utc = datetime(2026, 10, 19, int(hour), int(minute), tzinfo=timezone.utc)
            self.assertEqual(utc.astimezone(beijing).strftime('%Y-%m-%d %H:%M'), expected)

    def test_resume_routes_only_recovery_schedule_and_manual_resume(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    '.github/workflows/maritime-no-api.yml').read_text(encoding='utf-8')
        condition = re.search(r"RS_RESUME_ONLY: \$\{\{ (.+) \}\}", workflow).group(1)
        self.assertEqual(condition,
                         "(inputs.resume || github.event.schedule == '20 4 * * *') && '1' || '0'")
        recovery = re.search(r"github.event.schedule == '([^']+)'", condition).group(1)
        for manual_resume, schedule, expected in [
            (False, '20 23 * * *', False), (False, '20 4 * * *', True),
            (False, '', False), (True, '', True),
        ]:
            self.assertEqual(manual_resume or schedule == recovery, expected)
        self.assertIn('workflow_dispatch:', workflow)


if __name__ == '__main__':
    unittest.main()
