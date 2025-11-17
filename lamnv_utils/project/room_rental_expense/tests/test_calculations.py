# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests import common


class TestRoomInvoiceCalculations(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.room = self.env['rental.room'].create({
            'name': 'Test Room',
            'start_date': date.today(),
            'default_rent': 3000000,
        })
        self.config = self.env['room.config'].create({
            'room_id': self.room.id,
            'effective_date': date.today(),
            'electric_price': 3500,
            'water_price': 15000,
            'wifi_price': 120000,
            'trash_fee': 30000,
            'parking_fee': 100000,
            'other_utilities_price': 50000,
        })
        self.reading = self.env['meter.reading'].create({
            'room_id': self.room.id,
            'reading_date': date.today(),
            'electric_previous': 100,
            'electric_current': 120,
            'water_previous': 40,
            'water_current': 55,
            'electric_meter_replaced': False,
            'water_meter_replaced': False,
        })

    def test_invoice_amounts_and_status(self):
        invoice = self.env['room.invoice'].create({
            'room_id': self.room.id,
            'invoice_month': date.today().strftime('%m/%Y'),
            'meter_reading_id': self.reading.id,
        })
        self.assertEqual(invoice.rent_amount, self.room.default_rent)
        self.assertEqual(invoice.electric_usage, 20)
        self.assertEqual(invoice.water_usage, 15)
        self.assertEqual(invoice.electric_amount, 20 * self.config.electric_price)
        self.assertEqual(invoice.water_amount, 15 * self.config.water_price)
        self.assertAlmostEqual(
            invoice.utilities_amount,
            self.config.wifi_price + self.config.trash_fee +
            self.config.parking_fee + self.config.other_utilities_price
        )
        expected_subtotal = (
            invoice.rent_amount + invoice.electric_amount +
            invoice.water_amount + invoice.utilities_amount +
            invoice.other_charges
        )
        self.assertEqual(invoice.subtotal, expected_subtotal)
        self.assertEqual(invoice.total_amount, expected_subtotal)
        self.assertEqual(invoice.status, 'pending')
        self.assertIn('Nước', invoice.manual_breakdown or '')
        self.assertIn('Tổng', invoice.manual_breakdown or '')

        payment_partial = self.env['room.payment'].create({
            'invoice_id': invoice.id,
            'payment_date': date.today(),
            'payment_amount': 1000000,
            'payment_method': 'bank_transfer',
        })
        self.assertTrue(payment_partial)
        self.assertEqual(invoice.status, 'partially_paid')

        self.env['room.payment'].create({
            'invoice_id': invoice.id,
            'payment_date': date.today(),
            'payment_amount': invoice.remaining_amount,
            'payment_method': 'bank_transfer',
        })
        self.assertEqual(invoice.status, 'paid')

    def test_meter_replacement_usage(self):
        replacement_reading = self.env['meter.reading'].create({
            'room_id': self.room.id,
            'reading_date': date.today(),
            'electric_previous': 100,
            'electric_replacement_last': 120,
            'electric_current': 15,
            'electric_meter_replaced': True,
            'water_previous': 50,
            'water_replacement_last': 60,
            'water_current': 5,
            'water_meter_replaced': True,
        })
        self.assertEqual(replacement_reading.electric_usage, 35)
        self.assertEqual(replacement_reading.water_usage, 15)
