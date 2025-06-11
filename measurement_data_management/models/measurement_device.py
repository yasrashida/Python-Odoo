# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MeasurementDevice(models.Model):
    _name = 'measurement.device'
    _description = 'Measurement Device'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Device Name',
        required=True,
        tracking=True,
        help="Name of the measurement device"
    )
    
    serial_number = fields.Char(
        string='Serial Number',
        required=True,
        tracking=True,
        help="Unique serial number of the device"
    )
    
    device_type = fields.Selection([
        ('temperature', 'Temperature Sensor'),
        ('pressure', 'Pressure Sensor'),
        ('distance', 'Distance Sensor'),
        ('displacement', 'Displacement Sensor'),
        ('thickness', 'Thickness Gauge'),
        ('vibration', 'Vibration Sensor'),
        ('flow', 'Flow Meter'),
        ('level', 'Level Sensor'),
        ('force', 'Force Sensor'),
        ('other', 'Other'),
    ], string='Device Type', required=True, tracking=True)
    
    manufacturer = fields.Char(
        string='Manufacturer',
        tracking=True,
        help="Device manufacturer"
    )
    
    model = fields.Char(
        string='Model',
        tracking=True,
        help="Device model number"
    )
    
    location = fields.Char(
        string='Location',
        tracking=True,
        help="Physical location of the device"
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help="Uncheck to archive the device"
    )
    
    calibration_date = fields.Date(
        string='Last Calibration Date',
        tracking=True,
        help="Date of last calibration"
    )
    
    next_calibration_date = fields.Date(
        string='Next Calibration Date',
        tracking=True,
        help="Date of next required calibration"
    )
    
    calibration_interval = fields.Integer(
        string='Calibration Interval (days)',
        default=365,
        help="Calibration interval in days"
    )
    
    measurement_unit = fields.Char(
        string='Default Measurement Unit',
        help="Default unit for measurements from this device"
    )
    
    min_range = fields.Float(
        string='Minimum Range',
        help="Minimum measurement range of the device"
    )
    
    max_range = fields.Float(
        string='Maximum Range',
        help="Maximum measurement range of the device"
    )
    
    accuracy = fields.Float(
        string='Accuracy',
        help="Device accuracy specification"
    )
    
    accuracy_unit = fields.Char(
        string='Accuracy Unit',
        help="Unit for accuracy specification"
    )
    
    notes = fields.Text(
        string='Notes',
        help="Additional notes about the device"
    )
    
    measurement_record_ids = fields.One2many(
        'measurement.record',
        'device_id',
        string='Measurement Records'
    )
    
    record_count = fields.Integer(
        string='Total Records',
        compute='_compute_record_count',
        store=True
    )
    
    last_measurement_date = fields.Datetime(
        string='Last Measurement',
        compute='_compute_last_measurement_date',
        store=True
    )
    
    @api.depends('measurement_record_ids')
    def _compute_record_count(self):
        for device in self:
            device.record_count = len(device.measurement_record_ids)
    
    @api.depends('measurement_record_ids.measurement_date')
    def _compute_last_measurement_date(self):
        for device in self:
            if device.measurement_record_ids:
                device.last_measurement_date = max(
                    device.measurement_record_ids.mapped('measurement_date')
                )
            else:
                device.last_measurement_date = False
    
    @api.constrains('serial_number')
    def _check_serial_number_unique(self):
        for device in self:
            if device.serial_number:
                duplicate = self.search([
                    ('serial_number', '=', device.serial_number),
                    ('id', '!=', device.id)
                ])
                if duplicate:
                    raise ValidationError(
                        _('Serial number must be unique. Device "%s" already uses this serial number.') 
                        % duplicate.name
                    )
    
    @api.onchange('calibration_date', 'calibration_interval')
    def _onchange_calibration_date(self):
        if self.calibration_date and self.calibration_interval:
            self.next_calibration_date = fields.Date.add(
                self.calibration_date, 
                days=self.calibration_interval
            )
    
    def action_view_measurements(self):
        action = self.env.ref('measurement_data_management.action_measurement_record').read()[0]
        action['domain'] = [('device_id', '=', self.id)]
        action['context'] = {
            'default_device_id': self.id,
            'default_unit': self.measurement_unit,
        }
        return action
    
    def name_get(self):
        result = []
        for device in self:
            name = f"{device.name} ({device.serial_number})"
            result.append((device.id, name))
        return result
