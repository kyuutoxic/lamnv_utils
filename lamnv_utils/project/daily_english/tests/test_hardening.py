import hashlib
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import TransactionCase, tagged

from ..models.english_lesson import LESSON_FIELDS


@tagged('post_install', '-at_install')
class TestEnglishHardening(TransactionCase):

    def setUp(self):
        super().setUp()
        commit = patch.object(
            type(self.env['ir.cron']), '_commit_progress', return_value=60,
        )
        commit.start()
        self.addCleanup(commit.stop)
        self.config = self.env.ref('daily_english.configuration_default')
        self.config.write({
            'telegram_token': 'test-token', 'enabled': True,
            'daily_ai_enabled': True, 'daily_ai_auto_approve': True,
            'daily_api_limit': 30,
        })
        self.learner = self.env['english.learner'].create({
            'curriculum_enabled': False,
            'name': 'Hardening', 'chat_id': '991122',
            'bot_hash': hashlib.sha256(b'test-token').hexdigest(),
            'send_hour': 0,
        })
        self.jobs = self.env['english.job']
        self.outbox = self.env['english.delivery']

    def result(self, batch=False):
        seed = self.env.ref('daily_english.lesson_intro')
        values = {key: seed[key] for key in LESSON_FIELDS}
        values['sample_answers'] = 'I am Lan. — Tôi là Lan.'
        if not batch:
            return values
        result = {}
        for n in range(1, 6):
            for key, value in values.items():
                result[f'q{n}_{key}'] = value
            result[f'q{n}_exercise'] = f'Dịch: Tôi có {n} cuốn sách.'
            result[f'q{n}_answer'] = f'I have {n} books.'
        return result

    def test_correction_is_assistance_not_recall(self):
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        attempt = self.env['english.attempt'].create({
            'progress_id': progress.id, 'answer_text': 'Wrong',
        })
        attempt._finish(False, 'Sửa lại nhé.')
        self.assertTrue(progress.answer_shown)
        progress._submit(progress.lesson_id.answer)
        self.assertEqual(progress.review_step, 0)
        self.assertEqual(self.learner.session_correct, 0)
        self.assertEqual(self.learner.current_session_id.errors, 1)

    def test_seed_render_hides_exercise_answers(self):
        for lesson in self.env['english.lesson'].search([
            ('generated', '=', False), ('unit_id', '=', False),
        ]):
            self.assertNotIn(lesson.answer, lesson._render())

    def test_next_day_reminds_unfinished_question_once(self):
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        before = self.outbox.search_count([])
        self.learner._cron_daily()
        self.assertGreater(self.outbox.search_count([]), before)
        after = self.outbox.search_count([])
        self.learner._cron_daily()
        self.assertEqual(self.outbox.search_count([]), after)
        self.assertEqual(self.learner.current_progress_id, progress)

    def test_stop_cancels_queued_generation_and_outbox(self):
        self.learner._begin_session()
        self.learner.action_generate_lesson()
        old = self.outbox.search([])
        self.learner._handle_text('/stop')
        with patch.object(type(self.config), '_gemini') as generate:
            self.jobs._cron_process()
        generate.assert_not_called()
        self.assertEqual(set(old.mapped('state')), {'skipped'})
        self.assertEqual(self.learner.current_session_id.state, 'stopped')

    def test_stop_during_ai_discards_result(self):
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        progress._submit('Something different')

        def reply(*args):
            self.learner._handle_text('/stop')
            return {
                'correct': True, 'feedback': 'Good',
                'corrected_answer': progress.lesson_id.answer,
            }, 10

        with patch.object(type(self.config), '_gemini', side_effect=reply):
            self.jobs._cron_process()
        self.assertEqual(progress.state, 'awaiting')
        self.assertFalse(progress.attempt_ids.graded)
        self.assertEqual(self.jobs.search([], limit=1).state, 'skipped')

    def test_skip_while_grading_discards_late_result(self):
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        progress._submit('Something different')

        def reply(*args):
            self.learner._handle_text('/skip')
            return {
                'correct': True, 'feedback': 'Good',
                'corrected_answer': progress.lesson_id.answer,
            }, 10

        with patch.object(type(self.config), '_gemini', side_effect=reply):
            self.jobs._cron_process()
        self.assertEqual(progress.review_step, 0)
        self.assertEqual(self.learner.session_count, 1)
        self.assertNotEqual(self.learner.current_progress_id, progress)

    def test_quota_opens_question_and_explains(self):
        self.config.daily_api_limit = 1
        self.env['english.api.usage'].create({})
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        progress._submit('Different')
        with patch.object(type(self.config), '_gemini') as generate:
            self.jobs._cron_process()
        generate.assert_not_called()
        self.assertEqual(progress.state, 'awaiting')
        self.assertEqual(self.jobs.search([], limit=1).error_code,
                         'daily_quota')
        text = self.outbox.search([], order='id desc', limit=1).text
        self.assertIn('hết lượt AI', text)
        self.learner._handle_text('/skip')
        self.assertEqual(self.learner.session_count, 1)

    def test_daily_batch_is_unique_and_not_sent_early(self):
        day = self.learner._local_date()
        plan = self.learner._daily_plan(day)
        self.assertEqual(self.learner._daily_plan(day), plan)
        self.assertEqual(self.jobs.search_count([]), 1)
        with patch.object(type(self.config), '_gemini', return_value=(
            self.result(batch=True), 100,
        )):
            self.jobs._cron_process()
        self.assertEqual(len(plan.lesson_ids), 5)
        self.assertTrue(plan.generation_done)
        self.assertFalse(self.outbox.search([]))
        self.assertEqual(set(plan.lesson_ids.mapped('state')), {'ready'})
        self.learner._begin_session(planned=plan)
        self.assertIn(self.learner.current_progress_id.lesson_id,
                      plan.lesson_ids)

    def test_preparation_window_and_stop_not_regenerated(self):
        self.learner.write({'send_hour': 8, 'send_minute': 0})
        with patch.object(fields.Datetime, 'now', return_value=(
            fields.Datetime.to_datetime('2026-10-11 00:29:00')
        )):
            self.learner._cron_prepare()
        self.assertFalse(self.jobs.search([]))
        with patch.object(fields.Datetime, 'now', return_value=(
            fields.Datetime.to_datetime('2026-10-11 00:30:00')
        )):
            self.learner._cron_prepare()
            self.learner._cron_prepare()
            self.assertEqual(self.jobs.search_count([]), 1)
            self.learner._handle_text('/stop')
            self.learner._cron_prepare()
            self.assertEqual(self.jobs.search_count([]), 1)

    def test_session_history_survives_new_session(self):
        self.learner._begin_session()
        first = self.learner.current_session_id
        self.learner._handle_text('/skip')
        self.learner._handle_text('/stop')
        self.learner._begin_session()
        self.assertNotEqual(first, self.learner.current_session_id)
        self.assertEqual(first.skipped, 1)
        self.assertEqual(first.state, 'stopped')
        self.assertEqual(self.learner.current_session_id.count, 0)

    def test_cleanup_keeps_pending_history_and_receipts(self):
        old = fields.Datetime.now() - timedelta(days=90)
        sent = self.learner._reply('Old sent')
        sent.state = 'sent'
        pending = self.learner._reply('Old pending')
        receipt = self.env['english.update'].create({
            'update_id': 9911, 'bot_hash': 'test-hash',
        })
        self.env.flush_all()
        self.env.cr.execute(
            'UPDATE english_delivery SET write_date = %s '
            'WHERE id IN %s', [old, (sent.id, pending.id)],
        )
        self.env['english.session']._cron_cleanup()
        self.assertFalse(sent.exists())
        self.assertTrue(pending.exists())
        self.assertTrue(receipt.exists())

    def test_duplicate_ai_questions_rejected_atomically(self):
        plan = self.learner._daily_plan(self.learner._local_date())
        result = self.result(batch=True)
        result['q2_exercise'] = result['q1_exercise']
        with patch.object(type(self.config), '_gemini', return_value=(
            result, 100,
        )):
            self.jobs._cron_process()
        self.assertFalse(plan.lesson_ids)
        self.assertFalse(self.env['english.lesson'].search([
            ('generated_for_id', '=', self.learner.id),
        ]))

    def test_answer_viewed_while_ai_running_prevents_recall(self):
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        progress._submit('An equivalent answer')

        def reply(*args):
            self.learner._handle_text('/answer')
            return {
                'correct': True, 'feedback': 'Good',
                'corrected_answer': progress.lesson_id.answer,
            }, 10

        with patch.object(type(self.config), '_gemini', side_effect=reply):
            self.jobs._cron_process()
        self.assertEqual(progress.review_step, 0)
        self.assertEqual(self.learner.session_correct, 0)

    def test_expired_worker_recovery_is_bounded(self):
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        progress._submit('Something different')
        job = self.jobs.search([], limit=1)
        job.write({
            'state': 'running', 'calls': 3,
            'next_run': fields.Datetime.now() - timedelta(minutes=1),
        })
        with patch.object(type(self.config), '_gemini') as generate:
            self.jobs._cron_process()
        generate.assert_not_called()
        self.assertEqual(job.state, 'failed')
        self.assertEqual(progress.state, 'awaiting')

    def test_daily_generation_failure_uses_ready_fallback(self):
        plan = self.learner._daily_plan(self.learner._local_date())
        self.config.daily_api_limit = 1
        self.env['english.api.usage'].create({})
        self.jobs._cron_process()
        self.assertEqual(plan.state, 'failed')
        self.learner._cron_daily()
        self.assertEqual(self.learner.current_session_id, plan)
        self.assertTrue(self.learner.current_progress_id)

    def test_auto_approval_can_be_disabled_for_daily_batch(self):
        self.config.daily_ai_auto_approve = False
        plan = self.learner._daily_plan(self.learner._local_date())
        with patch.object(type(self.config), '_gemini', return_value=(
            self.result(batch=True), 100,
        )):
            self.jobs._cron_process()
        self.assertEqual(set(plan.lesson_ids.mapped('state')), {'draft'})
        self.learner._begin_session(planned=plan)
        self.assertNotIn(self.learner.current_progress_id.lesson_id,
                         plan.lesson_ids)

    def test_completed_history_and_pending_generation_survive_cleanup(self):
        self.learner._begin_session()
        plan = self.learner.current_session_id
        self.learner._handle_text('/stop')
        day = self.learner._local_date() + timedelta(days=1)
        self.learner._daily_plan(day)
        self.env['english.session']._cron_cleanup()
        self.assertTrue(plan.exists())
        self.assertTrue(self.jobs.search([('state', '=', 'pending')]))

    def test_changed_bot_between_parts_stops_delivery(self):
        delivery = self.learner._reply('x' * 5000)

        def send(*args):
            self.config.telegram_token = 'another-test-bot'
            return {}

        with patch.object(
            type(self.config), '_telegram', side_effect=send,
        ) as api:
            self.outbox._cron_send()
        self.assertEqual(api.call_count, 1)
        self.assertEqual(delivery.state, 'skipped')
        self.assertEqual(delivery.next_part, 1)

    def test_stop_keeps_tomorrows_plan(self):
        tomorrow = self.learner._local_date() + timedelta(days=1)
        plan = self.learner._daily_plan(tomorrow)
        job = self.jobs.search([('session_id', '=', plan.id)])
        self.learner._begin_session()
        self.learner._handle_text('/stop')
        self.assertEqual(plan.state, 'preparing')
        self.assertEqual(job.state, 'pending')
        self.assertEqual(job.command_epoch, self.learner.command_epoch)

    def test_pause_resume_reuses_future_slot(self):
        tomorrow = self.learner._local_date() + timedelta(days=1)
        plan = self.learner._daily_plan(tomorrow)
        self.learner._handle_text('/pause')
        self.assertEqual(plan.state, 'stopped')
        self.learner._handle_text('/resume')
        self.assertEqual(plan.state, 'preparing')
        self.assertEqual(self.jobs.search_count([
            ('session_id', '=', plan.id), ('state', '=', 'pending'),
        ]), 1)
        self.assertEqual(self.learner._daily_plan(tomorrow), plan)
