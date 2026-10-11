import hashlib
import secrets
from datetime import timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class EnglishLearner(models.Model):
    _name = 'english.learner'
    _description = 'English Learner'

    name = fields.Char(required=True)
    chat_id = fields.Char(copy=False, readonly=True, index=True)
    bot_hash = fields.Char(copy=False, readonly=True)
    timezone = fields.Selection(
        [(tz, tz) for tz in pytz.all_timezones],
        default='Asia/Bangkok', required=True,
    )
    send_hour = fields.Integer(default=8, required=True)
    send_minute = fields.Integer(default=0, required=True)
    level = fields.Selection([
        ('starter', 'Mất gốc'), ('beginner', 'Cơ bản'),
    ], default='starter', required=True)
    topic = fields.Selection([
        ('daily', 'Đời sống'), ('developer', 'Công việc dev'),
    ], default='daily', required=True)
    current_session_id = fields.Many2one(
        'english.session', readonly=True, copy=False, ondelete='set null',
    )
    session_ids = fields.One2many('english.session', 'learner_id')
    command_epoch = fields.Integer(default=0, copy=False)
    session_active = fields.Boolean(default=False, copy=False)
    session_count = fields.Integer(default=0, copy=False)
    session_correct = fields.Integer(default=0, copy=False)
    session_skipped = fields.Integer(default=0, copy=False)
    session_errors = fields.Integer(default=0, copy=False)
    session_notes = fields.Text(copy=False)
    paused = fields.Boolean(default=False)
    active = fields.Boolean(default=True)
    last_daily_date = fields.Date(readonly=True)
    pairing_hash = fields.Char(copy=False, groups='base.group_system')
    pairing_bot_hash = fields.Char(copy=False, groups='base.group_system')
    pairing_expiry = fields.Datetime(copy=False)
    pairing_command = fields.Char(copy=False, readonly=True)
    progress_ids = fields.One2many('english.progress', 'learner_id')
    current_progress_id = fields.Many2one(
        'english.progress', readonly=True, copy=False,
    )
    progress_count = fields.Integer(compute='_compute_counts')
    mastered_count = fields.Integer(compute='_compute_counts')

    _chat_unique = models.Constraint(
        'UNIQUE(chat_id)', 'Telegram chat already belongs to a learner.'
    )

    @api.depends('progress_ids', 'progress_ids.review_step')
    def _compute_counts(self):
        for learner in self:
            learner.progress_count = len(learner.progress_ids)
            learner.mastered_count = len(learner.progress_ids.filtered(
                lambda progress: progress.review_step >= 4
            ))

    @api.constrains('send_hour', 'send_minute', 'current_progress_id')
    def _check_learner(self):
        for learner in self:
            if not 0 <= learner.send_hour <= 23:
                raise ValidationError('Hour must be between 0 and 23.')
            if not 0 <= learner.send_minute <= 59:
                raise ValidationError('Minute must be between 0 and 59.')
            if (
                learner.current_progress_id
                and learner.current_progress_id.learner_id != learner
            ):
                raise ValidationError('Progress belongs to another learner.')

    def _lock(self):
        self.ensure_one()
        self.env.cr.execute(
            'SELECT id FROM english_learner WHERE id = %s FOR UPDATE',
            [self.id],
        )
        self.invalidate_recordset()

    def action_pair(self):
        self.check_access('write')
        self.ensure_one()
        self._lock()
        config = self.env['english.configuration']._get_config()
        if not config.telegram_token:
            raise UserError('Configure the bot token first.')
        code = secrets.token_urlsafe(24)
        self.write({
            'pairing_hash': hashlib.sha256(code.encode()).hexdigest(),
            'pairing_bot_hash': hashlib.sha256(
                config.telegram_token.encode()
            ).hexdigest(),
            'pairing_expiry': fields.Datetime.now() + timedelta(minutes=10),
            'pairing_command': f'/connect {code}',
        })
        return config._notification(
            'Copy /connect into your private bot chat.'
        )

    def action_send_lesson(self):
        self.check_access('write')
        for learner in self:
            learner._begin_session()

    def action_generate_lesson(self):
        self.check_access('write')
        for learner in self:
            learner._lock()
            pending = self.env['english.job'].search([
                ('learner_id', '=', learner.id),
                ('kind', '=', 'generate'),
                ('unit_id', '=', learner._learning_unit().id),
                ('state', 'in', ['pending', 'running']),
            ], limit=1)
            draft = self.env['english.lesson'].search([
                ('generated_for_id', '=', learner.id), ('state', '=', 'draft'),
                ('unit_id', '=', learner._learning_unit().id),
            ], limit=1)
            if not pending and not draft:
                self.env['english.job']._enqueue(learner, 'generate')

    def _reply(self, text, keyboard=False, automatic=False):
        self.ensure_one()
        return self.env['english.delivery']._enqueue(
            self, text, keyboard=keyboard, automatic=automatic,
            session=self.current_session_id if self.session_active else None
        )

    def _begin_session(self, automatic=False, planned=None):
        self.ensure_one()
        self._lock()
        if self.paused or not self.chat_id:
            return self._start_lesson(automatic=automatic)
        if not self.session_active:
            if not planned:
                planned = self.env['english.session'].sudo().search([
                    ('learner_id', '=', self.id),
                    ('daily_date', '=', self._local_date()),
                    ('state', 'in', ['ready', 'preparing', 'failed']),
                ], limit=1)
            session = planned or self.env['english.session'].sudo().create({
                'learner_id': self.id, 'study_date': self._local_date(),
                'level': self.level, 'topic': self.topic,
            })
            session.state = 'active'
            self.current_session_id = session
            self.write({
                'session_active': True, 'session_count': 0,
                'session_correct': 0, 'session_skipped': 0,
                'session_errors': 0,
                'session_notes': False,
            })
        return self._start_lesson(automatic=automatic)

    def _session_advance(self, progress, skipped=False):
        self.ensure_one()
        if not self.session_active or self.paused:
            return
        count = self.session_count + 1
        notes = (self.session_notes or '') + (
            f'• {progress.lesson_id.name}: '
            f'{progress.lesson_id.answer}\n'
            f'  Ngữ pháp: {progress.lesson_id.grammar_name}\n'
        )
        self.write({
            'session_count': count,
            'session_correct': self.session_correct + int(
                not skipped and not progress.answer_shown
            ),
            'session_skipped': self.session_skipped + int(skipped),
            'session_notes': notes,
        })
        self._save_session()
        if self.current_session_id:
            self.current_session_id.completed_ids = [
                (4, progress.lesson_id.id),
            ]
        if count >= 5:
            if self.current_session_id:
                self.current_session_id.write({
                    'state': 'done', 'ended_at': fields.Datetime.now(),
                })
            self.session_active = False
            self._reply(
                f'🎉 Hoàn thành buổi học 5 câu!\n'
                f'Tự trả lời đúng: {self.session_correct}/5\n'
                f'Bỏ qua: {self.session_skipped}\n'
                f'Lượt cần sửa: {self.session_errors}\n'
                'Câu đã xem đáp án không tính tự trả lời đúng.\n\n'
                f'Ôn lại các câu mẫu:\n{notes}\n'
                'Gửi /lesson để học buổi tiếp theo.', keyboard=True,
            )
        else:
            self._start_lesson()

    def _local_date(self):
        now = pytz.UTC.localize(fields.Datetime.now())
        return now.astimezone(pytz.timezone(self.timezone)).date()

    def _save_session(self):
        if not self.current_session_id and self.session_active:
            sessions = self.env['english.session'].sudo()
            self.current_session_id = sessions.create({
                'learner_id': self.id, 'study_date': self._local_date(),
                'level': self.level, 'topic': self.topic,
            })
        if self.current_session_id:
            self.current_session_id.write({
                'count': self.session_count, 'correct': self.session_correct,
                'skipped': self.session_skipped, 'errors': self.session_errors,
                'notes': self.session_notes,
            })

    def _stop_session(self):
        self._lock()
        self._save_session()
        if self.current_session_id.state == 'active':
            self.current_session_id.write({
                'state': 'stopped', 'ended_at': fields.Datetime.now(),
            })
        self.write({
            'session_active': False, 'command_epoch': self.command_epoch + 1,
        })
        jobs = self.env['english.job'].search([
            ('learner_id', '=', self.id),
            ('state', 'in', ['pending', 'running']),
        ])
        future = jobs.filtered(
            lambda job: not self.paused and job.kind == 'prepare'
            and job.session_id.daily_date
            and job.session_id.daily_date > self._local_date()
        )
        future.command_epoch = self.command_epoch
        (jobs - future).write({
            'state': 'skipped', 'error_code': 'learner_stopped',
        })
        plans = self.env['english.session'].sudo().search([
            ('learner_id', '=', self.id),
            ('state', 'in', ['preparing', 'ready', 'failed']),
        ]).filtered(
            lambda plan: self.paused
            or not plan.daily_date or plan.daily_date <= self._local_date()
        )
        plans.write({'state': 'stopped', 'ended_at': fields.Datetime.now()})
        if self.current_progress_id.state == 'grading':
            self.current_progress_id.state = 'awaiting'
        self.env['english.delivery'].search([
            ('learner_id', '=', self.id),
            ('state', 'in', ['pending', 'sending']),
        ]).write({'state': 'skipped'})

    def _daily_plan(self, day):
        self._lock()
        sessions = self.env['english.session'].sudo()
        plan = sessions.search([
            ('learner_id', '=', self.id), ('daily_date', '=', day),
        ], limit=1)
        if not plan:
            plan = sessions.create({
                'learner_id': self.id, 'study_date': day, 'daily_date': day,
                'state': 'preparing', 'level': self.level, 'topic': self.topic,
            })
            job = self.env['english.job']._enqueue(
                self, 'prepare', session=plan,
            )
            if not job:
                plan.state = 'failed'
        return plan

    @api.model
    def _cron_prepare(self):
        config = self.env['english.configuration']._get_config()
        if not config.enabled or not config.daily_ai_enabled:
            return
        now = pytz.UTC.localize(fields.Datetime.now())
        for learner in self.sudo().search([
            ('paused', '=', False), ('chat_id', '!=', False),
        ]):
            local = now.astimezone(pytz.timezone(learner.timezone))
            # Only today's due slot or tomorrow's slot within 30 minutes.
            for day in (local.date(), local.date() + timedelta(days=1)):
                zone = pytz.timezone(learner.timezone)
                scheduled = zone.localize(fields.Datetime.to_datetime(day))
                scheduled += timedelta(
                    hours=learner.send_hour, minutes=learner.send_minute,
                )
                if scheduled <= local + timedelta(minutes=30):
                    learner._daily_plan(day)
        # Expire unused plans, keeping an unfinished active session.
        self.env['english.session'].sudo().search([
            ('state', 'in', ['ready', 'preparing']),
            ('daily_date', '<', fields.Date.today() - timedelta(days=1)),
        ]).write({'state': 'stopped', 'ended_at': fields.Datetime.now()})

    def _lesson_text(self, lesson):
        prefix = (
            f'📚 Câu {self.session_count + 1}/5\n\n'
            if self.session_active else ''
        )
        return prefix + lesson._render()

    def _start_lesson(self, automatic=False):
        self.ensure_one()
        self._lock()
        if self.paused or not self.chat_id:
            if not automatic:
                raise UserError('Pair the learner and resume learning first.')
            return False
        config = self.env['english.configuration']._get_config()
        current_hash = hashlib.sha256(
            (config.telegram_token or '').encode()
        ).hexdigest()
        if self.bot_hash != current_hash:
            if not automatic:
                raise UserError('Bot changed. Pair this learner again.')
            return False
        progress = self.current_progress_id
        if progress and progress.state in ('awaiting', 'grading'):
            if progress.state == 'awaiting':
                self._reply(
                    self._lesson_text(progress.lesson_id), keyboard=True,
                    automatic=automatic,
                )
            if automatic and progress.state == 'grading':
                self._reply(
                    'Bài trước đang chấm. Bạn có thể /skip hoặc /stop.',
                    automatic=True,
                )
            return True
        progress = self.env['english.progress'].search([
            ('learner_id', '=', self.id), ('state', '=', 'done'),
            ('lesson_id.active', '=', True),
            ('lesson_id.topic', '=', self.topic),
            ('lesson_id.level', '=', self.level),
            ('lesson_id.state', '=', 'ready'),
            ('review_date', '<=', fields.Date.today()),
        ], order='review_date, id', limit=1)
        plan = self.current_session_id
        unit = self._learning_unit()
        seen = {
            lesson._text_key(lesson.exercise)
            for lesson in self.progress_ids.lesson_id
        }
        planned = plan.lesson_ids.filtered(
            lambda lesson: lesson.state == 'ready' and lesson.active
            and (lesson.unit_id == unit or (
                unit and lesson.unit_id
                and lesson.unit_id.sequence < unit.sequence
                and plan.unit_id == unit
            ))
            and lesson not in self.progress_ids.lesson_id
            and lesson._text_key(lesson.exercise) not in seen
        ).sorted('sequence')[:1]
        if self.session_active and self.session_count > 0:
            progress = self.env['english.progress']
        if progress:
            progress.write({
                'state': 'awaiting', 'answer_shown': False,
                'dialogue_turn': 0, 'dialogue_question': False,
                'dialogue_question_vi': False, 'dialogue_supported': False,
            })
        else:
            lesson = planned or self.env['english.lesson'].search([
                ('state', '=', 'ready'), ('level', '=', self.level),
                ('unit_id', '=', unit.id),
                ('topic', '=', self.topic),
                ('id', 'not in', self.progress_ids.lesson_id.ids),
                '|', ('generated_for_id', '=', False),
                ('generated_for_id', '=', self.id),
            ]).filtered(
                lambda item: item._text_key(item.exercise) not in seen
            )[:1]
            if not lesson:
                self.action_generate_lesson()
                if self._send_waiting_review(automatic=automatic):
                    return True
                if not automatic:
                    self._reply(
                        'Đang chuẩn bị bài mới hoặc chờ duyệt ở Odoo.'
                        if config.require_approval
                        else 'Đang tạo bài mới. Bài sẽ tự gửi khi sẵn sàng.'
                    )
                return True
            progress = self.env['english.progress'].create({
                'learner_id': self.id, 'lesson_id': lesson.id,
            })
        self.current_progress_id = progress
        self._reply(
            self._lesson_text(progress.lesson_id),
            keyboard=True, automatic=automatic
        )
        return True

    def _send_waiting_review(self, automatic=False):
        # Keep a session moving without awarding early recall credit.
        if not self.session_active or self.session_count > 0:
            return False
        excluded = self.current_session_id.completed_ids
        excluded |= self.current_progress_id.lesson_id
        progress = self.env['english.progress'].search([
            ('learner_id', '=', self.id), ('state', '=', 'done'),
            ('lesson_id', 'not in', excluded.ids),
            ('write_date', '<',
             fields.Datetime.now() - timedelta(hours=24)),
            ('lesson_id.active', '=', True),
            ('lesson_id.state', '=', 'ready'),
            ('lesson_id.unit_id', '=', self._learning_unit().id),
            ('lesson_id.level', '=', self.level),
            ('lesson_id.topic', '=', self.topic),
        ], order='review_step, review_date, id', limit=1)
        if not progress:
            return False
        progress.write({
            'state': 'awaiting', 'answer_shown': True,
            'dialogue_turn': 0, 'dialogue_question': False,
            'dialogue_question_vi': False, 'dialogue_supported': False,
        })
        self.current_progress_id = progress
        self._reply(
            '🔄 Trong lúc AI tạo bài mới, mình ôn một câu đã học. '
            'Lượt ôn sớm này không tăng mức ghi nhớ.\n\n'
            + self._lesson_text(progress.lesson_id),
            keyboard=True, automatic=automatic,
        )
        return True

    @api.model
    def _cron_daily(self):
        config = self.env['english.configuration']._get_config()
        if not config.enabled:
            return
        learners = self.sudo().search([
            ('paused', '=', False), ('chat_id', '!=', False),
        ])
        now = pytz.UTC.localize(fields.Datetime.now())
        for learner in learners:
            local = now.astimezone(pytz.timezone(learner.timezone))
            learner._lock()
            if learner.last_daily_date == local.date():
                continue
            if (local.hour, local.minute) < (
                learner.send_hour, learner.send_minute
            ):
                continue
            plan = self.env['english.session'].sudo().search([
                ('learner_id', '=', learner.id),
                ('daily_date', '=', local.date()),
            ], limit=1)
            if not plan and config.daily_ai_enabled:
                plan = learner._daily_plan(local.date())
            if plan.state == 'stopped':
                learner.last_daily_date = local.date()
                continue
            if learner._begin_session(automatic=True, planned=plan):
                learner.last_daily_date = local.date()

    def _handle_text(self, text):
        self.ensure_one()
        command = text.strip().split()[0].split('@')[0].lower()
        buttons = {
            '📖 Bài học': '/lesson', '🧩 Giải thích': '/explain',
            '✅ Đáp án': '/answer', '📊 Tiến độ': '/progress',
            '💡 Gợi ý': '/hint', '⏭ Bỏ qua': '/skip',
            '🛑 Dừng buổi': '/stop',
            '⏸ Tạm nghỉ': '/pause', '▶️ Học tiếp': '/resume',
        }
        command = buttons.get(text, command)
        if command in ('/start', '/help'):
            return self._reply(
                'Mỗi buổi 5 câu, đúng thì tự chuyển câu tiếp.\n'
                '/hint — Gợi ý; /skip — Bỏ qua; /stop — Dừng buổi\n'
                '/lesson — Học hoặc ôn bài\n'
                '/explain — Từ vựng, cụm từ, ngữ pháp\n'
                '/answer — Đáp án bài tập\n'
                '/ask <câu hỏi> — Hỏi thêm về bài\n'
                '/progress — Tiến độ\n'
                '/roadmap — Lộ trình; /mistakes — Sổ lỗi sai\n'
                '/pause, /resume — Tạm nghỉ, học tiếp\n'
                'Gửi câu trả lời bằng tin nhắn thường.', keyboard=True,
            )
        if command == '/stop':
            self._stop_session()
            return self._reply(
                'Đã dừng buổi học. Gửi /lesson để bắt đầu lại; '
                'câu chưa xong được giữ lại.', keyboard=True,
            )
        if command in ('/pause', '/resume'):
            self.paused = command == '/pause'
            if self.paused:
                self._stop_session()
            else:
                # Resume future daily plans without creating duplicate slots.
                for plan in self.env['english.session'].sudo().search([
                    ('learner_id', '=', self.id), ('state', '=', 'stopped'),
                    ('daily_date', '>', self._local_date()),
                ]):
                    plan.state = (
                        'ready' if plan.generation_done else 'preparing'
                    )
                    if not plan.generation_done:
                        self.env['english.job']._enqueue(
                            self, 'prepare', session=plan,
                        )
            return self._reply(
                'Đã tạm nghỉ.' if self.paused else (
                    'Đã bật lịch học. Gửi /lesson để tiếp tục bài hiện tại.'
                )
            )
        if command == '/progress':
            return self._reply(
                f'Bạn đã học {self.progress_count} bài.\n'
                f'{self.mastered_count} bài đã qua 4 lượt nhớ đúng.'
            )
        if self.paused:
            return self._reply('Đang tạm nghỉ. Gửi /resume để học tiếp.')
        if command == '/lesson':
            self._begin_session()
            return
        progress = self.current_progress_id
        if not progress:
            return self._reply('Gửi /lesson để bắt đầu bài đầu tiên.')
        if command == '/hint':
            return self._reply(
                f'💡 {progress.lesson_id.grammar_name}\n'
                f'{progress.lesson_id.grammar_vi}\n\n'
                f'Từ gợi ý: {progress.lesson_id.vocabulary_vi}'
            )
        if command == '/skip':
            if progress.state not in ('awaiting', 'grading'):
                return self._reply('Gửi /lesson để học câu tiếp theo.')
            self.env['english.job'].search([
                ('progress_id', '=', progress.id),
                ('state', 'in', ['pending', 'running']),
            ]).write({'state': 'skipped', 'error_code': 'question_skipped'})
            progress.write({
                'state': 'done', 'answer_shown': True,
                'review_date': fields.Date.today() + timedelta(days=1),
            })
            self._reply(progress.lesson_id._render('answer'))
            if self.session_active:
                self._session_advance(progress, skipped=True)
            else:
                self._reply('Gửi /lesson để học tiếp.')
            return
        if command in ('/explain', '/answer'):
            if command == '/answer':
                progress.answer_shown = True
            return self._reply(progress.lesson_id._render(
                'answer' if command == '/answer' else 'explain'
            ))
        if command == '/ask':
            question = text.partition(' ')[2].strip()
            if not question:
                return self._reply('Ví dụ: /ask Vì sao câu này dùng am?')
            self.env['english.job']._enqueue(
                self, 'explain', progress=progress, text=question
            )
            return self._reply('Đang chuẩn bị giải thích cho bạn.')
        if text.startswith('/'):
            return self._reply('Lệnh chưa hỗ trợ. Gửi /help để xem hướng dẫn.')
        if progress.state != 'awaiting':
            return self._reply(
                'Đang chấm bài hoặc đã hoàn thành. Gửi /lesson.'
            )
        progress._submit(text)
