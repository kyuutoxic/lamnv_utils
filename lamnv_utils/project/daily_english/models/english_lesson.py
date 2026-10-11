import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


LESSON_FIELDS = (
    'name', 'question', 'meaning_vi', 'situation_vi', 'sample_answers',
    'vocabulary_vi', 'phrases_vi', 'grammar_name', 'grammar_vi',
    'common_mistake_vi', 'exercise', 'answer', 'answer_explanation_vi',
)


class EnglishLesson(models.Model):
    _name = 'english.lesson'
    _description = 'English Lesson'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    level = fields.Selection([
        ('starter', 'Mất gốc'), ('beginner', 'Cơ bản'),
    ], default='starter', required=True)
    topic = fields.Selection([
        ('daily', 'Đời sống'), ('developer', 'Công việc dev'),
    ], default='daily', required=True)
    state = fields.Selection([
        ('draft', 'Nháp'), ('ready', 'Sẵn sàng'),
    ], default='draft', required=True)
    question = fields.Text(required=True)
    meaning_vi = fields.Text(required=True)
    situation_vi = fields.Text(required=True)
    sample_answers = fields.Text(required=True)
    vocabulary_vi = fields.Text(required=True)
    phrases_vi = fields.Text(required=True)
    grammar_name = fields.Char(required=True)
    grammar_vi = fields.Text(required=True)
    common_mistake_vi = fields.Text(required=True)
    exercise = fields.Text(required=True)
    answer = fields.Text(required=True)
    accepted_answers = fields.Text(
        help='One accepted answer per line; other answers use Gemini.'
    )
    answer_explanation_vi = fields.Text(required=True)
    generated = fields.Boolean(readonly=True)
    generated_for_id = fields.Many2one(
        'english.learner', readonly=True, ondelete='cascade',
    )
    active = fields.Boolean(default=True)

    @api.constrains(*LESSON_FIELDS)
    def _check_content(self):
        for lesson in self:
            for name in LESSON_FIELDS:
                if not (lesson[name] or '').strip():
                    raise ValidationError('Lesson sections cannot be empty.')
                if len(lesson[name]) > 4000:
                    raise ValidationError('Each section is limited to 4000.')

    @api.model
    def _validate_generated(self, values):
        answer = self._text_key(values['answer'])
        if answer and answer in self._text_key(values['sample_answers']):
            raise ValidationError('AI examples disclose the exercise answer.')

    @api.model
    def _text_key(self, text):
        return re.sub(r'[^\w]+', ' ', text.casefold()).strip()

    def action_approve(self):
        self.write({'state': 'ready'})

    def _render(self, section='lesson'):
        self.ensure_one()
        if section == 'explain':
            return (
                f'🧩 Từ vựng\n{self.vocabulary_vi}\n\n'
                f'Cụm từ\n{self.phrases_vi}\n\n'
                f'⏳ {self.grammar_name}\n{self.grammar_vi}\n\n'
                f'Lỗi thường gặp\n{self.common_mistake_vi}'
            )
        if section == 'answer':
            return (
                f'✅ Đáp án mẫu\n{self.answer}\n\n'
                f'{self.answer_explanation_vi}'
            )
        # Also protect existing/custom lessons created before validation.
        answer = self._text_key(self.answer)
        examples = '\n'.join(
            line for line in self.sample_answers.splitlines()
            if self.exercise_type in ('choice', 'cloze')
            or answer not in self._text_key(line)
        ) or 'Xem từ vựng và công thức bằng nút Gợi ý.'
        return (
            f'📘 {self.name}\n{self.situation_vi}\n\n'
            f'❓ {self.question}\n🇻🇳 {self.meaning_vi}\n\n'
            f'💬 Ví dụ minh họa\n{examples}\n\n'
            f'✍️ Bài tập\n{self.exercise}\n\n'
            'Gửi câu trả lời của bạn hoặc bấm nút bên dưới.'
        )
