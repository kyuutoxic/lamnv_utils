import hashlib
import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged

from ..models.english_delivery import split_message
from ..models.english_configuration import gemini_api_error
from ..models.english_lesson import LESSON_FIELDS


@tagged('post_install', '-at_install')
class TestDailyEnglish(TransactionCase):

    def setUp(self):
        super().setUp()
        commit = patch.object(
            type(self.env['ir.cron']), '_commit_progress', return_value=60,
        )
        commit.start()
        self.addCleanup(commit.stop)
        self.config = self.env.ref('daily_english.configuration_default')
        self.config.write({
            'require_approval': True,
            'telegram_token': 'test-only-token',
            'webhook_secret': 'test-only-secret-123456',
            'gemini_key': 'test-only-key',
            'gemini_model': 'gemini-2.5-flash',
            'gemini_api': 'generate_content',
        })
        self.bot_hash = hashlib.sha256(b'test-only-token').hexdigest()
        self.learner = self.env['english.learner'].create({
            'curriculum_enabled': False,
            'name': 'Test learner', 'chat_id': '123',
            'bot_hash': self.bot_hash,
        })
        self.outbox = self.env['english.delivery']
        self.jobs = self.env['english.job']
        self.updates = self.env['english.update']
        self.config_type = type(self.config)

    def update(self, text, update_id=1, chat=123):
        self.updates._process({
            'update_id': update_id,
            'message': {
                'chat': {'id': chat, 'type': 'private'},
                'from': {'id': chat}, 'text': text,
            },
        })

    def start(self):
        self.learner._start_lesson()
        return self.learner.current_progress_id

    def test_lesson_contains_samples_but_hides_exercise_answer(self):
        progress = self.start()
        text = self.outbox.search([], order='id desc', limit=1).text
        self.assertIn(progress.lesson_id.question, text)
        self.assertIn(progress.lesson_id.meaning_vi, text)
        self.assertNotIn(progress.lesson_id.answer, text)
        self.assertIn('Ví dụ minh họa', text)
        self.assertNotIn('Đáp án mẫu', text)
        self.learner._handle_text('/explain')
        text = self.outbox.search([], order='id desc', limit=1).text
        self.assertIn(progress.lesson_id.grammar_vi, text)
        self.assertIn(progress.lesson_id.phrases_vi, text)

    def test_exact_answer_without_api_and_review_schedule(self):
        progress = self.start()
        with patch.object(self.config_type, '_gemini') as gemini:
            self.learner._handle_text('  MY name is Nam! ')
        gemini.assert_not_called()
        self.assertEqual(progress.state, 'done')
        self.assertEqual(progress.review_step, 1)
        self.assertEqual(
            progress.review_date, fields.Date.today() + timedelta(days=1)
        )
        self.assertTrue(progress.attempt_ids.correct)

    def test_answer_shown_does_not_increase_mastery(self):
        progress = self.start()
        self.learner._handle_text('/answer')
        self.learner._handle_text(progress.lesson_id.answer)
        self.assertEqual(progress.state, 'done')
        self.assertEqual(progress.review_step, 0)
        self.assertTrue(progress.attempt_ids.answer_shown)

    def test_due_review_before_new_lesson(self):
        progress = self.start()
        self.learner._handle_text(progress.lesson_id.answer)
        progress.review_date = fields.Date.today()
        self.learner._start_lesson()
        self.assertEqual(self.learner.current_progress_id, progress)
        self.assertEqual(progress.state, 'awaiting')
        self.assertFalse(progress.answer_shown)

    def test_pending_lesson_not_replaced(self):
        progress = self.start()
        self.learner._start_lesson()
        self.assertEqual(self.learner.current_progress_id, progress)
        self.assertEqual(len(self.learner.progress_ids), 1)

    def test_equivalent_answer_graded_as_correct(self):
        progress = self.start()
        self.learner._handle_text('You can call me Nam.')
        self.assertEqual(progress.state, 'grading')
        with patch.object(self.config_type, '_gemini', return_value=({
            'correct': True, 'feedback': 'Cách giới thiệu phù hợp.',
            'corrected_answer': 'You can call me Nam.',
        }, 50)):
            self.jobs._cron_process()
        self.assertEqual(progress.state, 'done')
        self.assertTrue(progress.attempt_ids.correct)
        self.assertEqual(self.jobs.search([], limit=1).tokens, 50)

    def test_wrong_answer_can_retry(self):
        progress = self.start()
        self.learner._handle_text('My name Nam.')
        with patch.object(self.config_type, '_gemini', return_value=({
            'correct': False, 'feedback': 'Cần thêm is sau My name.',
            'corrected_answer': 'My name is Nam.',
        }, 45)):
            self.jobs._cron_process()
        self.assertEqual(progress.state, 'awaiting')
        self.assertFalse(progress.attempt_ids.correct)
        self.learner._handle_text('My name is Nam.')
        self.assertEqual(progress.state, 'done')
        self.assertEqual(len(progress.attempt_ids), 2)

    def test_duplicate_update_only_one_attempt(self):
        self.start()
        self.update('My name is Nam.', update_id=12)
        self.update('My name is Nam.', update_id=12)
        self.assertEqual(len(self.learner.current_progress_id.attempt_ids), 1)

    def test_unpaired_chat_cannot_receive_data(self):
        self.update('/lesson', chat=456)
        self.assertFalse(self.outbox.search([]))
        self.assertFalse(self.learner.progress_ids)

    def test_pairing_once_and_bot_binding(self):
        learner = self.env['english.learner'].create({'name': 'Pairing'})
        learner.action_pair()
        command = learner.pairing_command
        self.update(command, update_id=1, chat=456)
        self.assertEqual(learner.chat_id, '456')
        self.assertFalse(learner.pairing_hash)
        self.update(command, update_id=2, chat=789)
        self.assertEqual(learner.chat_id, '456')

    def test_expired_pairing_and_changed_bot_rejected(self):
        learner = self.env['english.learner'].create({'name': 'Expired'})
        learner.action_pair()
        command = learner.pairing_command
        learner.pairing_expiry = fields.Datetime.now() - timedelta(seconds=1)
        self.update(command, update_id=1, chat=456)
        self.assertFalse(learner.chat_id)
        learner.action_pair()
        self.config.telegram_token = 'new-test-token'
        self.update(learner.pairing_command, update_id=2, chat=456)
        self.assertFalse(learner.chat_id)

    def test_daily_local_timezone_and_dedup(self):
        self.config.enabled = True
        self.learner.write({'send_hour': 8, 'send_minute': 15})
        with patch.object(fields.Datetime, 'now', return_value=(
            fields.Datetime.to_datetime('2026-10-08 01:14:00')
        )):
            self.env['english.learner']._cron_daily()
        self.assertFalse(self.learner.progress_ids)
        with patch.object(fields.Datetime, 'now', return_value=(
            fields.Datetime.to_datetime('2026-10-08 01:15:00')
        )):
            self.env['english.learner']._cron_daily()
            count = self.outbox.search_count([])
            self.env['english.learner']._cron_daily()
        self.assertEqual(
            self.learner.last_daily_date.isoformat(), '2026-10-08'
        )
        self.assertEqual(self.outbox.search_count([]), count)

    def test_pause_resume_and_automatic_delivery_skipped(self):
        self.learner._start_lesson(automatic=True)
        delivery = self.outbox.search([], limit=1)
        self.learner._handle_text('/pause')
        with patch.object(self.config_type, '_telegram', return_value={}):
            self.outbox._cron_send()
        self.assertEqual(delivery.state, 'skipped')
        self.learner._handle_text('/resume')
        self.assertFalse(self.learner.paused)

    def test_changed_bot_outbox_skipped(self):
        self.start()
        delivery = self.outbox.search([], limit=1)
        self.config.telegram_token = 'new-test-token'
        with patch.object(self.config_type, '_telegram') as telegram:
            self.outbox._cron_send()
        telegram.assert_not_called()
        self.assertEqual(delivery.state, 'skipped')

    def test_split_unicode_and_resume_after_partial_failure(self):
        text = '🌱' * 4000
        self.assertEqual(''.join(split_message(text)), text)
        for part in split_message(text):
            self.assertLessEqual(len(part.encode('utf-16-le')) // 2, 3800)
        delivery = self.learner._reply(text, keyboard=True)
        with patch.object(self.config_type, '_telegram', side_effect=[
            {}, UserError('mock unavailable'),
        ]):
            self.outbox._cron_send()
        self.assertEqual(delivery.next_part, 1)
        self.assertEqual(delivery.state, 'pending')
        delivery.next_run = fields.Datetime.now()
        with patch.object(
            self.config_type, '_telegram', return_value={}
        ) as api:
            self.outbox._cron_send()
        self.assertEqual(api.call_count, 2)
        self.assertEqual(delivery.state, 'sent')
        self.assertIn('reply_markup', api.call_args.args[1])

    def test_outbox_order_and_retry_limit(self):
        first = self.learner._reply('First')
        second = self.learner._reply('Second')
        with patch.object(self.config_type, '_telegram', side_effect=(
            UserError('mock unavailable')
        )):
            self.outbox._cron_send()
            self.assertEqual(second.attempts, 0)
            for unused in range(4):
                first.next_run = fields.Datetime.now()
                self.outbox._cron_send()
        self.assertEqual(first.state, 'failed')
        first.action_retry()
        self.assertEqual(first.attempts, 0)
        self.assertEqual(first.state, 'pending')

    def test_generation_draft_and_no_duplicate_pending(self):
        self.learner.action_generate_lesson()
        self.learner.action_generate_lesson()
        self.assertEqual(self.jobs.search_count([]), 1)
        seed = self.env.ref('daily_english.lesson_intro')
        result = {key: seed[key] for key in LESSON_FIELDS}
        result['sample_answers'] = 'I am Lan. — Tôi là Lan.'
        with patch.object(self.config_type, '_gemini', return_value=(
            result, 100,
        )):
            self.jobs._cron_process()
        generated = self.env['english.lesson'].search([
            ('generated', '=', True),
        ])
        self.assertEqual(generated.state, 'draft')
        self.assertEqual(generated.generated_for_id, self.learner)
        self.learner.action_generate_lesson()
        self.assertEqual(self.jobs.search_count([]), 1)

    def test_generation_auto_approved(self):
        self.config.require_approval = False
        self.learner.action_generate_lesson()
        seed = self.env.ref('daily_english.lesson_intro')
        result = {key: seed[key] for key in LESSON_FIELDS}
        result['sample_answers'] = 'I am Lan. — Tôi là Lan.'
        with patch.object(
            self.config_type, '_gemini', return_value=(result, 90)
        ):
            self.jobs._cron_process()
        self.assertEqual(self.env['english.lesson'].search([
            ('generated', '=', True),
        ]).state, 'ready')
        self.assertTrue(self.learner.current_progress_id)

    def test_generate_before_pairing_keeps_lesson(self):
        learner = self.env['english.learner'].create({'name': 'Not paired'})
        self.config.require_approval = False
        learner.action_generate_lesson()
        seed = self.env.ref('daily_english.lesson_intro')
        result = {key: seed[key] for key in LESSON_FIELDS}
        result['sample_answers'] = 'I am Lan. — Tôi là Lan.'
        with patch.object(
            self.config_type, '_gemini', return_value=(result, 90)
        ):
            self.jobs._cron_process()
        generated = self.env['english.lesson'].search([
            ('generated_for_id', '=', learner.id),
        ])
        self.assertEqual(generated.state, 'ready')
        self.assertEqual(self.jobs.search([], limit=1).state, 'done')
        self.assertFalse(learner.current_progress_id)

    def test_api_quota_persists_across_retry(self):
        self.config.daily_api_limit = 1
        self.learner.action_generate_lesson()
        job = self.jobs.search([], limit=1)
        with patch.object(self.config_type, '_gemini', side_effect=(
            UserError('mock unavailable')
        )) as gemini:
            self.jobs._cron_process()
            job.next_run = fields.Datetime.now()
            self.jobs._cron_process()
        self.assertEqual(gemini.call_count, 1)
        self.assertEqual(self.env['english.api.usage'].search_count([]), 1)

    def test_failed_grading_restores_answerable_state(self):
        progress = self.start()
        self.learner._handle_text('Incorrect answer')
        job = self.jobs.search([], limit=1)
        with patch.object(self.config_type, '_gemini', side_effect=(
            UserError('mock unavailable')
        )):
            for unused in range(3):
                job.next_run = fields.Datetime.now()
                self.jobs._cron_process()
        self.assertEqual(job.state, 'failed')
        self.assertEqual(progress.state, 'awaiting')

    def test_old_failed_job_cannot_overwrite_new_answer(self):
        progress = self.start()
        self.learner._handle_text('Incorrect answer')
        job = self.jobs.search([], limit=1)
        with patch.object(self.config_type, '_gemini', side_effect=(
            UserError('mock unavailable')
        )):
            for unused in range(3):
                job.next_run = fields.Datetime.now()
                self.jobs._cron_process()
        self.learner._handle_text(progress.lesson_id.answer)
        self.assertEqual(progress.state, 'done')
        with self.assertRaises(UserError):
            job.action_retry()
        self.assertEqual(progress.state, 'done')
        self.assertEqual(progress.review_step, 1)

    def test_paused_job_does_not_call_gemini(self):
        progress = self.start()
        self.learner._handle_text('Another answer')
        self.learner.paused = True
        with patch.object(self.config_type, '_gemini') as gemini:
            self.jobs._cron_process()
        gemini.assert_not_called()
        self.assertEqual(progress.state, 'awaiting')
        self.assertEqual(self.jobs.search([], limit=1).state, 'skipped')

    def test_ask_uses_current_lesson_context(self):
        self.start()
        self.learner._handle_text('/ask Vì sao dùng is?')
        with patch.object(self.config_type, '_gemini', return_value=(
            {'feedback': 'My name là chủ ngữ số ít nên dùng is.'}, 50,
        )) as gemini:
            self.jobs._cron_process()
        context = json.loads(gemini.call_args.args[0])
        self.assertEqual(context['learner_question'], 'Vì sao dùng is?')
        self.assertIn('My name', context['answer'])

    def test_gemini_rejects_incomplete_and_wrong_types(self):
        response = {'candidates': [{
            'finishReason': 'STOP', 'content': {'parts': [{
                'text': '{"correct":"false","feedback":"No"}',
            }]},
        }]}
        with patch.object(
            self.config_type, '_post_json', return_value=response
        ):
            with self.assertRaises(UserError):
                self.config._gemini('test', {
                    'correct': 'BOOLEAN', 'feedback': 'STRING',
                })
        response['candidates'][0]['finishReason'] = 'MAX_TOKENS'
        with patch.object(
            self.config_type, '_post_json', return_value=response
        ):
            with self.assertRaises(UserError):
                self.config._gemini('test', {'feedback': 'STRING'})

    def test_gemini_header_and_schema(self):
        response = {'candidates': [{
            'finishReason': 'STOP', 'content': {'parts': [{
                'text': '{"feedback":"Xin chào"}',
            }]},
        }], 'usageMetadata': {'totalTokenCount': 12}}
        with patch.object(self.config_type, '_post_json', return_value=response
                          ) as post:
            result, tokens = self.config._gemini(
                'test', {'feedback': 'STRING'}
            )
        self.assertEqual(result['feedback'], 'Xin chào')
        self.assertEqual(tokens, 12)
        self.assertNotIn(self.config.gemini_key, post.call_args.args[0])
        self.assertEqual(post.call_args.args[2]['x-goog-api-key'],
                         self.config.gemini_key)

    def gemini_response(self):
        return {'candidates': [{
            'finishReason': 'STOP', 'content': {'parts': [{
                'text': '{"feedback":"Xin chào"}',
            }]},
        }]}

    def interaction_response(self, status='completed'):
        return {
            'status': status, 'usage': {'total_tokens': 24},
            'steps': [
                {'type': 'thought', 'text': 'Do not display reasoning.'},
                {'type': 'model_output', 'content': [{
                    'type': 'text', 'text': '{"feedback":"Xin chào"}',
                }]},
            ],
        }

    def test_interactions_request_matches_documented_rest(self):
        self.config.gemini_api = 'interactions'
        self.config.gemini_model = 'gemini-3.8-flash'
        with patch.object(
            self.config_type, '_post_json',
            return_value=self.interaction_response(),
        ) as post:
            result, tokens = self.config._gemini(
                'Hello', {'feedback': 'STRING'}
            )
        endpoint, payload, headers = post.call_args.args
        self.assertEqual(
            endpoint,
            'https://generativelanguage.googleapis.com/v1beta/interactions',
        )
        self.assertEqual(payload['model'], 'gemini-3.8-flash')
        self.assertEqual(payload['input'], 'Hello')
        self.assertFalse(payload['store'])
        self.assertEqual(payload['response_format'], {
            'type': 'text', 'mime_type': 'application/json', 'schema': {
                'type': 'object',
                'properties': {'feedback': {'type': 'string'}},
                'required': ['feedback'], 'additionalProperties': False,
            },
        })
        self.assertNotIn('contents', payload)
        self.assertEqual(headers['x-goog-api-key'], self.config.gemini_key)
        self.assertEqual(result['feedback'], 'Xin chào')
        self.assertEqual(tokens, 24)

    def test_interactions_incomplete_refused(self):
        self.config.gemini_api = 'interactions'
        for status in ('incomplete', 'failed', 'in_progress'):
            with patch.object(
                self.config_type, '_post_json',
                return_value=self.interaction_response(status),
            ):
                with self.assertRaises(UserError):
                    self.config._gemini('Hello', {'feedback': 'STRING'})

    def test_interactions_auto_fallback_uses_model_in_payload(self):
        self.config.write({
            'gemini_api': 'interactions', 'gemini_model': 'auto',
        })
        with patch.object(
            self.config_type, '_list_gemini_models', return_value=[
                'gemini-3.8-flash', 'gemini-2.5-flash',
            ],
        ), patch.object(self.config_type, '_post_json', side_effect=[
            gemini_api_error(404), self.interaction_response(),
        ]) as post:
            self.config._gemini('Hello', {'feedback': 'STRING'})
        self.assertEqual(post.call_args_list[0].args[1]['model'],
                         'gemini-3.8-flash')
        self.assertEqual(post.call_args_list[1].args[1]['model'],
                         'gemini-2.5-flash')
        self.assertEqual(self.config.resolved_gemini_model, 'gemini-2.5-flash')

    def test_google_error_detail_redacts_secrets(self):
        from io import BytesIO
        from urllib import error

        body = json.dumps({'error': {'message': (
            'Model not found. Key: ' + self.config.gemini_key
            + ' https://example.com?key=' + self.config.gemini_key
        )}}).encode()
        endpoint = 'https://generativelanguage.googleapis.com/v1beta/models'
        failure = error.HTTPError(
            endpoint, 404, 'Not Found', {}, BytesIO(body)
        )
        with patch(
            'odoo.addons.daily_english.models.english_configuration.'
            'request.urlopen', side_effect=failure,
        ):
            with self.assertRaises(UserError) as caught:
                self.config._get_json(endpoint)
        self.assertEqual(type(caught.exception), UserError)
        self.assertIn('Model not found', str(caught.exception))
        self.assertNotIn(self.config.gemini_key, str(caught.exception))
        self.assertNotIn('https://', str(caught.exception))

    def test_interactions_generated_lesson_saved(self):
        self.config.gemini_api = 'interactions'
        self.learner.action_generate_lesson()
        seed = self.env.ref('daily_english.lesson_intro')
        response = self.interaction_response()
        response['steps'][-1]['content'][0]['text'] = json.dumps({
            **{key: seed[key] for key in LESSON_FIELDS},
            'sample_answers': 'I am Lan. — Tôi là Lan.',
        })
        with patch.object(
            self.config_type, '_post_json', return_value=response
        ):
            self.jobs._cron_process()
        generated = self.env['english.lesson'].search([
            ('generated_for_id', '=', self.learner.id),
        ])
        self.assertEqual(generated.state, 'draft')
        self.assertEqual(self.jobs.search([], limit=1).state, 'done')

    def test_auto_model_falls_back_on_404(self):
        self.config.gemini_model = 'auto'
        names = ['gemini-3.8-flash', 'gemini-2.5-flash']
        with patch.object(
            self.config_type, '_list_gemini_models', return_value=names
        ), patch.object(self.config_type, '_post_json', side_effect=[
            gemini_api_error(404), self.gemini_response(),
        ]) as post:
            self.config._gemini('hello', {'feedback': 'STRING'})
        self.assertEqual(post.call_count, 2)
        self.assertIn('gemini-3.8-flash', post.call_args_list[0].args[0])
        self.assertEqual(self.config.resolved_gemini_model, 'gemini-2.5-flash')

    def test_auto_does_not_fallback_for_quota_or_permissions(self):
        self.config.gemini_model = 'auto'
        for status in (400, 403, 429, 500):
            with patch.object(
                self.config_type, '_list_gemini_models', return_value=[
                    'gemini-3.8-flash', 'gemini-2.5-flash',
                ],
            ), patch.object(
                self.config_type, '_post_json',
                side_effect=gemini_api_error(status),
            ) as post:
                with self.assertRaises(UserError):
                    self.config._gemini('hello', {'feedback': 'STRING'})
            self.assertEqual(post.call_count, 1)

    def test_manual_model_404_does_not_change_model(self):
        with patch.object(self.config_type, '_post_json', side_effect=(
            gemini_api_error(404)
        )), patch.object(self.config_type, '_list_gemini_models') as listing:
            with self.assertRaises(UserError):
                self.config._gemini('hello', {'feedback': 'STRING'})
        listing.assert_not_called()
        self.assertEqual(self.config.gemini_model, 'gemini-2.5-flash')

    def test_auto_excludes_specialized_and_pro_models(self):
        names = [
            'gemini-3.8-pro', 'gemini-3.8-flash-image',
            'gemini-3.8-flash-preview', 'gemini-2.5-flash',
            'gemini-3.8-flash', 'gemini-3.8-flash-lite',
            'gemini-3.8-flash-tts',
        ]
        with patch.object(
            self.config_type, '_list_gemini_models', return_value=names
        ):
            candidates = self.config._auto_candidates()
        self.assertEqual(candidates, [
            'gemini-3.8-flash', 'gemini-2.5-flash', 'gemini-3.8-flash-lite',
        ])

    def test_auto_404_exhaustion_is_bounded(self):
        self.config.gemini_model = 'auto'
        names = [f'gemini-{version}.0-flash' for version in range(2, 7)]
        with patch.object(
            self.config_type, '_list_gemini_models', return_value=names
        ), patch.object(
            self.config_type, '_post_json', side_effect=gemini_api_error(404)
        ) as post:
            with self.assertRaises(UserError):
                self.config._gemini('hello', {'feedback': 'STRING'})
        self.assertEqual(post.call_count, 3)

    def test_models_list_pagination_and_api_key_header(self):
        pages = [
            {'models': [{
                'name': 'models/gemini-3.8-flash',
                'supportedGenerationMethods': ['generateContent'],
            }], 'nextPageToken': 'page 2'},
            {'models': [{
                'name': 'models/gemini-2.5-flash',
                'supportedGenerationMethods': ['generateContent'],
            }, {
                'name': 'models/embedding-only',
                'supportedGenerationMethods': ['embedContent'],
            }]},
        ]
        with patch.object(
            self.config_type, '_get_json', side_effect=pages
        ) as get:
            names = self.config._list_gemini_models()
        self.assertEqual(names, ['gemini-2.5-flash', 'gemini-3.8-flash'])
        self.assertIn('pageToken=page+2', get.call_args.args[0])
        self.assertNotIn(self.config.gemini_key, get.call_args.args[0])
        self.assertEqual(get.call_args.args[1], {
            'x-goog-api-key': self.config.gemini_key,
        })

    def test_auto_button_and_empty_candidates(self):
        with patch.object(
            self.config_type, '_list_gemini_models', return_value=[
                'gemini-3.8-flash',
            ],
        ):
            self.config.action_auto_model()
        self.assertEqual(self.config.gemini_model, 'auto')
        self.assertIn('gemini-3.8-flash', self.config.gemini_models_info)
        with patch.object(
            self.config_type, '_list_gemini_models', return_value=[]
        ):
            with self.assertRaises(UserError):
                self.config._auto_candidates()

    def test_gemini_http_errors_do_not_leak_keys(self):
        from urllib import error

        endpoint = 'https://generativelanguage.googleapis.com/v1beta/models'
        error_response = error.HTTPError(
            endpoint, 404, f'Contains {self.config.gemini_key}', {}, None,
        )
        with patch(
            'odoo.addons.daily_english.models.english_configuration.'
            'request.urlopen', side_effect=error_response,
        ):
            with self.assertRaises(UserError) as caught:
                self.config._get_json(endpoint)
        self.assertNotIn(self.config.gemini_key, str(caught.exception))
        self.assertIn('Auto', str(caught.exception))

    def test_changing_key_clears_previous_model_info(self):
        self.config.write({
            'resolved_gemini_model': 'gemini-2.5-flash',
            'gemini_models_info': 'gemini-2.5-flash',
        })
        self.config.gemini_key = 'new-test-key'
        self.assertFalse(self.config.resolved_gemini_model)
        self.assertFalse(self.config.gemini_models_info)

    def test_admin_only_access_and_rpc_actions(self):
        user = self.env['res.users'].create({
            'name': 'Non admin', 'login': 'daily_english_test_user',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        for model in (
            'english.configuration', 'english.lesson', 'english.learner',
            'english.progress', 'english.attempt', 'english.delivery',
            'english.job', 'english.update', 'english.api.usage',
        ):
            with self.assertRaises(AccessError):
                self.env[model].with_user(user).search([])
        with self.assertRaises(AccessError):
            self.learner.with_user(user).action_pair()
        with self.assertRaises(UserError):
            self.config.with_user(user).action_test_gemini()

    def test_configuration_url_and_time_validation(self):
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.learner.send_hour = 24
        self.config.public_url = 'https://example.com?key=secret'
        with self.assertRaises(UserError):
            self.config.action_connect()

    def test_webhook_setup_preserves_pending_updates(self):
        self.config.public_url = 'https://example.com'
        with patch.object(self.config_type, '_telegram', return_value=True
                          ) as telegram:
            self.config.action_connect()
        payload = telegram.call_args.args[1]
        self.assertEqual(
            payload['url'],
            'https://example.com/daily_english/telegram/webhook',
        )
        self.assertFalse(payload['drop_pending_updates'])
        self.assertEqual(payload['secret_token'], self.config.webhook_secret)

    def test_router_combo_payload_and_json(self):
        self.config.write({
            'ai_provider': '9router', 'gemini_key': False,
            'router_key': 'router-test-key',
        })
        response = {
            'choices': [{'finish_reason': 'stop', 'message': {
                'content': '{"feedback": "Chào bạn"}',
            }}],
            'usage': {'total_tokens': 12},
        }
        with patch.object(
            self.config_type, '_post_json', return_value=response,
        ) as post:
            result, tokens = self.config._gemini(
                'Hello', {'feedback': 'STRING'},
            )
        args, kwargs = post.call_args
        self.assertEqual(
            args[0], 'http://localhost:20128/v1/chat/completions',
        )
        self.assertEqual(args[1]['model'], 'daily-english')
        self.assertFalse(args[1]['stream'])
        self.assertEqual(args[2]['Authorization'], 'Bearer router-test-key')
        self.assertEqual(kwargs['timeout'], 30)
        self.assertEqual(result['feedback'], 'Chào bạn')
        self.assertEqual(tokens, 12)

    def test_router_rejects_truncated_and_invalid_json(self):
        self.config.ai_provider = '9router'
        for reason, content in (
            ('length', '{"feedback": "Hello"}'),
            ('stop', '{"feedback": true}'),
        ):
            with self.assertRaises(UserError):
                self.config._gemini_parse({
                    'choices': [{'finish_reason': reason, 'message': {
                        'content': content,
                    }}],
                }, {'feedback': 'STRING'})

    def test_enqueue_wakes_ai_and_delivery_independently(self):
        cron_type = type(self.env['ir.cron'])
        woke = []

        def trigger(cron, at=None):
            woke.append(cron.id)
            return self.env['ir.cron.trigger']

        delivery_cron = self.env.ref('daily_english.cron_english_delivery')
        ai_cron = self.env.ref('daily_english.cron_english_jobs')
        with patch.object(cron_type, '_trigger', trigger):
            self.jobs._enqueue(self.learner, 'generate')
            self.learner._reply('Đã nhận yêu cầu.')
            self.assertEqual(woke, [ai_cron.id, delivery_cron.id])
            with patch.object(
                self.config_type, '_telegram', return_value={},
            ) as telegram:
                self.outbox._cron_send()
            telegram.assert_called_once()
            self.assertEqual(woke[-1], ai_cron.id)

    def test_ai_one_job_per_wakeup(self):
        self.jobs._enqueue(self.learner, 'generate')
        self.jobs._enqueue(self.learner, 'generate')
        with patch.object(type(self.jobs), '_process') as process:
            self.jobs._cron_process()
        self.assertEqual(process.call_count, 1)
        self.assertEqual(self.jobs.search_count([
            ('state', '=', 'pending'),
        ]), 1)

    def test_session_five_answers_then_summary(self):
        self.learner._handle_text('/lesson')
        seen = set()
        for index in range(5):
            progress = self.learner.current_progress_id
            self.assertNotIn(progress.id, seen)
            seen.add(progress.id)
            self.assertEqual(progress.state, 'awaiting')
            progress._submit(progress.lesson_id.answer)
            self.assertEqual(self.learner.session_count, index + 1)
        self.assertFalse(self.learner.session_active)
        self.assertEqual(self.learner.session_correct, 5)
        self.assertIn('Hoàn thành buổi học', self.outbox.search(
            [], order='id desc', limit=1,
        ).text)

    def test_session_skip_does_not_increase_mastery(self):
        self.learner._handle_text('/lesson')
        progress = self.learner.current_progress_id
        self.learner._handle_text('/skip')
        self.assertEqual(progress.review_step, 0)
        self.assertEqual(self.learner.session_skipped, 1)
        self.assertNotEqual(self.learner.current_progress_id, progress)

    def test_stopped_session_does_not_auto_advance(self):
        self.learner._handle_text('/lesson')
        progress = self.learner.current_progress_id
        self.learner._handle_text('/stop')
        progress._submit(progress.lesson_id.answer)
        self.assertEqual(self.learner.current_progress_id, progress)
        self.assertFalse(self.learner.session_active)

    def test_session_wrong_answer_stays_on_question(self):
        self.learner._handle_text('/lesson')
        progress = self.learner.current_progress_id
        attempt = self.env['english.attempt'].create({
            'progress_id': progress.id, 'answer_text': 'wrong',
        })
        attempt._finish(False, 'Thử lại nhé.')
        self.assertEqual(self.learner.current_progress_id, progress)
        self.assertEqual(progress.state, 'awaiting')
        self.assertEqual(self.learner.session_count, 0)

    def test_grade_retry_notifies_once_and_schedules_quickly(self):
        self.start()
        self.learner._handle_text('Another answer')
        job = self.jobs.search([], limit=1)
        failure = UserError('Do not expose provider details')
        failure.api_error_code = 'api_timeout'
        before = fields.Datetime.now()
        with patch.object(self.config_type, '_gemini', side_effect=failure):
            self.jobs._cron_process()
            self.assertEqual(job.error_code, 'api_timeout')
            self.assertLessEqual(job.next_run - before, timedelta(seconds=12))
            notices = self.outbox.search([
                ('text', 'ilike', 'không cần gửi lại'),
            ])
            self.assertEqual(len(notices), 1)
            job.next_run = fields.Datetime.now()
            self.jobs._cron_process()
            self.assertEqual(self.outbox.search_count([
                ('text', 'ilike', 'không cần gửi lại'),
            ]), 1)
        self.assertEqual(job.state, 'failed')
        self.assertEqual(job.progress_id.state, 'awaiting')
        self.assertNotIn('provider details', notices.text)

    def test_invalid_ai_output_has_safe_error_code(self):
        self.config.ai_provider = '9router'
        with self.assertRaises(UserError) as caught:
            self.config._gemini_parse({
                'choices': [{
                    'finish_reason': 'stop',
                    'message': {'content': 'not json'},
                }],
            }, {'feedback': 'STRING'})
        self.assertEqual(caught.exception.api_error_code, 'invalid_ai_output')

    def test_telegram_commands_registration(self):
        with patch.object(self.config_type, '_telegram',
                          return_value=True) as telegram:
            action = self.config.action_update_telegram_commands()
        self.assertEqual(telegram.call_count, 3)
        first = telegram.call_args_list[0].args
        self.assertEqual(first[0], 'setMyCommands')
        self.assertEqual(first[1]['scope'], {'type': 'all_private_chats'})
        commands = first[1]['commands']
        self.assertEqual(len(commands), 15)
        self.assertTrue(all(' ' not in c['command'] for c in commands))
        self.assertIn('roadmap', [c['command'] for c in commands])
        self.assertEqual(telegram.call_args_list[-1].args, (
            'setChatMenuButton', {'menu_button': {'type': 'commands'}},
        ))
        self.assertEqual(action['type'], 'ir.actions.client')

    def test_telegram_commands_failure_not_reported_as_success(self):
        with patch.object(self.config_type, '_telegram', return_value=False):
            with self.assertRaises(UserError):
                self.config.action_update_telegram_commands()

    def test_interactive_timeout_does_not_reduce_generation_budget(self):
        self.assertEqual(self.config.with_context(
            english_job_kind='grade',
        )._ai_timeout(), 12)
        self.assertEqual(self.config.with_context(
            english_job_kind='prepare',
        )._ai_timeout(), 30)

    def test_zero_quota_allows_calls_and_still_records_usage(self):
        self.config.daily_api_limit = 0
        self.start()
        self.learner._handle_text('An alternative answer')
        with patch.object(self.config_type, '_gemini', return_value=({
            'correct': True, 'feedback': 'Đúng.',
            'corrected_answer': 'My name is Nam.',
        }, 10)) as ai:
            self.jobs._cron_process()
        ai.assert_called_once()
        self.assertEqual(self.jobs.search([], limit=1).state, 'done')
        self.assertEqual(self.env['english.api.usage'].search_count([]), 1)
