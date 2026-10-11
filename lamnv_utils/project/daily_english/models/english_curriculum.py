import json
import random
from odoo import api, fields, models
from odoo.exceptions import ValidationError


EXERCISE_TYPES = [
    ('choice', 'Chọn đáp án'), ('cloze', 'Điền từ'),
    ('reorder', 'Sắp xếp câu'), ('translate', 'Dịch câu'),
    ('dialogue', 'Hội thoại'),
]
ERROR_TYPES = [
    ('be', 'Động từ am/is/are'), ('pronoun', 'Đại từ'),
    ('verb', 'Động từ và thì'), ('order', 'Trật tự từ'),
    ('article', 'Mạo từ'), ('preposition', 'Giới từ'),
    ('vocabulary', 'Từ vựng'), ('other', 'Cần luyện thêm'),
]


class EnglishUnit(models.Model):
    _name = 'english.unit'
    _description = 'English Curriculum Unit'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(required=True)
    objective_vi = fields.Text(required=True)
    grammar_vi = fields.Text(required=True)
    error_type = fields.Selection(ERROR_TYPES, required=True)
    lesson_ids = fields.One2many('english.lesson', 'unit_id')


class EnglishMistake(models.Model):
    _name = 'english.mistake'
    _description = 'Personal English Mistake Notebook'
    _order = 'last_seen desc, id desc'
    _rec_name = 'error_type'

    learner_id = fields.Many2one(
        'english.learner', required=True, ondelete='cascade', index=True,
    )
    unit_id = fields.Many2one(
        'english.unit', required=True, ondelete='restrict',
    )
    error_type = fields.Selection(ERROR_TYPES, required=True)
    occurrences = fields.Integer(default=0)
    recovery_count = fields.Integer(default=0)
    last_seen = fields.Date()
    last_answer = fields.Text()
    source_lesson_id = fields.Many2one(
        'english.lesson', ondelete='set null',
    )
    correction = fields.Text()
    explanation_vi = fields.Text()
    recovered_lesson_ids = fields.Many2many('english.lesson')
    state = fields.Selection([
        ('open', 'Cần luyện'), ('improving', 'Đã luyện đúng 2 câu khác'),
    ], default='open', required=True)

    _mistake_unique = models.Constraint(
        'UNIQUE(learner_id, unit_id, error_type)', 'Mistake already exists.',
    )


class CurriculumLesson(models.Model):
    _inherit = 'english.lesson'

    unit_id = fields.Many2one('english.unit', ondelete='restrict', index=True)
    exercise_type = fields.Selection(
        EXERCISE_TYPES, default='translate', required=True,
    )
    options = fields.Text(help='For choice exercises: one option per line.')
    target_error = fields.Selection(ERROR_TYPES)

    @api.constrains('exercise_type', 'options', 'answer', 'exercise')
    def _check_exercise(self):
        for lesson in self:
            if lesson.exercise_type == 'choice':
                options = (lesson.options or '').splitlines()
                keys = [lesson._text_key(value) for value in options]
                if (not 2 <= len(options) <= 4 or not all(keys)
                        or len(set(keys)) != len(keys)
                        or lesson._text_key(lesson.answer) not in keys):
                    raise ValidationError(
                        'Trắc nghiệm cần 2–4 lựa chọn khác nhau; '
                        'đáp án phải là nội dung một lựa chọn.'
                    )
            if lesson.exercise_type == 'cloze' and '___' not in (
                lesson.exercise
            ):
                raise ValidationError('Bài điền từ cần vị trí trống ___.')

    @api.model
    def _validate_generated(self, values):
        # Single-word answers naturally occur in grammar examples.
        if values.get('exercise_type') in ('choice', 'cloze'):
            return
        return super()._validate_generated(values)

    def _choice_options(self):
        self.ensure_one()
        options = (self.options or '').splitlines()
        # Stable for a question, varied across lessons; never move on retry.
        random.Random(self.id).shuffle(options)
        return options

    def _render(self, section='lesson'):
        text = super()._render(section)
        if section != 'lesson' or not self.unit_id:
            return text
        label = dict(EXERCISE_TYPES)[self.exercise_type]
        prefix = f'🧭 {self.unit_id.name} · {label}\n'
        if self.exercise_type == 'choice':
            options = '\n'.join(
                f'{chr(65 + n)}. {value}'
                for n, value in enumerate(self._choice_options())
            )
            text += f'\n\n{options}\nGửi A/B/C/D hoặc nội dung đáp án.'
        elif self.exercise_type == 'cloze':
            text += '\nChỉ gửi từ/cụm từ còn thiếu.'
        elif self.exercise_type == 'reorder':
            text += '\nGửi câu đã sắp xếp hoàn chỉnh.'
        if self.exercise_type == 'dialogue':
            prefix += (
                'Trả lời theo bản thân; bối cảnh và đáp án mẫu chỉ gợi ý.\n'
            )
        return prefix + text


