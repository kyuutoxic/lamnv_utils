from datetime import timedelta
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTelegramFeatures(TransactionCase):
    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()
        self.icp = self.env['ir.config_parameter'].sudo()
        self.icp.set_param(
            'room_rental_expense.telegram_allowed_chat_ids', '123'
        )
        self.icp.set_param(
            'room_rental_expense.telegram_bot_token', 'test-only'
        )
        self.room = self.env['rental.room'].create(
            {
                'name': 'Feature room',
                'telegram_code': 'FEATURE',
                'default_rent': 1000000,
            }
        )
        self.readings = self.env['meter.reading']

    def message(self, text, user=123, chat=123):
        return {'chat': {'id': chat}, 'from': {'id': user}, 'text': text}

    def send(self, text, user=123, chat=123):
        return self.readings.process_telegram_message(
            self.message(text, user, chat)
        )

    def invoice(self, **values):
        inv = self.env['room.invoice'].create(
            {'room_id': self.room.id, 'invoice_date': self.today, **values}
        )
        inv.action_confirm()
        return inv

    def start_reading(self):
        self.send('/menu')
        self.send('Ghi chỉ số')
        self.send(f'#{self.room.id} - {self.room.name}')

    def test_guided_reading_only_saves_after_confirmation(self):
        self.start_reading()
        self.send('100')
        self.send('10')
        result = self.send('Hôm nay')
        self.assertIn('Xác nhận', str(result['reply_markup']))
        self.assertFalse(
            self.readings.search([('room_id', '=', self.room.id)])
        )
        result = self.send('Xác nhận')
        self.assertEqual(result['status'], 'success')
        reading = self.readings.browse(result['reading_id'])
        self.assertEqual(reading.electric_current, 100)
        self.assertEqual(reading.water_current, 10)
        self.assertEqual(reading.reading_date, self.today)

    def test_cancel_invalid_and_expiry(self):
        self.start_reading()
        for text in ('nan', '-1', 'abc'):
            self.assertEqual(self.send(text)['status'], 'error')
        session = self.env['room.telegram.session'].search(
            [('chat_id', '=', '123')]
        )
        self.assertEqual(session.step, 'electric')
        session.expires_at = fields.Datetime.now() - timedelta(seconds=1)
        self.assertIn('hết hạn', self.send('100')['message'])
        self.start_reading()
        self.send('Hủy')
        self.assertFalse(
            self.readings.search([('room_id', '=', self.room.id)])
        )

    def test_create_invoice_after_guided_reading(self):
        self.start_reading()
        self.send('100')
        self.send('10')
        self.send('Hôm nay')
        result = self.send('Xác nhận')
        self.assertIn('Tạo hóa đơn', str(result['reply_markup']))
        reading = self.readings.browse(result['reading_id'])
        self.send('Tạo hóa đơn')
        self.send('09/2026')
        self.assertFalse(reading.invoice_id)
        result = self.send('Xác nhận')
        self.assertEqual(result['invoice_id'], reading.invoice_id.id)
        self.assertEqual(reading.invoice_id.status, 'pending')
        self.assertEqual(reading.invoice_id.invoice_month, '09/2026')
        self.assertEqual(reading.reading_date, self.today)
        self.send('Xác nhận')
        self.assertEqual(
            self.env['room.invoice'].search_count(
                [('meter_reading_id', '=', reading.id)]
            ),
            1,
        )

    def test_cancel_guided_invoice_creation(self):
        self.start_reading()
        self.send('100')
        self.send('10')
        self.send('Hôm nay')
        result = self.send('Xác nhận')
        reading = self.readings.browse(result['reading_id'])
        self.send('Tạo hóa đơn')
        self.send('Hủy')
        self.send('Xác nhận')
        self.assertFalse(reading.invoice_id)

    def test_change_period_preserves_amounts_and_dates(self):
        inv = self.invoice()
        old = inv.invoice_month
        dates = (inv.invoice_date, inv.due_date)
        total = inv.total_amount
        self.send('Đổi kỳ hóa đơn')
        self.send(inv.invoice_number)
        self.assertEqual(self.send('bad')['status'], 'error')
        self.send('08/2026')
        self.send('Ghi nhầm kỳ')
        self.assertEqual(inv.invoice_month, old)
        result = self.send('Xác nhận')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(inv.invoice_month, '08/2026')
        self.assertEqual(inv.total_amount, total)
        self.assertEqual((inv.invoice_date, inv.due_date), dates)
        self.assertEqual(inv.status, 'pending')
        self.assertTrue(
            any(
                'Đổi kỳ hóa đơn' in (msg.body or '') for msg in inv.message_ids
            )
        )

    def test_change_period_invoice_choices_are_visible(self):
        result = self.send('Đổi kỳ hóa đơn')
        self.assertIn('Không có hóa đơn', result['message'])
        inv = self.invoice()
        result = self.send('Đổi kỳ hóa đơn')
        label = result['reply_markup']['keyboard'][0][0]
        self.assertIn(inv.invoice_number, label)
        self.assertIn(self.room.name, label)
        self.assertIn(inv.invoice_month, label)
        self.assertIn(label, result['message'])
        result = self.send(label)
        self.assertIn('Nhập kỳ MM/YYYY', result['message'])

    def test_change_period_preserves_payment_after_preview(self):
        inv = self.invoice()
        old = inv.invoice_month
        self.send('Đổi kỳ hóa đơn')
        self.send(inv.invoice_number)
        self.send('08/2026')
        self.send('Ghi nhầm kỳ')
        inv.paid_amount = 100
        status = inv.status
        self.assertEqual(self.send('Xác nhận')['status'], 'success')
        self.assertNotEqual(inv.invoice_month, old)
        self.assertEqual(inv.paid_amount, 100)
        self.assertEqual(inv.status, status)

    def test_change_period_duplicate_canceled_and_draft(self):
        inv = self.env['room.invoice'].create({'room_id': self.room.id})
        other = self.invoice(invoice_month='08/2026')
        self.send('Đổi kỳ hóa đơn')
        self.send(inv.invoice_number)
        self.assertEqual(self.send('08/2026')['status'], 'error')
        other.action_cancel()
        self.send('08/2026')
        self.send('Hủy')
        self.assertNotEqual(inv.invoice_month, '08/2026')
        self.send('Đổi kỳ hóa đơn')
        self.send(inv.invoice_number)
        self.send('08/2026')
        self.send('Ghi nhầm kỳ')
        self.assertEqual(self.send('Xác nhận')['status'], 'success')
        self.assertEqual(inv.status, 'draft')

    def test_change_period_stale_preview(self):
        inv = self.invoice()
        self.send('Đổi kỳ hóa đơn')
        self.send(inv.invoice_number)
        self.send('08/2026')
        self.send('Ghi nhầm kỳ')
        inv._change_billing_period('07/2026', inv.invoice_month, 'Sửa kỳ')
        self.assertEqual(self.send('Xác nhận')['status'], 'error')
        self.assertEqual(inv.invoice_month, '07/2026')

    def test_new_invoice_rechecks_duplicate_at_confirmation(self):
        self.start_reading()
        self.send('100')
        self.send('10')
        self.send('Hôm nay')
        result = self.send('Xác nhận')
        reading = self.readings.browse(result['reading_id'])
        self.send('Tạo hóa đơn')
        self.send('08/2026')
        self.invoice(invoice_month='08/2026')
        self.assertEqual(self.send('Xác nhận')['status'], 'error')
        self.assertFalse(reading.invoice_id)

    def test_paid_invoice_period_can_change_with_reason(self):
        inv = self.invoice()
        inv.action_paid()
        paid = inv.paid_amount
        dates = (inv.invoice_date, inv.due_date)
        result = self.send('Đổi kỳ hóa đơn')
        self.assertIn(inv.invoice_number, result['message'])
        self.send(inv.invoice_number)
        self.send('08/2026')
        self.assertEqual(self.send('')['status'], 'error')
        self.assertEqual(self.send('x' * 501)['status'], 'error')
        preview = self.send('Ghi nhầm tháng khi chốt tiền')
        self.assertIn('Tổng kết tháng sẽ thay đổi', preview['message'])
        self.assertEqual(self.send('Xác nhận')['status'], 'success')
        self.assertEqual(inv.invoice_month, '08/2026')
        self.assertEqual(inv.paid_amount, paid)
        self.assertEqual(inv.status, 'paid')
        self.assertEqual(inv.remaining_amount, 0)
        self.assertEqual((inv.invoice_date, inv.due_date), dates)
        self.assertTrue(
            any(
                'Ghi nhầm tháng khi chốt tiền' in (msg.body or '')
                for msg in inv.message_ids
            )
        )

    def test_canceled_invoice_period_cannot_change(self):
        inv = self.invoice()
        self.send('Đổi kỳ hóa đơn')
        self.send(inv.invoice_number)
        self.send('08/2026')
        self.send('Ghi nhầm kỳ')
        inv.action_cancel()
        self.assertEqual(self.send('Xác nhận')['status'], 'error')
        self.send('Đổi kỳ hóa đơn')
        self.assertEqual(self.send(inv.invoice_number)['status'], 'error')

    def test_summary_moves_with_billing_period(self):
        inv = self.invoice(invoice_month='09/2026')
        summary = self.env['room.monthly.summary']
        self.assertEqual(summary._totals('09/2026')['invoice_count'], 1)
        inv._change_billing_period('08/2026', '09/2026', 'Sửa kỳ')
        self.assertEqual(summary._totals('09/2026')['invoice_count'], 0)
        self.assertEqual(summary._totals('08/2026')['invoice_count'], 1)

    def test_late_reading_date_correction_allows_new_reading(self):
        old = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_previous': 50,
                'electric_current': 100,
                'water_previous': 5,
                'water_current': 10,
            }
        )
        inv = self.invoice(meter_reading_id=old.id, invoice_month='05/2026')
        inv.action_paid()
        total = inv.total_amount
        self.send('Sửa ngày chỉ số')
        self.send(inv.invoice_number)
        self.send('2026-05-31')
        self.send('Chỉ số tháng 5 nhập muộn')
        self.assertEqual(old.reading_date, self.today)
        self.assertEqual(self.send('Xác nhận')['status'], 'success')
        self.assertEqual(str(old.reading_date), '2026-05-31')
        self.assertEqual(old.electric_usage, 50)
        self.assertEqual(inv.total_amount, total)
        self.assertEqual(inv.paid_amount, total)
        self.assertEqual(inv.status, 'paid')
        self.assertTrue(
            any(
                'Chỉ số tháng 5 nhập muộn' in (msg.body or '')
                for msg in inv.message_ids
            )
        )
        self.start_reading()
        self.send('110')
        self.send('12')
        self.send('Hôm nay')
        result = self.send('Xác nhận')
        self.assertEqual(result['status'], 'success')
        new = self.readings.browse(result['reading_id'])
        self.assertNotEqual(old, new)
        self.assertEqual(new.electric_previous, 100)
        self.assertEqual(new.electric_usage, 10)

    def test_date_correction_duplicate_future_and_cancel(self):
        reading = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_current': 100,
                'water_current': 10,
            }
        )
        inv = self.invoice(meter_reading_id=reading.id)
        self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': '2026-05-31',
                'electric_current': 90,
                'water_current': 9,
            }
        )
        self.send('Sửa ngày chỉ số')
        self.send(inv.invoice_number)
        self.assertEqual(self.send('bad')['status'], 'error')
        self.assertEqual(self.send('2099-01-01')['status'], 'error')
        self.send('2026-05-31')
        self.send('Nhập muộn')
        self.assertEqual(self.send('Xác nhận')['status'], 'error')
        self.send('Hủy')
        self.assertEqual(reading.reading_date, self.today)

    def test_date_correction_warns_inconsistent_neighbors(self):
        self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': '2026-06-30',
                'electric_previous': 100,
                'electric_current': 200,
                'water_previous': 10,
                'water_current': 20,
            }
        )
        reading = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_previous': 200,
                'electric_current': 300,
                'water_previous': 20,
                'water_current': 30,
            }
        )
        inv = self.invoice(meter_reading_id=reading.id)
        total = inv.total_amount
        self.send('Sửa ngày chỉ số')
        self.send(inv.invoice_number)
        self.send('2026-05-31')
        preview = self.send('Sửa ngày')
        self.assertIn('Cảnh báo điện', preview['message'])
        self.assertIn('Vẫn cho sửa ngày', preview['message'])
        result = self.send('Xác nhận')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(str(reading.reading_date), '2026-05-31')
        self.assertEqual(inv.total_amount, total)

    def test_date_correction_is_independent_of_invoice_dates(self):
        other = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': '2026-10-06',
                'electric_current': 100,
                'water_current': 10,
            }
        )
        self.invoice(meter_reading_id=other.id, invoice_month='05/2026')
        reading = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_previous': 100,
                'electric_current': 150,
                'water_previous': 10,
                'water_current': 15,
            }
        )
        inv = self.invoice(
            meter_reading_id=reading.id, invoice_month='07/2026'
        )
        invoice_date = inv.invoice_date
        self.send('Sửa ngày chỉ số')
        self.send(inv.invoice_number)
        self.send('2026-07-30')
        preview = self.send('Sửa lần lượt dữ liệu nhập muộn')
        self.assertIn('2026-10-06', preview['message'])
        self.assertEqual(self.send('Xác nhận')['status'], 'success')
        self.assertEqual(str(reading.reading_date), '2026-07-30')
        self.assertEqual(inv.invoice_date, invoice_date)
        self.assertEqual(other.reading_date.isoformat(), '2026-10-06')

    def test_date_menu_filters_before_limit(self):
        reading = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_current': 100,
                'water_current': 10,
            }
        )
        inv = self.invoice(meter_reading_id=reading.id)
        for index in range(20):
            self.env['room.invoice'].create(
                {
                    'room_id': self.room.id,
                    'invoice_month': '12/2099',
                    'invoice_date': '2099-12-01',
                }
            )
        result = self.send('Sửa ngày chỉ số')
        self.assertIn(inv.invoice_number, result['message'])
        self.assertIn(inv.invoice_number, str(result['reply_markup']))

    def test_date_correction_warns_previous_counter_mismatch(self):
        self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': '2026-05-01',
                'electric_current': 100,
                'water_current': 10,
            }
        )
        reading = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_previous': 100,
                'electric_current': 150,
                'water_previous': 9,
                'water_current': 15,
            }
        )
        inv = self.invoice(meter_reading_id=reading.id)
        self.send('Sửa ngày chỉ số')
        self.send(inv.invoice_number)
        self.send('2026-05-31')
        preview = self.send('Sửa ngày')
        self.assertIn('Lưu ý nước', preview['message'])
        result = self.send('Xác nhận')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(str(reading.reading_date), '2026-05-31')
        self.assertEqual(reading.water_previous, 9)
        self.assertEqual(reading.water_usage, 6)

    def test_latest_date_correction_keeps_settled_consumption(self):
        self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': '2026-06-07',
                'electric_current': 100,
                'water_current': 10,
            }
        )
        reading = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_previous': 90,
                'electric_current': 150,
                'water_previous': 9,
                'water_current': 15,
            }
        )
        inv = self.invoice(meter_reading_id=reading.id)
        inv.action_paid()
        total = inv.total_amount
        self.send('Sửa ngày chỉ số')
        self.send(inv.invoice_number)
        self.send('2026-07-30')
        preview = self.send('Nhập nhầm ngày')
        self.assertIn('Lưu ý điện', preview['message'])
        self.assertEqual(self.send('Xác nhận')['status'], 'success')
        self.assertEqual(str(reading.reading_date), '2026-07-30')
        self.assertEqual(reading.electric_usage, 60)
        self.assertEqual(inv.total_amount, total)
        self.assertEqual(inv.paid_amount, total)
        self.assertEqual(inv.status, 'paid')

    def test_reminders_are_separate_for_each_bot(self):
        self.icp.set_param(
            'room_rental_expense.telegram_reminders_enabled', 'True'
        )
        self.invoice(due_date=self.today)
        reminders = self.env['room.telegram.reminder']
        with patch.object(
            type(reminders), '_send_reminder', return_value=True
        ) as send:
            reminders._run_reminders()
            self.assertEqual(send.call_count, 1)
            self.icp.set_param(
                'room_rental_expense.telegram_bot_token', 'new-test-bot'
            )
            reminders._run_reminders()
            reminders._run_reminders()
            self.assertEqual(send.call_count, 2)
        self.assertEqual(len(set(reminders.search([]).mapped('bot_key'))), 2)

    def test_short_interval_does_not_show_percentage(self):
        for index in range(4):
            self.readings.create(
                {
                    'room_id': self.room.id,
                    'reading_date': self.today
                    - timedelta(days=91 - index * 30),
                    'electric_previous': index * 30,
                    'electric_current': (index + 1) * 30,
                    'water_previous': index * 3,
                    'water_current': (index + 1) * 3,
                }
            )
        current = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_previous': 120,
                'electric_current': 300,
                'water_previous': 12,
                'water_current': 100,
            }
        )
        self.assertIn('chưa đủ 7 ngày', current.anomaly_warning)
        self.assertNotIn('%', current.anomaly_warning)

    def test_old_pending_reminder_is_not_sent_by_new_bot(self):
        self.icp.set_param(
            'room_rental_expense.telegram_reminders_enabled', 'True'
        )
        self.invoice(due_date=self.today)
        reminders = self.env['room.telegram.reminder']
        with patch.object(
            type(reminders), '_send_reminder', return_value=False
        ):
            reminders._run_reminders()
        old = reminders.search([])
        self.icp.set_param(
            'room_rental_expense.telegram_bot_token', 'another-test-bot'
        )
        with patch.object(
            type(reminders), '_send_reminder', return_value=True
        ) as send:
            reminders._run_reminders()
            self.assertEqual(send.call_count, 1)
        self.assertEqual(old.state, 'pending')
        self.assertEqual(reminders.search_count([('state', '=', 'sent')]), 1)

    def test_anomaly_ignores_broken_counter_chain(self):
        for index in range(4):
            self.readings.create(
                {
                    'room_id': self.room.id,
                    'reading_date': self.today
                    - timedelta(days=120 - index * 30),
                    'electric_previous': index * 30,
                    'electric_current': (index + 1) * 30,
                    'water_previous': index * 3,
                    'water_current': (index + 1) * 3,
                }
            )
        current = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_previous': 0,
                'electric_current': 300,
                'water_previous': 0,
                'water_current': 100,
            }
        )
        self.assertFalse(current.anomaly_warning)

    def test_session_user_isolation_and_unauthorized(self):
        self.start_reading()
        self.send('/menu', user=456)
        sessions = self.env['room.telegram.session'].search(
            [('chat_id', '=', '123')]
        )
        self.assertEqual(len(sessions), 2)
        self.assertEqual(
            sessions.filtered(lambda item: item.user_id == '123').step,
            'electric',
        )
        self.assertEqual(self.send('/menu', chat=999)['status'], 'error')

    def test_payment_confirm_and_duplicate_update(self):
        inv = self.invoice()
        self.send('Thanh toán')
        self.send(inv.invoice_number)
        self.send('100000')
        self.assertEqual(inv.paid_amount, 0)
        updates = self.env['room.telegram.update'].sudo()
        payload = {'update_id': 900, 'message': self.message('Xác nhận')}
        self.assertEqual(updates._process_update(payload)['status'], 'success')
        self.assertTrue(updates._process_update(payload)['duplicate'])
        self.assertEqual(inv.paid_amount, 100000)

    def test_payment_over_amount_and_cancellation(self):
        inv = self.invoice()
        self.send('Thanh toán')
        self.send(inv.invoice_number)
        self.send(str(int(inv.total_amount + 1)))
        self.assertEqual(self.send('Xác nhận')['status'], 'error')
        self.assertEqual(inv.paid_amount, 0)
        self.send('Hủy')
        self.assertEqual(inv.paid_amount, 0)

    def test_anomaly_normalizes_days_and_skips_manual(self):
        for index in range(4):
            self.readings.create(
                {
                    'room_id': self.room.id,
                    'reading_date': self.today
                    - timedelta(days=90 - index * 30),
                    'electric_previous': index * 30,
                    'electric_current': (index + 1) * 30,
                    'water_previous': index * 3,
                    'water_current': (index + 1) * 3,
                }
            )
        current = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today + timedelta(days=30),
                'electric_previous': 120,
                'electric_current': 180,
                'water_previous': 12,
                'water_current': 15,
            }
        )
        self.assertIn('Điện tăng', current.anomaly_warning)
        current.electric_usage_manual_override = True
        self.assertFalse(current.anomaly_warning)

    def test_anomaly_insufficient_history_and_long_interval(self):
        readings = []
        for index in range(3):
            readings.append(
                self.readings.create(
                    {
                        'room_id': self.room.id,
                        'reading_date': self.today
                        - timedelta(days=60 - index * 30),
                        'electric_previous': index * 30,
                        'electric_current': (index + 1) * 30,
                        'water_previous': index * 3,
                        'water_current': (index + 1) * 3,
                    }
                )
            )
        self.assertFalse(readings[0].anomaly_warning)
        current = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today + timedelta(days=60),
                'electric_previous': 90,
                'electric_current': 150,
                'water_previous': 9,
                'water_current': 15,
            }
        )
        self.assertFalse(current.anomaly_warning)

    def test_monthly_summary_excludes_draft_cancel_and_covers_expense(self):
        inv = self.invoice()
        inv.paid_amount = 100000
        canceled = self.invoice()
        canceled.action_cancel()
        self.env['room.invoice'].create({'room_id': self.room.id})
        self.env['room.expense'].create(
            {
                'room_id': self.room.id,
                'expense_date': self.today,
                'category': 'repair',
                'description': 'Test',
                'amount': 50000,
            }
        )
        model = self.env['room.monthly.summary']
        month = self.today.strftime('%m/%Y')
        totals = model._totals(month, self.room)
        self.assertEqual(totals['invoice_count'], 1)
        self.assertEqual(totals['cost'], inv.total_amount + 50000)
        self.assertEqual(totals['paid_amount'], 100000)
        self.assertEqual(
            self.send(f'/summary {month} FEATURE')['status'], 'success'
        )
        self.send('Tổng kết tháng')
        self.send('FEATURE')
        self.assertIn('Tổng chi phí', self.send(month)['message'])
        self.assertEqual(self.send('/summary 13/2026')['status'], 'error')

    def test_reminders_once_and_paid_stops(self):
        self.icp.set_param(
            'room_rental_expense.telegram_reminders_enabled', 'True'
        )
        inv = self.invoice(due_date=self.today + timedelta(days=1))
        reminders = self.env['room.telegram.reminder'].sudo()
        with patch.object(
            type(reminders), '_send_reminder', return_value=True
        ) as send:
            self.env['room.invoice'].cron_update_overdue_status()
            self.env['room.invoice'].cron_update_overdue_status()
            self.assertEqual(send.call_count, 1)
            inv.action_paid()
            self.env['room.invoice'].cron_update_overdue_status()
            self.assertEqual(send.call_count, 1)

    def test_reminder_failure_retry_and_chat_revoked(self):
        self.icp.set_param(
            'room_rental_expense.telegram_reminders_enabled', 'True'
        )
        self.invoice(due_date=self.today)
        reminders = self.env['room.telegram.reminder'].sudo()
        with patch.object(
            type(reminders), '_send_reminder', return_value=False
        ):
            reminders._run_reminders()
        self.assertEqual(reminders.search([]).state, 'pending')
        with patch.object(
            type(reminders), '_send_reminder', return_value=True
        ) as send:
            reminders._run_reminders()
            reminders._run_reminders()
            self.assertEqual(send.call_count, 1)
        self.invoice(due_date=self.today)
        with patch.object(
            type(reminders), '_send_reminder', return_value=False
        ):
            reminders._run_reminders()
        self.icp.set_param(
            'room_rental_expense.telegram_allowed_chat_ids', '456'
        )
        with patch.object(
            type(reminders), '_send_reminder', return_value=True
        ):
            reminders._run_reminders()
        self.assertTrue(reminders.search([('state', '=', 'skipped')]))

    def test_reminders_disabled_and_overdue(self):
        self.invoice(
            invoice_date=self.today - timedelta(days=2),
            due_date=self.today - timedelta(days=1),
        )
        reminders = self.env['room.telegram.reminder'].sudo()
        self.icp.set_param(
            'room_rental_expense.telegram_reminders_enabled', 'False'
        )
        with patch.object(
            type(reminders), '_send_reminder', return_value=True
        ) as send:
            reminders._run_reminders()
            send.assert_not_called()
            self.icp.set_param(
                'room_rental_expense.telegram_reminders_enabled', 'True'
            )
            reminders._run_reminders()
            self.assertEqual(send.call_count, 1)
        self.assertEqual(reminders.search([]).kind, 'overdue')

    def test_monthly_comparison_and_room_filter(self):
        previous = self.invoice(
            invoice_date=self.today - relativedelta(months=1)
        )
        current = self.invoice()
        other = self.env['rental.room'].create(
            {'name': 'Other', 'default_rent': 500000}
        )
        inv = self.env['room.invoice'].create({'room_id': other.id})
        inv.action_confirm()
        model = self.env['room.monthly.summary']
        month = self.today.strftime('%m/%Y')
        previous_month = (self.today - relativedelta(months=1)).strftime(
            '%m/%Y'
        )
        self.assertEqual(
            model._totals(month, self.room)['cost'], current.total_amount
        )
        self.assertEqual(
            model._totals(previous_month, self.room)['cost'],
            previous.total_amount,
        )
        self.assertEqual(
            model._totals(month)['cost'],
            current.total_amount + inv.total_amount,
        )

    def test_pre_due_then_overdue_stage_only_once(self):
        self.icp.set_param(
            'room_rental_expense.telegram_reminders_enabled', 'True'
        )
        inv = self.invoice(due_date=self.today)
        reminders = self.env['room.telegram.reminder'].sudo()
        with patch.object(
            type(reminders), '_send_reminder', return_value=True
        ) as send:
            reminders._run_reminders()
            with patch(
                'odoo.fields.Date.context_today',
                return_value=self.today + timedelta(days=1),
            ):
                reminders._run_reminders()
                reminders._run_reminders()
            self.assertEqual(send.call_count, 2)
        self.assertEqual(
            reminders.search_count([('invoice_id', '=', inv.id)]), 2
        )

    def test_cancel_invoice_suppresses_pending_reminder(self):
        self.icp.set_param(
            'room_rental_expense.telegram_reminders_enabled', 'True'
        )
        inv = self.invoice(due_date=self.today)
        reminders = self.env['room.telegram.reminder'].sudo()
        with patch.object(
            type(reminders), '_send_reminder', return_value=False
        ):
            reminders._run_reminders()
        inv.action_cancel()
        with patch.object(
            type(reminders), '_send_reminder', return_value=True
        ) as send:
            reminders._run_reminders()
            send.assert_not_called()
        self.assertEqual(reminders.search([]).state, 'skipped')

    def test_slash_command_interrupts_session(self):
        self.start_reading()
        self.assertEqual(self.send('/help')['status'], 'success')
        self.assertFalse(
            self.env['room.telegram.session'].search([('chat_id', '=', '123')])
        )

    def test_guided_reading_linked_invoice_cannot_be_changed(self):
        reading = self.readings.create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_current': 100,
                'water_current': 10,
            }
        )
        self.invoice(meter_reading_id=reading.id)
        self.start_reading()
        self.send('110')
        self.send('11')
        self.send('Hôm nay')
        self.assertEqual(self.send('Xác nhận')['status'], 'error')
        self.assertEqual(reading.electric_current, 100)
