import hashlib
import json
import uuid
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from .english_lesson import LESSON_FIELDS


class EnglishJob(models.Model):
    _name = 'english.job'
    _description = 'English AI Task'
    _order = 'priority, id'
    _rec_name = 'kind'

    learner_id = fields.Many2one(
        'english.learner', required=True, ondelete='cascade', index=True,
    )
    kind = fields.Selection([
        ('generate', 'Tạo bài'), ('prepare', 'Chuẩn bị buổi học'),
        ('grade', 'Chấm bài'), ('explain', 'Giải thích thêm'),
    ], required=True)
    session_id = fields.Many2one('english.session', ondelete='set null')
    command_epoch = fields.Integer()
    bot_hash = fields.Char()
    request_level = fields.Char()
    request_topic = fields.Char()
    lease_token = fields.Char(copy=False)
    priority = fields.Integer(default=10, index=True)
    progress_id = fields.Many2one('english.progress', ondelete='cascade')
    attempt_id = fields.Many2one('english.attempt', ondelete='cascade')
    input_text = fields.Text()
    state = fields.Selection([
        ('pending', 'Chờ xử lý'), ('running', 'Đang gọi AI'),
        ('done', 'Hoàn thành'), ('failed', 'Lỗi'), ('skipped', 'Bỏ qua'),
    ], default='pending', required=True, index=True)
    calls = fields.Integer(default=0, readonly=True)
    tokens = fields.Integer(default=0, readonly=True)
    error_code = fields.Char(readonly=True)
    next_run = fields.Datetime(default=fields.Datetime.now, index=True)

    @api.model
    def _enqueue(self, learner, kind, progress=None, attempt=None, text=None,
                 session=None):
        learner._lock()
        if self.search_count([
            ('learner_id', '=', learner.id),
            ('state', 'in', ['pending', 'running']),
        ]) >= 5:
            if kind != 'prepare':
                learner._reply('Đang có nhiều yêu cầu. Hãy thử lại sau.')
            return self.browse()
        config = self.env['english.configuration']._get_config()
        job = self.create({
            'learner_id': learner.id, 'kind': kind,
            'progress_id': progress.id if progress else False,
            'attempt_id': attempt.id if attempt else False,
            'input_text': text,
            'session_id': (session or (
                learner.current_session_id if learner.session_active
                else self.env['english.session']
            )).id,
            'command_epoch': learner.command_epoch,
            'bot_hash': hashlib.sha256(
                (config.telegram_token or '').encode()
            ).hexdigest(),
            'request_level': learner.level, 'request_topic': learner.topic,
            'priority': 0 if kind == 'grade' else 10,
        })
        job._wake_worker()
        return job

    def _valid(self, config):
        self.ensure_one()
        learner = self.learner_id
        if (
            not learner.active or learner.paused
            or learner.command_epoch != self.command_epoch
            or learner.level != self.request_level
            or learner.topic != self.request_topic
            or (self.session_id and self.session_id.state in (
                'stopped', 'done',
            ))
            or self.bot_hash != hashlib.sha256(
                (config.telegram_token or '').encode()
            ).hexdigest()
        ):
            return False
        if (
            self.kind == 'prepare' and self.session_id.daily_date
            and self.session_id.daily_date < learner._local_date()
        ):
            return False
        if self.kind == 'grade':
            return self.attempt_id._can_grade()
        if self.kind == 'explain':
            return self.progress_id == learner.current_progress_id
        return True

    def _release_question(self):
        if self.kind == 'grade' and self.attempt_id._can_grade():
            self.progress_id.state = 'awaiting'

    def _wake_worker(self, at=None):
        interactive = self.kind in ('grade', 'explain')
        xmlid = (
            'daily_english.cron_english_interactive' if interactive
            else 'daily_english.cron_english_jobs'
        )
        cron = self.env.ref(xmlid, raise_if_not_found=False)
        if not cron:
            cron = self.env.ref('daily_english.cron_english_jobs')
        cron._trigger(at=at)

    @api.model
    def _wake_due_workers(self):
        for kinds in (['grade', 'explain'], ['generate', 'prepare']):
            job = self.sudo().search([
                ('state', '=', 'pending'), ('kind', 'in', kinds),
                ('next_run', '<=', fields.Datetime.now()),
            ], limit=1)
            if job:
                job._wake_worker()

    @api.model
    def _cron_process(self, interactive=None):
        config = self.env['english.configuration']._get_config()
        self.env.cr.execute(
            'SELECT pg_try_advisory_xact_lock(hashtext(%s))',
            ['daily_english.gemini_worker'],
        )
        if not self.env.cr.fetchone()[0]:
            # Another worker is briefly claiming quota; retry without
            # waiting for the one-minute fallback cron.
            xmlid = (
                'daily_english.cron_english_interactive' if interactive
                else 'daily_english.cron_english_jobs'
            )
            cron = self.env.ref(xmlid, raise_if_not_found=False)
            if cron:
                cron._trigger(at=fields.Datetime.now() + timedelta(seconds=1))
            return
        # Recover a worker killed after claiming a request.
        for stale in self.sudo().search([
            ('state', '=', 'running'),
            ('next_run', '<=', fields.Datetime.now()),
        ], limit=20):
            stale.learner_id._lock()
            stale.invalidate_recordset()
            stale._failure(config, 'worker_interrupted')
        domain = [
            ('state', '=', 'pending'),
            ('next_run', '<=', fields.Datetime.now()),
        ]
        if interactive is not None:
            domain.append((
                'kind', 'in' if interactive else 'not in',
                ['grade', 'explain'],
            ))
        job = self.sudo().search(domain, limit=1)
        if not job:
            return
        job.learner_id._lock()
        job.invalidate_recordset()
        if job.state != 'pending':
            return
        if not job._valid(config):
            job._release_question()
            job.state = 'skipped'
        else:
            start = fields.Datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0,
            )
            used = self.env['english.api.usage'].sudo().search_count([
                ('create_date', '>=', start),
            ])
            if config.daily_api_limit and used >= config.daily_api_limit:
                job._quota_exhausted(start + timedelta(days=1))
            else:
                lease = uuid.uuid4().hex
                job.write({
                    'lease_token': lease,
                    'state': 'running', 'calls': job.calls + 1,
                    'next_run': fields.Datetime.now() + timedelta(minutes=5),
                })
                usage = self.env['english.api.usage'].sudo().create({
                    'job_id': job.id,
                })
                # Persist claim/quota and RELEASE learner locks before HTTP.
                self.env['ir.cron']._commit_progress(remaining=1)
                try:
                    job._process(config)
                    usage.tokens = job.tokens
                except (UserError, ValidationError) as exc:
                    self.env['ir.cron']._commit_progress(remaining=1)
                    self.env.invalidate_all()
                    job.learner_id._lock()
                    job.invalidate_recordset()
                    if job.lease_token == lease:
                        code = getattr(exc, 'api_error_code', None)
                        status = getattr(exc, 'gemini_status_code', None)
                        if not code:
                            code = (
                                f'http_{status}' if status
                                else 'invalid_lesson'
                                if isinstance(exc, ValidationError)
                                else 'ai_unavailable_or_invalid'
                            )
                        job._failure(config, code)
        self._wake_due_workers()

        self.env['ir.cron']._commit_progress(1, remaining=0)

    def _quota_exhausted(self, reset):
        if self.kind in ('grade', 'explain'):
            self._release_question()
            self.write({'state': 'failed', 'error_code': 'daily_quota'})
            self.learner_id._reply(
                'Đã hết lượt AI hôm nay (đặt lại lúc 07:00 giờ Bangkok). '
                'Bạn có thể thử đáp án mẫu, /hint, /skip hoặc /stop.'
            )
        else:
            self.write({'next_run': reset, 'error_code': 'daily_quota'})
            if self.session_id.state == 'preparing':
                self.session_id.state = 'failed'

    def _failure(self, config, code):
        if self.state != 'running':
            return
        if not self._valid(config):
            self._release_question()
            self.state = 'skipped'
            return
        fast = self.kind in ('grade', 'explain')
        failed = self.calls >= (2 if fast else 3)
        interactive = self.kind in ('grade', 'explain') or (
            self.kind == 'generate' and self.learner_id.session_active
        )
        delay = timedelta(
            seconds=(
                0 if fast
                else max(self.calls, 1) * (10 if interactive else 120)
            )
        )
        self.write({
            'state': 'failed' if failed else 'pending', 'error_code': code,
            'next_run': fields.Datetime.now() + delay,
        })
        if not failed:
            self._wake_worker(at=self.next_run)
            if interactive and self.calls == 1:
                timing = 'ngay' if fast else 'sau khoảng 10 giây'
                self.learner_id._reply(
                    'AI chưa xử lý được lượt vừa rồi. Mình sẽ tự thử lại '
                    f'{timing}; bạn không cần gửi lại câu trả lời. '
                    'Bạn vẫn có thể dùng /hint, /skip hoặc /stop.'
                )
        if failed:
            self._release_question()
            if self.session_id.state == 'preparing':
                self.session_id.state = 'failed'
            if self.kind != 'prepare':
                self.learner_id._reply(
                    'AI chưa xử lý được. Bạn có thể thử lại, /skip hoặc /stop.'
                )

    def _build_request(self):
        learner = self.learner_id
        if self.kind in ('generate', 'prepare'):
            history = self.env['english.lesson'].search([
                ('generated_for_id', '=', learner.id),
            ], order='id desc', limit=20)
            history |= learner.progress_ids.lesson_id[-10:]
            count = 5 if self.kind == 'prepare' else 1
            task = (
                f'Create {count} connected English exercises on one topic. '
                'Use a gradual progression. Explain in simple Vietnamese. '
                'Examples MUST differ from exercise answers; never reveal '
                'the exercise answer in examples or hints. Each text field '
                'under 350 characters. Include bilingual examples, words, '
                'phrases, grammar formula, common mistake, translation '
                'exercise and answer with explanation. Avoid recent '
                'exercises. Return exactly the requested flat JSON keys.'
            )
            properties = dict.fromkeys(LESSON_FIELDS, 'STRING')
            if self.kind == 'prepare':
                properties = {
                    f'q{n}_{key}': 'STRING'
                    for n in range(1, 6) for key in LESSON_FIELDS
                }
            return json.dumps({
                'task': task, 'level': self.request_level,
                'topic': self.request_topic,
                'recent': history.mapped('exercise'),
            }, ensure_ascii=False), properties
        lesson = self.progress_id.lesson_id
        context = {
            'question': lesson.question, 'exercise': lesson.exercise,
            'answer': lesson.answer, 'grammar': lesson.grammar_vi,
            'sample_answers': lesson.sample_answers,
        }
        if self.kind == 'grade':
            context.pop('sample_answers')
            context.pop('question')
            context.update({
                'task': 'Assess correctness, accept natural equivalent '
                'answers. Explain at most two errors in Vietnamese and '
                'give the corrected English answer. Keep feedback within '
                '2 short sentences (under 240 characters).',
                'learner_answer': self.attempt_id.answer_text,
            })
            properties = {
                'correct': 'BOOLEAN', 'feedback': 'STRING',
                'corrected_answer': 'STRING',
            }
        else:
            context.update({
                'task': 'Explain this question in simple Vietnamese with '
                'bilingual examples, under 1800 characters.',
                'learner_question': self.input_text,
            })
            properties = {'feedback': 'STRING'}
        return json.dumps(context, ensure_ascii=False), properties

    def _process(self, config):
        self.ensure_one()
        lease = self.lease_token
        prompt, properties = self._build_request()
        result, tokens = config.with_context(
            english_job_kind=self.kind,
        )._gemini(prompt, properties)
        # End the read snapshot before checking a stop/skip received in HTTP.
        self.env['ir.cron']._commit_progress(remaining=1)
        self.env.invalidate_all()
        self.learner_id._lock()
        if self.lease_token != lease:
            return
        self.tokens = tokens
        if self.state != 'running' or not self._valid(config):
            if self.state == 'running':
                self._release_question()
                self.state = 'skipped'
            return
        with self.env.cr.savepoint():
            self._apply_result(config, result)
            self.write({
                'state': 'done', 'tokens': tokens, 'error_code': False,
            })

    def _apply_result(self, config, result):
        learner = self.learner_id
        if self.kind in ('generate', 'prepare'):
            count = 5 if self.kind == 'prepare' else 1
            lessons = self.env['english.lesson']
            seen = set()
            if self.kind == 'prepare':
                previous = lessons.search([
                    ('generated_for_id', '=', learner.id),
                ], order='id desc', limit=60)
                seen = {lessons._text_key(item.exercise) for item in previous}
            auto = (
                config.daily_ai_auto_approve if self.kind == 'prepare'
                else not config.require_approval
            )
            for n in range(1, count + 1):
                values = {
                    key: result[f'q{n}_{key}' if count > 1 else key]
                    for key in LESSON_FIELDS
                }
                values.update(self._lesson_metadata(n, result))
                self.env['english.lesson']._validate_generated(values)
                exercise = self.env['english.lesson']._text_key(
                    values['exercise']
                )
                if exercise in seen:
                    raise ValidationError('AI repeated an exercise.')
                seen.add(exercise)
                lessons |= self.env['english.lesson'].create({
                    **values, 'level': self.request_level,
                    'topic': self.request_topic, 'sequence': 100 + n,
                    'generated': True, 'generated_for_id': learner.id,
                    'state': 'ready' if auto else 'draft',
                })
            if self.kind == 'prepare':
                self.session_id.write({
                    'lesson_ids': [(6, 0, lessons.ids)],
                    'generation_done': True,
                })
                if self.session_id.state in ('preparing', 'failed'):
                    self.session_id.state = 'ready'
                # Preparation never sends messages before the scheduled slot.
            elif config.require_approval:
                learner._reply('Bài mới đang chờ duyệt trong Odoo.')
            elif learner.current_progress_id.state not in (
                'awaiting', 'grading',
            ):
                learner._start_lesson(automatic=True)
        elif self.kind == 'grade':
            self.attempt_id._finish(
                result['correct'], result['feedback'],
                result['corrected_answer'],
            )
        else:
            # Explanations can disclose the answer: do not score recall.
            self.progress_id.answer_shown = True
            learner._reply(result['feedback'])

    def _lesson_metadata(self, number, result):
        return {}

    def action_retry(self):
        self.check_access('write')
        for job in self.filtered(lambda item: item.state == 'failed'):
            job.learner_id._lock()
            config = self.env['english.configuration']._get_config()
            if not job._valid(config):
                raise UserError('Tác vụ đã cũ hoặc buổi học đã dừng.')
            if job.kind == 'grade':
                if job.progress_id.state == 'grading':
                    raise UserError('Another attempt is already being graded.')
                job.progress_id.state = 'grading'
            job.write({
                'state': 'pending', 'calls': 0,
                'next_run': fields.Datetime.now(),
            })
        self._wake_due_workers()


class EnglishApiUsage(models.Model):
    _name = 'english.api.usage'
    _description = 'English AI API Usage'

    job_id = fields.Many2one('english.job', ondelete='set null')
    tokens = fields.Integer(default=0)