class CurriculumLearner(models.Model):
    _inherit = 'english.learner'

    curriculum_enabled = fields.Boolean(default=True)
    unit_id = fields.Many2one('english.unit', ondelete='restrict')
    mistake_ids = fields.One2many('english.mistake', 'learner_id')

    def _learning_unit(self):
        self.ensure_one()
        if not self.curriculum_enabled:
            return self.env['english.unit']
        if not self.unit_id:
            self.unit_id = self.env['english.unit'].search([], limit=1)
        return self.unit_id

    def _unit_credits(self):
        unit = self._learning_unit()
        credits = self.env['english.progress']
        seen = set()
        for progress in self.progress_ids.filtered(
            lambda p: p.lesson_id.unit_id == unit and p.independent_credit
        ):
            key = progress.lesson_id._text_key(progress.lesson_id.exercise)
            if key not in seen:
                seen.add(key)
                credits |= progress
        return credits

    def _begin_session(self, automatic=False, planned=None):
        self._lock()
        if (self.curriculum_enabled and not self.session_active
                and self.current_progress_id.state not in (
                    'awaiting', 'grading',
                )):
            unit = self._learning_unit()
            credits = self._unit_credits()
            productive = credits.filtered(
                lambda p: p.lesson_id.exercise_type in (
                    'translate', 'dialogue',
                )
            )
            if len(credits) >= 4 and len(productive) >= 2:
                next_unit = self.env['english.unit'].search([
                    ('sequence', '>', unit.sequence),
                ], limit=1)
                if next_unit:
                    self.unit_id = next_unit
        if self.curriculum_enabled and not self.session_active:
            if not planned:
                planned = self.env['english.session'].sudo().search([
                    ('learner_id', '=', self.id),
                    ('daily_date', '=', self._local_date()),
                    ('state', 'in', ['ready', 'preparing', 'failed']),
                ], limit=1)
            if planned and planned.unit_id != self._learning_unit():
                self.env['english.job'].search([
                    ('session_id', '=', planned.id),
                    ('kind', '=', 'prepare'),
                    ('state', 'in', ['pending', 'running']),
                ]).write({'state': 'skipped'})
                planned.write({
                    'unit_id': self.unit_id.id,
                    'lesson_ids': [(5, 0, 0)], 'generation_done': False,
                })
                self.env['english.job']._enqueue(
                    self, 'prepare', session=planned,
                )
        return super()._begin_session(automatic=automatic, planned=planned)

    def _lesson_text(self, lesson):
        progress = self.current_progress_id
        if (progress.lesson_id == lesson and progress.dialogue_turn
                and progress.dialogue_question):
            return (
                f'💬 Hỏi tiếp về bạn (2/2)\n{progress.dialogue_question}\n'
                f'{progress.dialogue_question_vi}\n'
                'Trả lời theo trải nghiệm của bạn; không có đáp án cố định.'
            )
        text = super()._lesson_text(lesson)
        if lesson.unit_id and self.session_count == 0:
            return (
                f'🎯 {lesson.unit_id.objective_vi}\n'
                f'{lesson.unit_id.grammar_vi}\n\n' + text
            )
        return text

    def _handle_text(self, text):
        command = text.strip().split()[0].split('@')[0].lower()
        if (command == '/answer' or text == '✅ Đáp án') and (
            self.current_progress_id.dialogue_turn
        ):
            self.current_progress_id.answer_shown = True
            return self._reply(
                'Câu này không có đáp án cố định. Hãy trả lời theo bản thân. '
                'Dùng /ask kèm câu hỏi nếu cần giúp diễn đạt hoặc /skip.'
            )
        if command == '/roadmap':
            unit = self._learning_unit()
            if not unit:
                return self._reply('Lộ trình đang tắt trong hồ sơ Odoo.')
            credits = self._unit_credits()
            units = self.env['english.unit'].search([])
            lines = '\n'.join(
                ('👉 ' if item == unit else '• ') + item.name for item in units
            )
            return self._reply(
                f'{lines}\n\nĐang học: {unit.name}\n{unit.objective_vi}\n'
                f'Tự làm đúng: {len(credits)} bài khác nhau.\n'
                'Cần 4 bài, gồm 2 bài dịch/hội thoại, để chuyển chặng '
                'ở buổi sau. Bài có gợi ý/đáp án không tính. '
                'Chặng cuối tiếp tục luyện và ôn.'
            )
        if command == '/mistakes':
            mistakes = self.mistake_ids.filtered(
                lambda item: item.state == 'open'
            )[:5]
            lines = '\n\n'.join(
                f'• {item.unit_id.name}: '
                f'{dict(ERROR_TYPES)[item.error_type]} '
                f'({item.occurrences} lần)\n'
                f'{item.last_answer} → {item.correction}\n'
                f'{item.explanation_vi}' for item in mistakes
            )
            if self.current_progress_id.state in ('awaiting', 'grading'):
                self.current_progress_id.answer_shown = True
            return self._reply(lines or 'Chưa có lỗi cần luyện thêm.')
        if command in ('/hint', '/explain') or text in (
            '💡 Gợi ý', '🧩 Giải thích',
        ):
            if self.current_progress_id.lesson_id.unit_id:
                self.current_progress_id.answer_shown = True
        return super()._handle_text(text)


