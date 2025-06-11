# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MeasurementRecord(models.Model):
    _name = 'measurement.record'
    _description = 'Measurement Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'measurement_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    device_id = fields.Many2one(
        'measurement.device',
        string='Device',
        required=True,
        tracking=True,
        help="Device used for this measurement"
    )
    
    measurement_date = fields.Datetime(
        string='Measurement Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        help="Date and time when measurement was taken"
    )
    
    value = fields.Float(
        string='Value',
        required=True,
        digits=(16, 6),
        tracking=True,
        help="Measured value"
    )
    
    unit = fields.Char(
        string='Unit',
        required=True,
        tracking=True,
        help="Unit of measurement"
    )
    
    operator = fields.Char(
        string='Operator',
        tracking=True,
        help="Person who performed the measurement"
    )
    
    measurement_type = fields.Selection([
        ('manual', 'Manual Entry'),
        ('imported', 'CSV Import'),
        ('automatic', 'Automatic'),
    ], string='Measurement Type', default='manual', tracking=True)
    
    quality_status = fields.Selection([
        ('good', 'Good'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('out_of_range', 'Out of Range'),
    ], string='Quality Status', compute='_compute_quality_status', store=True)
    
    temperature = fields.Float(
        string='Ambient Temperature',
        help="Ambient temperature during measurement"
    )
    
    humidity = fields.Float(
        string='Humidity (%)',
        help="Ambient humidity during measurement"
    )
    
    notes = fields.Text(
        string='Notes',
        help="Additional notes about the measurement"
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
        help="Files related to this measurement"
    )
    
    batch_id = fields.Char(
        string='Batch ID',
        help="Batch identifier for grouped measurements"
    )
    
    import_session_id = fields.Char(
        string='Import Session',
        help="Session ID for CSV imports"
    )
    
    is_validated = fields.Boolean(
        string='Validated',
        default=False,
        tracking=True,
        help="Mark as validated by quality control"
    )
    
    validated_by = fields.Many2one(
        'res.users',
        string='Validated By',
        help="User who validated this measurement"
    )
    
    validated_date = fields.Datetime(
        string='Validation Date',
        help="Date when measurement was validated"
    )
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('measurement.record') or _('New')
        return super().create(vals)
    
    @api.depends('value', 'device_id.min_range', 'device_id.max_range')
    def _compute_quality_status(self):
        for record in self:
            if record.device_id.min_range and record.device_id.max_range:
                min_range = record.device_id.min_range
                max_range = record.device_id.max_range
                value = record.value
                
                if value < min_range or value > max_range:
                    record.quality_status = 'out_of_range'
                elif value < min_range * 1.1 or value > max_range * 0.9:
                    record.quality_status = 'warning'
                else:
                    record.quality_status = 'good'
            else:
                record.quality_status = 'good'
    
    @api.onchange('device_id')
    def _onchange_device_id(self):
        if self.device_id:
            self.unit = self.device_id.measurement_unit or ''
    
    def action_validate(self):
        self.write({
            'is_validated': True,
            'validated_by': self.env.user.id,
            'validated_date': fields.Datetime.now(),
        })
        self.message_post(body=_("Measurement validated by %s") % self.env.user.name)
    
    def action_invalidate(self):
        self.write({
            'is_validated': False,
            'validated_by': False,
            'validated_date': False,
        })
        self.message_post(body=_("Measurement validation removed by %s") % self.env.user.name)
    
    @api.constrains('value')
    def _check_value(self):
        for record in self:
            if record.device_id.min_range and record.value < record.device_id.min_range:
                _logger.warning(f"Measurement value {record.value} is below device minimum range {record.device_id.min_range}")
            if record.device_id.max_range and record.value > record.device_id.max_range:
                _logger.warning(f"Measurement value {record.value} is above device maximum range {record.device_id.max_range}")