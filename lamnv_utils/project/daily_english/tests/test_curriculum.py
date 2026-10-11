import hashlib
import importlib.util
from pathlib import Path
import json
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged

from ..models.english_lesson import LESSON_FIELDS


@tagged('post_install', '-at_install')
class TestCurriculum(TransactionCase):

    def setUp(self):
        super().setUp()
        commit = patch.object(
            type(self.env['ir.cron']), '_commit_progress', return_value=60,
        )
        commit.start()
        self.addCleanup(commit.stop)
        self.config = self.env.ref('daily_english.configuration_default')
        self.config.telegram_token = 'curriculum-test'
        self.learner = self.env['english.learner'].create({
            'name': 'Curriculum', 'chat_id': '88001',
            'bot_hash': hashlib.sha256(b'curriculum-test').hexdigest(),
        })
        self.unit = self.env.ref('daily_english.unit_1')
        self.lessons = self.env['english.lesson'].search([
            ('unit_id', '=', self.unit.id), ('level', '=', 'starter'),
            ('topic', '=', 'daily'),
        ])

    def assign(self, lesson):
        progress = self.env['english.progress'].search([
            ('learner_id', '=', self.learner.id),
            ('lesson_id', '=', lesson.id),
        ], limit=1)
        if not progress:
            progress = self.env['english.progress'].create({
                'learner_id': self.learner.id, 'lesson_id': lesson.id,
            })
        progress.write({'state': 'awaiting', 'answer_shown': False})
        self.learner.current_progress_id = progress
        return progress

    def finish(self, progress, correct, code=None):
        attempt = self.env['english.attempt'].create({
            'progress_id': progress.id, 'answer_text': 'She am happy.',
        })
        attempt._finish(correct, 'She đi với is.', error_type=code)
        return attempt

    def test_default_curriculum_and_local_choice(self):
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        self.assertEqual(progress.lesson_id.unit_id, self.unit)
        self.assertEqual(progress.lesson_id.exercise_type, 'choice')
        with patch.object(type(self.config), '_gemini') as ai:
            progress._submit(progress.lesson_id.answer)
        ai.assert_not_called()
        self.assertTrue(progress.independent_credit)
        self.assertEqual(
            self.learner.current_progress_id.lesson_id.exercise_type, 'cloze',
        )

    def test_wrong_choice_is_immediate_and_records_mistake(self):
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        options = progress.lesson_id._choice_options()
        wrong = next(value for value in options
                     if value != progress.lesson_id.answer)
        self.learner._handle_text(chr(65 + options.index(wrong)))
        self.assertEqual(progress.state, 'awaiting')
        self.assertTrue(progress.answer_shown)
        self.assertEqual(self.learner.mistake_ids.error_type, 'be')
        self.assertEqual(self.learner.mistake_ids.occurrences, 1)
        self.learner._handle_text(
            chr(65 + options.index(progress.lesson_id.answer))
        )
        self.assertFalse(progress.independent_credit)
        self.assertFalse(self.learner.mistake_ids.recovery_count)

    def test_invalid_choice_does_not_grade(self):
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        self.learner._handle_text('D')
        self.assertFalse(progress.attempt_ids)
        self.assertFalse(self.learner.mistake_ids)

    def test_hint_excludes_independent_credit(self):
        progress = self.assign(self.lessons[3])
        self.learner._handle_text('💡 Gợi ý')
        progress._submit(progress.lesson_id.answer)
        self.assertFalse(progress.independent_credit)

    def test_mistake_recovery_requires_two_different_exercises(self):
        progress = self.assign(self.lessons[0])
        self.finish(progress, False, 'be')
        self.finish(progress, False, 'be')
        mistake = self.learner.mistake_ids
        self.assertEqual(mistake.occurrences, 2)
        self.finish(self.assign(self.lessons[0]), True)
        self.assertEqual(mistake.recovery_count, 0)
        self.finish(self.assign(self.lessons[1]), True)
        self.finish(self.assign(self.lessons[1]), True)
        self.assertEqual(mistake.recovery_count, 1)
        self.finish(self.assign(self.lessons[2]), True)
        self.assertEqual(mistake.state, 'improving')
        self.finish(self.assign(self.lessons[2]), False, 'be')
        self.assertEqual(mistake.state, 'open')
        self.assertEqual(mistake.recovery_count, 0)

    def test_advance_only_next_session_with_productive_credit(self):
        for lesson in self.lessons:
            self.finish(self.assign(lesson), True)
        self.learner._begin_session()
        self.assertEqual(
            self.learner.unit_id, self.env.ref('daily_english.unit_2'),
        )
        self.assertEqual(self.learner.current_session_id.unit_id,
                         self.learner.unit_id)
        self.assertEqual(self.learner.current_progress_id.lesson_id.unit_id,
                         self.learner.unit_id)

    def test_recognition_alone_does_not_advance(self):
        for lesson in self.lessons[:3]:
            self.finish(self.assign(lesson), True)
        self.learner._begin_session()
        self.assertEqual(self.learner.unit_id, self.unit)

    def test_old_unfinished_lesson_is_preserved(self):
        old = self.env.ref('daily_english.lesson_intro')
        progress = self.assign(old)
        self.learner._begin_session()
        self.assertEqual(self.learner.current_progress_id, progress)

    def batch(self):
        result = {}
        for n, lesson in enumerate(self.lessons, 1):
            result.update({
                f'q{n}_{key}': lesson[key] for key in LESSON_FIELDS
            })
        result['q1_options'] = self.lessons[0].options
        return result

    def test_generation_schema_and_result_carry_curriculum(self):
        self.finish(self.assign(self.lessons[0]), False, 'be')
        plan = self.learner._daily_plan(self.learner._local_date())
        job = self.env['english.job'].search([
            ('session_id', '=', plan.id),
        ])
        prompt, properties = job._build_request()
        context = json.loads(prompt)
        self.assertEqual(len(context['exercise_types']), 5)
        self.assertEqual(context['target_error'], 'be')
        self.assertTrue(context['mistakes'])
        self.assertIn('q1_options', properties)
        self.assertNotIn('q2_options', properties)
        job._apply_result(self.config, self.batch())
        self.assertEqual(len(plan.lesson_ids), 5)
        self.assertEqual(plan.lesson_ids.unit_id, self.unit)
        self.assertEqual(plan.lesson_ids.mapped('exercise_type'), [
            'choice', 'cloze', 'reorder', 'translate', 'dialogue',
        ])

    def test_grade_schema_classifies_errors(self):
        progress = self.assign(self.lessons[3])
        progress._submit('I developer')
        job = self.env['english.job'].search([
            ('progress_id', '=', progress.id),
        ])
        prompt, properties = job._build_request()
        self.assertIn('error_type', properties)
        job._apply_result(self.config, {
            'correct': False, 'feedback': 'Thiếu am.',
            'corrected_answer': 'I am a developer.', 'error_type': 'be',
        })
        self.assertEqual(self.learner.mistake_ids.error_type, 'be')

    def test_choice_validation(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.lessons[0].options = 'am\nam'

    def test_roadmap_and_notebook_commands(self):
        self.learner._handle_text('/roadmap')
        outbox = self.env['english.delivery']
        self.assertIn(self.unit.name,
                      outbox.search([], order='id desc', limit=1).text)
        self.learner._handle_text('/mistakes')
        self.assertIn('Chưa có lỗi',
                      outbox.search([], order='id desc', limit=1).text)

    def test_stale_daily_plan_rebuilt_after_advance(self):
        plan = self.learner._daily_plan(fields.Date.today())
        old_job = self.env['english.job'].search([
            ('session_id', '=', plan.id),
        ])
        for lesson in self.lessons:
            self.finish(self.assign(lesson), True)
        self.learner._begin_session(planned=plan)
        self.assertEqual(old_job.state, 'skipped')
        self.assertEqual(plan.unit_id, self.env.ref('daily_english.unit_2'))
        self.assertFalse(old_job._valid(self.config))

    def test_previous_unit_mistake_drives_new_daily_exercise(self):
        self.finish(self.assign(self.lessons[0]), False, 'be')
        self.learner.unit_id = self.env.ref('daily_english.unit_2')
        plan = self.learner._daily_plan(self.learner._local_date())
        job = self.env['english.job'].search([
            ('session_id', '=', plan.id),
        ])
        self.assertEqual(job.target_unit_id, self.unit)
        self.assertEqual(job._lesson_metadata(1, {})['unit_id'], self.unit.id)
        self.assertEqual(job._lesson_metadata(2, {})['unit_id'],
                         self.learner.unit_id.id)
        job._apply_result(self.config, self.batch())
        self.learner.current_progress_id.state = 'done'
        self.learner._begin_session(planned=plan)
        self.assertEqual(self.learner.current_progress_id.lesson_id,
                         plan.lesson_ids.sorted('sequence')[0])

    def test_old_draft_does_not_block_curriculum_generation(self):
        self.env.ref('daily_english.lesson_intro').copy({
            'state': 'draft', 'generated_for_id': self.learner.id,
        })
        self.learner.action_generate_lesson()
        job = self.env['english.job'].search([
            ('learner_id', '=', self.learner.id), ('kind', '=', 'generate'),
        ])
        self.assertEqual(job.unit_id, self.unit)

    def test_full_worker_batch_uses_strict_schema(self):
        plan = self.learner._daily_plan(self.learner._local_date())
        result = self.batch()
        with patch.object(type(self.config), '_gemini',
                          return_value=(result, 200)) as ai:
            self.env['english.job']._cron_process()
        ai.assert_called_once()
        self.assertEqual(plan.state, 'ready')
        self.assertEqual(len(plan.lesson_ids), 5)
        self.assertEqual(plan.lesson_ids[0].options, result['q1_options'])

    def test_cloze_reorder_translation_dialogue_exact_answers(self):
        for lesson in self.lessons[1:4]:
            progress = self.assign(lesson)
            with patch.object(type(self.config), '_gemini') as ai:
                progress._submit(lesson.answer)
            ai.assert_not_called()
            self.assertEqual(progress.state, 'done')
            self.assertTrue(progress.independent_credit)

    def test_duplicate_exercises_do_not_double_curriculum_credit(self):
        self.finish(self.assign(self.lessons[3]), True)
        duplicate = self.lessons[3].copy()
        self.finish(self.assign(duplicate), True)
        self.assertEqual(len(self.learner._unit_credits()), 1)

    def test_wrong_review_revokes_curriculum_credit(self):
        progress = self.assign(self.lessons[3])
        self.finish(progress, True)
        self.assertTrue(progress.independent_credit)
        self.finish(self.assign(self.lessons[3]), False)
        self.assertFalse(progress.independent_credit)

    def test_choice_render_and_letter_share_same_order(self):
        progress = self.assign(self.lessons[0])
        lesson = progress.lesson_id
        options = lesson._choice_options()
        index = options.index(lesson.answer)
        letter = chr(65 + index)
        self.assertIn(f'{letter}. {lesson.answer}', lesson._render())
        progress._submit(letter)
        self.assertTrue(progress.independent_credit)

    def test_upgrade_skips_only_legacy_generation(self):
        job = self.env['english.job']._enqueue(self.learner, 'generate')
        job.unit_id = False
        progress = self.assign(self.lessons[3])
        progress._submit('I developer')
        grading = self.env['english.job'].search([
            ('progress_id', '=', progress.id), ('kind', '=', 'grade'),
        ])
        path = (Path(__file__).parents[1] / 'migrations'
                / '19.0.1.0.8' / 'post-migration.py')
        spec = importlib.util.spec_from_file_location('upgrade_english', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.migrate(self.cr, '19.0.1.0.7')
        self.assertEqual(job.state, 'skipped')
        self.assertEqual(grading.state, 'pending')
        self.assertEqual(self.learner.current_progress_id, progress)

    def test_notebook_is_admin_only(self):
        user = self.env['res.users'].create({
            'name': 'English unprivileged', 'login': 'english-unprivileged',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        with self.assertRaises(AccessError):
            self.env['english.mistake'].with_user(user).search([])

    def test_generation_does_not_block_interactive_worker(self):
        plan = self.learner._daily_plan(self.learner._local_date())
        progress = self.assign(self.lessons[3])
        progress._submit('I developer')
        grade = self.env['english.job'].search([
            ('progress_id', '=', progress.id), ('kind', '=', 'grade'),
        ])
        calls = []

        def respond(config, prompt, properties):
            if 'correct' in properties:
                calls.append('grade')
                return {
                    'correct': False, 'feedback': 'Thiếu am.',
                    'corrected_answer': 'I am a developer.',
                    'error_type': 'be',
                }, 50
            calls.append('prepare_started')
            self.env['english.job']._cron_process(interactive=True)
            self.assertEqual(grade.state, 'done')
            calls.append('prepare_finished')
            return self.batch(), 200

        with patch.object(type(self.config), '_gemini', respond):
            self.env['english.job']._cron_process(interactive=False)
        self.assertEqual(
            calls, ['prepare_started', 'grade', 'prepare_finished'],
        )
        self.assertEqual(plan.state, 'ready')

    def test_contractions_preserve_meaning(self):
        progress = self.assign(self.lessons[3])
        progress._submit('I’m a developer!')
        self.assertTrue(progress.independent_credit)
        self.assertFalse(self.env['english.job'].search([
            ('progress_id', '=', progress.id),
        ]))
        progress = self.assign(self.lessons[3])
        progress._submit('I am not a developer')
        self.assertEqual(progress.state, 'grading')

    def test_cached_grade_is_private_and_expires_after_edit(self):
        progress = self.assign(self.lessons[3])
        self.finish(progress, False, 'be')
        self.assertFalse(self.env['english.job'].search([
            ('progress_id', '=', progress.id),
        ]))
        progress._submit('She am happy.')
        self.assertTrue(progress.attempt_ids[0].graded)
        self.assertEqual(self.learner.mistake_ids.occurrences, 2)
        other = self.env['english.learner'].create({'name': 'Other'})
        other_progress = self.env['english.progress'].create({
            'learner_id': other.id, 'lesson_id': progress.lesson_id.id,
        })
        other.current_progress_id = other_progress
        other_progress._submit('She am happy.')
        self.assertEqual(other_progress.state, 'grading')
        self.assertFalse(other_progress.attempt_ids.graded)
        # Simulate a lesson edit newer than the recorded assessment.
        self.cr.execute(
            "UPDATE english_lesson SET write_date = NOW() + interval '1 day' "
            'WHERE id = %s', [progress.lesson_id.id],
        )
        progress.lesson_id.invalidate_recordset(['write_date'])
        progress._submit('She am happy.')
        self.assertEqual(progress.state, 'grading')

    def test_grade_enqueue_wakes_ai_without_waiting_for_delivery(self):
        progress = self.assign(self.lessons[3])
        awakened = []

        def trigger(cron, at=None):
            awakened.extend(cron.ids)

        with patch.object(type(self.env['ir.cron']), '_trigger', trigger):
            progress._submit('I developer')
        self.assertIn(
            self.env.ref('daily_english.cron_english_interactive').id,
            awakened,
        )
        self.assertIn(
            self.env.ref('daily_english.cron_english_delivery').id, awakened,
        )

    def test_exhausted_stock_sends_early_review_without_recall_credit(self):
        for lesson in self.lessons:
            progress = self.assign(lesson)
            progress.write({
                'state': 'done', 'review_date': '2099-01-01',
            })
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        self.assertEqual(progress.state, 'awaiting')
        self.assertTrue(progress.answer_shown)
        self.assertTrue(self.env['english.job'].search([
            ('learner_id', '=', self.learner.id), ('kind', '=', 'generate'),
        ]))
        progress._submit(progress.lesson_id.answer)
        self.assertEqual(progress.review_step, 0)
        self.assertFalse(progress.independent_credit)
        self.assertNotEqual(self.learner.current_progress_id, progress)

    def test_generation_does_not_resend_unanswered_question(self):
        self.learner._begin_session()
        progress = self.learner.current_progress_id
        job = self.env['english.job']._enqueue(self.learner, 'generate')
        result = {key: self.lessons[3][key] for key in LESSON_FIELDS}
        before = self.env['english.delivery'].search_count([])
        self.config.require_approval = False
        job._apply_result(self.config, result)
        self.assertEqual(self.learner.current_progress_id, progress)
        self.assertEqual(self.env['english.delivery'].search_count([]), before)

    def test_dialogue_accepts_personal_answer_and_follows_up(self):
        progress = self.assign(self.lessons[4])
        progress._submit('I work at company')
        job = self.env['english.job'].search([
            ('progress_id', '=', progress.id),
        ], limit=1)
        prompt, schema = job._build_request()
        self.assertNotIn('answer', json.loads(prompt))
        self.assertIn('grammar_clean', schema)
        result = {
            'correct': True, 'grammar_clean': False, 'error_type': 'article',
            'feedback': 'Đúng ý, thêm a trước company.',
            'corrected_answer': 'I work at a company.',
            'followup': 'What do you do there?',
            'followup_vi': 'Bạn làm công việc gì ở đó?',
        }
        job._apply_result(self.config, result)
        self.assertEqual(progress.state, 'awaiting')
        self.assertEqual(progress.dialogue_turn, 1)
        self.assertFalse(progress.independent_credit)
        self.assertIn('What do you do there?',
                      self.learner._lesson_text(progress.lesson_id))
        job.state = 'done'
        progress._submit('I write software.')
        next_job = self.env['english.job'].search([
            ('progress_id', '=', progress.id), ('state', '=', 'pending'),
        ], limit=1)
        prompt, unused = next_job._build_request()
        self.assertEqual(json.loads(prompt)['exercise'],
                         'What do you do there?')
        result.update({
            'grammar_clean': True, 'corrected_answer': 'I write software.',
        })
        next_job._apply_result(self.config, result)
        self.assertEqual(progress.state, 'done')
        self.assertFalse(progress.independent_credit)

    def test_repeating_dialogue_question_does_not_advance(self):
        progress = self.assign(self.lessons[4])
        progress._submit('What is your name?')
        job = self.env['english.job'].search([
            ('progress_id', '=', progress.id),
        ], limit=1)
        job._apply_result(self.config, {
            'correct': False, 'grammar_clean': True, 'error_type': 'other',
            'feedback': 'Hãy trả lời thay vì lặp lại câu hỏi.',
            'corrected_answer': 'My name is Lam.',
            'followup': 'What is your name?', 'followup_vi': 'Bạn tên gì?',
        })
        self.assertEqual(progress.state, 'awaiting')
        self.assertEqual(progress.dialogue_turn, 0)