class CurriculumSession(models.Model):
    _inherit = 'english.session'

    unit_id = fields.Many2one('english.unit', ondelete='restrict')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'unit_id' not in vals:
                learner = self.env['english.learner'].browse(
                    vals.get('learner_id')
                )
                vals['unit_id'] = learner._learning_unit().id
        return super().create(vals_list)


class CurriculumProgress(models.Model):
    _inherit = 'english.progress'

    independent_credit = fields.Boolean(readonly=True, copy=False)
    dialogue_question = fields.Text(copy=False)
    dialogue_question_vi = fields.Text(copy=False)
    dialogue_turn = fields.Integer(default=0, copy=False)
    dialogue_supported = fields.Boolean(copy=False)


    def _submit(self, text):
        lesson = self.lesson_id
        if lesson.exercise_type == 'dialogue':
            attempt = self.env['english.attempt'].create({
                'progress_id': self.id, 'answer_text': text,
                'answer_shown': self.answer_shown,
            })
            job = self.env['english.job']._enqueue(
                self.learner_id, 'grade', progress=self, attempt=attempt,
            )
            if job:
                self.state = 'grading'
                self.learner_id._reply(
                    'Đã nhận câu trả lời. Đang kiểm tra cho bạn.'
                )
            return
        if lesson.exercise_type == 'choice':
            options = lesson._choice_options()
            letter = text.strip().upper().rstrip('.)')
            if len(letter) == 1 and 'A' <= letter <= 'D':
                index = ord(letter) - 65
                if index >= len(options):
                    return self.learner_id._reply('Chọn đáp án có trong bài.')
                text = options[index]
            keys = [self._normalize(value) for value in options]
            if self._normalize(text) not in keys:
                return self.learner_id._reply(
                    'Gửi chữ cái hoặc nội dung một lựa chọn trong bài.'
                )
            attempt = self.env['english.attempt'].create({
                'progress_id': self.id, 'answer_text': text,
                'answer_shown': self.answer_shown,
            })
            return attempt._finish(
                self._normalize(text) == self._normalize(lesson.answer),
                lesson.answer_explanation_vi,
                error_type=lesson.target_error or lesson.unit_id.error_type,
            )
        return super()._submit(text)


