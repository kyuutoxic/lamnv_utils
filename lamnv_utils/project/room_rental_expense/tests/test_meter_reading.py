from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMeterReading(TransactionCase):
    def setUp(self):
        super().setUp()
        self.room = self.env['rental.room'].create({'name': 'Counter tests'})
        self.today = fields.Date.today()

    def reading(self, **values):
        return self.env['meter.reading'].create(
            {
                'room_id': self.room.id,
                'reading_date': self.today,
                'electric_previous': 300,
                'electric_current': 350,
                'water_previous': 10,
                'water_current': 15,
                **values,
            }
        )

    def test_normal_and_replacement_usage(self):
        normal = self.reading()
        self.assertEqual(normal.electric_usage, 50)
        self.assertEqual(normal.water_usage, 5)
        replaced = self.reading(
            electric_meter_replaced=True,
            electric_current=15,
            electric_replacement_last=320,
            water_meter_replaced=True,
            water_current=2,
            water_replacement_last=12,
        )
        self.assertEqual(replaced.electric_usage, 35)
        self.assertEqual(replaced.water_usage, 4)

    def test_manual_override(self):
        reading = self.reading(
            electric_usage_manual_override=True, electric_usage_manual_value=42
        )
        self.assertEqual(reading.electric_usage, 42)
        reading.water_usage = 7
        self.assertTrue(reading.water_usage_manual_override)
        self.assertEqual(reading.water_usage_manual_value, 7)

    def test_regression_rejected(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.reading(electric_current=299)

    def test_previous_reading_is_before_date(self):
        previous = self.reading(reading_date=self.today - timedelta(days=1))
        self.reading(reading_date=self.today + timedelta(days=1))
        chosen = self.env['meter.reading']._get_previous_reading(
            self.room, self.today
        )
        self.assertEqual(chosen, previous)
