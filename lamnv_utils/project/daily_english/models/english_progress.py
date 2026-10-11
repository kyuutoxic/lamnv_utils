import re
import unicodedata
from datetime import timedelta

from odoo import fields, models


class EnglishProgress(models.Model):
    _name = 'english.progress'
    _description = 'English Learning Progress'
    _rec_name = 'lesson_id'

    learner_id = fields.Many2one(
        'english.learner', required=True, ondelete='cascade', index=True,
    )
    lesson_id = fields.Many2one(
        'english.lesson', required=True, ondelete='restrict',
    )
    state = fields.Selection([
        ('awaiting', 'Chờ trả lời'), ('grading', 'Đang chấm'),
        ('done', 'Đã hoàn thành'),
    ], default='awaiting', required=True)
    review_date = fields.Date(index=True)
    review_step = fields.Integer(default=0)
    answer_shown = fields.Boolean(default=False)
    attempt_ids = fields.One2many('english.attempt', 'progress_id')

    _learner_lesson_unique = models.Constraint(
        'UNIQUE(learner_id, lesson_id)', 'Lesson already assigned.'
    )

    def _submit(self, text):
        self.ensure_one()
        answers = [self.lesson_id.answer] + (
            self.lesson_id.accepted_answers or ''
        ).splitlines()
        normalized = self._normalize(text)
        attempt = self.env['english.attempt'].create({
            'progress_id': self.id, 'answer_text': text,
            'answer_shown': self.answer_shown,
        })
        if normalized in [self._normalize(answer) for answer in answers]:
            attempt._finish(True, self.lesson_id.answer_explanation_vi)
        else:
            # Reuse only this learner's result for the same unchanged lesson.
            recent = self.env['english.attempt'].search([
                ('progress_id', '=', self.id), ('graded', '=', True),
                ('create_date', '>=', self.lesson_id.write_date),
            ], limit=20)
            cached = recent.filtered(
                lambda item: self._normalize(item.answer_text) == normalized
            )[:1]
            if cached:
                return attempt._finish(
                    cached.correct, cached.feedback_vi,
                    cached.corrected_answer, error_type=cached.error_type,
                )
            job = self.env['english.job']._enqueue(
                self.learner_id, 'grade', progress=self, attempt=attempt,
            )
            if job:
                self.state = 'grading'
                self.learner_id._reply(
                    'Đã nhận câu trả lời. Đang kiểm tra cho bạn.'
                )

    def _normalize(self, text):
        text = unicodedata.normalize('NFC', text).casefold().strip()
        text = text.replace('’', "'").replace('‘', "'")
        contractions = {
            "i'm": 'i am', "you're": 'you are', "we're": 'we are',
            "they're": 'they are', "isn't": 'is not', "aren't": 'are not',
            "wasn't": 'was not', "weren't": 'were not',
            "don't": 'do not', "doesn't": 'does not', "didn't": 'did not',
            "can't": 'cannot', "won't": 'will not',
        }
        for short, full in contractions.items():
            text = re.sub(r'\b' + re.escape(short) + r'\b', full, text)
        return re.sub(r'\s+', ' ', text).rstrip('.!?').strip()


class EnglishAttempt(models.Model):
    _name = 'english.attempt'
    _description = 'English Exercise Attempt'
    _order = 'id desc'
    _rec_name = 'answer_text'

    progress_id = fields.Many2one(
        'english.progress', required=True, ondelete='cascade', index=True,
    )
    answer_text = fields.Text(required=True)
    correct = fields.Boolean(readonly=True)
    graded = fields.Boolean(readonly=True)
    answer_shown = fields.Boolean(readonly=True)
    feedback_vi = fields.Text(readonly=True)
    corrected_answer = fields.Text(readonly=True)

    def _can_grade(self):
        self.ensure_one()
        progress = self.progress_id
        latest = self.search([
            ('progress_id', '=', progress.id),
        ], order='id desc', limit=1)
        return (
            not self.graded and latest == self
            and progress.learner_id.current_progress_id == progress
            and progress.state in ('awaiting', 'grading')
        )

    def _finish(self, correct, feedback, corrected=None):
        self.ensure_one()
        if self.graded:
            return
        if self.progress_id.answer_shown:
            self.answer_shown = True
        self.write({
            'correct': correct, 'graded': True,
            'feedback_vi': feedback,
            'corrected_answer': corrected or self.progress_id.lesson_id.answer,
        })
        progress = self.progress_id
        if correct:
            step = progress.review_step
            if not self.answer_shown:
                step = min(step + 1, 4)
            delays = [1, 1, 3, 7, 14]
            progress.write({
                'state': 'done', 'review_step': step,
                'review_date': fields.Date.today()
                + timedelta(days=delays[step]),
            })
        else:
            if progress.learner_id.session_active:
                progress.learner_id.session_errors += 1
            progress.write({
                'state': 'awaiting', 'review_step': 0, 'answer_shown': True,
            })
            progress.learner_id._save_session()
        label = '✅ Đúng rồi!' if correct else '🌱 Mình cùng sửa nhé.'
        progress.learner_id._reply(
            f'{label}\n{feedback}\n\n'
            f'Câu mẫu: {self.corrected_answer}', keyboard=True,
        )
        if correct:
            progress.learner_id._session_advance(progress)