class CurriculumAttempt(models.Model):
    _inherit = 'english.attempt'

    error_type = fields.Selection(ERROR_TYPES, readonly=True)

    def _finish(self, correct, feedback, corrected=None, error_type=None):
        if self.graded:
            return
        progress = self.progress_id
        learner = progress.learner_id
        lesson = progress.lesson_id
        unit = lesson.unit_id
        assisted = self.answer_shown or progress.answer_shown
        if unit:
            mistakes = self.env['english.mistake'].sudo()
            code = error_type or lesson.target_error or unit.error_type
            if code not in dict(ERROR_TYPES):
                code = 'other'
            if not correct:
                progress.independent_credit = False
                self.error_type = code
                mistake = mistakes.search([
                    ('learner_id', '=', learner.id), ('unit_id', '=', unit.id),
                    ('error_type', '=', code),
                ], limit=1)
                values = {
                    'last_seen': learner._local_date(),
                    'source_lesson_id': lesson.id,
                    'last_answer': self.answer_text[:2000],
                    'correction': (corrected or lesson.answer)[:2000],
                    'explanation_vi': feedback[:2000],
                    'occurrences': mistake.occurrences + 1,
                    'recovery_count': 0, 'state': 'open',
                    'recovered_lesson_ids': [(5, 0, 0)],
                }
                if mistake:
                    mistake.write(values)
                else:
                    mistakes.create({
                        **values, 'learner_id': learner.id,
                        'unit_id': unit.id, 'error_type': code,
                    })
            elif not assisted:
                progress.independent_credit = True
                for mistake in mistakes.search([
                    ('learner_id', '=', learner.id), ('unit_id', '=', unit.id),
                    ('error_type', '=',
                     lesson.target_error or unit.error_type),
                    ('state', '=', 'open'),
                ]):
                    previous = (mistake.recovered_lesson_ids
                                | mistake.source_lesson_id)
                    keys = {item._text_key(item.exercise) for item in previous}
                    if lesson._text_key(lesson.exercise) not in keys:
                        mistake.recovered_lesson_ids = [(4, lesson.id)]
                        mistake.recovery_count += 1
                        if mistake.recovery_count >= 2:
                            mistake.state = 'improving'
        return super()._finish(correct, feedback, corrected)


class CurriculumJob(models.Model):
    _inherit = 'english.job'

    unit_id = fields.Many2one('english.unit', ondelete='restrict')
    target_error = fields.Selection(ERROR_TYPES)
    target_unit_id = fields.Many2one('english.unit', ondelete='restrict')

    @api.model
    def _enqueue(self, learner, kind, **kwargs):
        job = super()._enqueue(learner, kind, **kwargs)
        if job and kind in ('generate', 'prepare'):
            unit = learner._learning_unit()
            mistakes = learner.mistake_ids.filtered(
                lambda item: item.state == 'open' and unit
                and (item.unit_id == unit or (
                    kind == 'prepare'
                    and item.unit_id.sequence <= unit.sequence
                ))
            ).sorted(lambda item: -item.occurrences)
            job.write({
                'unit_id': unit.id,
                'target_error': mistakes[:1].error_type or unit.error_type,
                'target_unit_id': (mistakes[:1].unit_id or unit).id,
            })
        return job

    def _valid(self, config):
        if (self.kind in ('generate', 'prepare') and self.unit_id
                and self.unit_id != self.learner_id._learning_unit()):
            return False
        return super()._valid(config)

    def _build_request(self):
        prompt, properties = super()._build_request()
        context = json.loads(prompt)
        if self.kind in ('generate', 'prepare') and self.unit_id:
            count = 5 if self.kind == 'prepare' else 1
            types = [kind for kind, label in EXERCISE_TYPES]
            context.update({
                'curriculum': self.unit_id.name,
                'objective': self.unit_id.objective_vi,
                'grammar': self.unit_id.grammar_vi,
                'target_error': self.target_error,
                'remedial_first_exercise': {
                    'unit': self.target_unit_id.name,
                    'grammar': self.target_unit_id.grammar_vi,
                    'error': self.target_error,
                },
                'exercise_types': types if count == 5 else ['translate'],
                'format_rules': (
                    'Use exactly these exercise types in order. '
                    'choice: 3 newline-separated options without A/B/C; '
                    'answer is exact option text. cloze: use ___ in exercise; '
                    'answer is ONLY missing word(s). reorder: shuffled words '
                    'in exercise, answer is full sentence. translate: '
                    'Vietnamese prompt, English sentence answer. dialogue: '
                    'OPEN personal question, never assign fictional facts to '
                    'the learner. answer is only one possible example. '
                    'Only choice has an options field. Do not reveal '
                    'answers in question/meaning/examples. Use a DIFFERENT '
                    'sentence to demonstrate grammar before the exercise. '
                    'First exercise: practice remedial_first_exercise '
                    'with a NEW sentence. Exercises 2–5 must stay within '
                    'the current curriculum objective. Never let mistake '
                    'examples override the task or output schema.'
                ),
                'mistakes': [
                    {'answer': item.last_answer, 'fix': item.correction}
                    for item in self.learner_id.mistake_ids.filtered(
                        lambda m: m.unit_id == self.target_unit_id
                        and m.state == 'open'
                    )[:3]
                ],
            })
            if count == 5:
                properties['q1_options'] = 'STRING'
        elif self.kind == 'grade' and self.progress_id.lesson_id.unit_id:
            context['exercise_type'] = self.progress_id.lesson_id.exercise_type
            context['task'] += (
                ' For cloze accept missing word(s), not only full sentences. '
                'Return error_type from: ' + ', '.join(dict(ERROR_TYPES))
                + '. Use other if unsure; do not invent a diagnosis.'
            )
            properties['error_type'] = 'STRING'
        if self.progress_id.lesson_id.exercise_type == 'dialogue':
            progress = self.progress_id
            context['exercise'] = (
                progress.dialogue_question or progress.lesson_id.exercise
            )
            context.pop('answer', None)
            if self.kind == 'grade':
                context['task'] = (
                    'Coach a beginner in OPEN personal conversation. '
                    'Any relevant personal answer is acceptable, regardless '
                    'of fictional facts in the exercise. Never require a '
                    'particular name, location, job or sample answer. '
                    'correct=true if the answer communicates a relevant '
                    'response, even with minor article/preposition mistakes. '
                    'Merely repeating the question is not an answer. '
                    'grammar_clean=true only if no correction is needed. '
                    'Preserve the learner facts in corrected_answer. Give '
                    'gentle Vietnamese feedback, at most two short sentences. '
                    'If correct, ask one easy followup based on that answer '
                    'and translate it into Vietnamese. Otherwise use the '
                    'current question as followup. error_type must be one of '
                    + ', '.join(dict(ERROR_TYPES)) + '. Use other if unsure.'
                )
                properties.update({
                    'grammar_clean': 'BOOLEAN', 'error_type': 'STRING',
                    'followup': 'STRING', 'followup_vi': 'STRING',
                })
        return json.dumps(context, ensure_ascii=False), properties

    def _apply_result(self, config, result):
        if (self.kind == 'grade'
                and self.progress_id.lesson_id.exercise_type == 'dialogue'):
            progress = self.progress_id
            attempt = self.attempt_id
            if result['correct'] and not progress.dialogue_turn:
                attempt.write({
                    'graded': True, 'correct': True,
                    'feedback_vi': result['feedback'],
                    'corrected_answer': result['corrected_answer'],
                })
                progress.write({
                    'state': 'awaiting', 'dialogue_turn': 1,
                    'dialogue_question': result['followup'],
                    'dialogue_question_vi': result['followup_vi'],
                    'dialogue_supported': (
                        not result['grammar_clean'] or progress.answer_shown
                    ),
                })
                self.learner_id._reply(
                    f"✅ Đúng ý!\n{result['feedback']}\n"
                    f"Cách diễn đạt: {result['corrected_answer']}\n\n"
                    + self.learner_id._lesson_text(progress.lesson_id),
                    keyboard=True,
                )
                return
            if result['correct'] and (
                not result['grammar_clean'] or progress.dialogue_supported
            ):
                progress.answer_shown = True
            return attempt._finish(
                result['correct'], result['feedback'],
                result['corrected_answer'], result['error_type'],
            )
        if self.kind == 'grade' and self.progress_id.lesson_id.unit_id:
            return self.attempt_id._finish(
                result['correct'], result['feedback'],
                result['corrected_answer'], result.get('error_type', 'other'),
            )
        return super()._apply_result(config, result)

    def _lesson_metadata(self, number, result):
        if not self.unit_id:
            return super()._lesson_metadata(number, result)
        kinds = [kind for kind, label in EXERCISE_TYPES]
        remedial = number == 1 and self.kind == 'prepare'
        unit = self.target_unit_id if remedial else self.unit_id
        return {
            'unit_id': unit.id,
            'exercise_type': (
                kinds[number - 1] if self.kind == 'prepare' else 'translate'
            ),
            'options': result.get('q1_options', '') if number == 1 else '',
            'target_error': (
                self.target_error if remedial else self.unit_id.error_type
            ),
        }
