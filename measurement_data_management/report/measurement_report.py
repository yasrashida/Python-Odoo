# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class MeasurementReport(models.AbstractModel):
    _name = 'report.measurement_data_management.measurement_device_report'
    _description = 'Measurement Device Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Generate report data for measurement device reports
        """
        devices = self.env['measurement.device'].browse(docids)
        
        report_data = []
        for device in devices:
            # Get recent measurements (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_measurements = device.measurement_record_ids.filtered(
                lambda r: r.measurement_date >= thirty_days_ago
            ).sorted('measurement_date', reverse=True)
            
            # Calculate statistics
            if recent_measurements:
                values = recent_measurements.mapped('value')
                statistics = {
                    'count': len(values),
                    'average': sum(values) / len(values),
                    'minimum': min(values),
                    'maximum': max(values),
                    'range': max(values) - min(values),
                }
                
                # Quality analysis
                quality_counts = {}
                for status in ['good', 'warning', 'critical', 'out_of_range']:
                    quality_counts[status] = len(recent_measurements.filtered(
                        lambda r: r.quality_status == status
                    ))
                
                # Operator analysis
                operators = recent_measurements.mapped('operator')
                operator_counts = {}
                for operator in set(operators):
                    if operator:
                        operator_counts[operator] = operators.count(operator)
                
            else:
                statistics = {
                    'count': 0,
                    'average': 0,
                    'minimum': 0,
                    'maximum': 0,
                    'range': 0,
                }
                quality_counts = {}
                operator_counts = {}
            
            # Calibration status
            calibration_status = 'unknown'
            if device.next_calibration_date:
                if device.next_calibration_date < fields.Date.today():
                    calibration_status = 'overdue'
                elif device.next_calibration_date <= fields.Date.today() + timedelta(days=30):
                    calibration_status = 'due_soon'
                else:
                    calibration_status = 'current'
            
            device_data = {
                'device': device,
                'recent_measurements': recent_measurements[:50],
                'statistics': statistics,
                'quality_counts': quality_counts,
                'operator_counts': operator_counts,
                'calibration_status': calibration_status,
            }
            report_data.append(device_data)
        
        return {
            'doc_ids': docids,
            'doc_model': 'measurement.device',
            'docs': devices,
            'report_data': report_data,
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }


class MeasurementRecordReport(models.AbstractModel):
    _name = 'report.measurement_data_management.measurement_record_report'
    _description = 'Measurement Records Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Generate report data for measurement records
        """
        records = self.env['measurement.record'].browse(docids)
        
        # Group records by device
        devices_data = {}
        for record in records:
            device_id = record.device_id.id
            if device_id not in devices_data:
                devices_data[device_id] = {
                    'device': record.device_id,
                    'records': [],
                    'statistics': {},
                }
            devices_data[device_id]['records'].append(record)
        
        # Calculate statistics for each device
        for device_data in devices_data.values():
            records_list = device_data['records']
            values = [r.value for r in records_list]
            
            if values:
                device_data['statistics'] = {
                    'count': len(values),
                    'average': sum(values) / len(values),
                    'minimum': min(values),
                    'maximum': max(values),
                    'std_dev': self._calculate_std_dev(values),
                }
            else:
                device_data['statistics'] = {
                    'count': 0,
                    'average': 0,
                    'minimum': 0,
                    'maximum': 0,
                    'std_dev': 0,
                }
        
        return {
            'doc_ids': docids,
            'doc_model': 'measurement.record',
            'docs': records,
            'devices_data': devices_data,
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    
    def _calculate_std_dev(self, values):
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5


class MeasurementAnalysisWizard(models.TransientModel):
    _name = 'measurement.analysis.wizard'
    _description = 'Measurement Analysis Report Wizard'

    device_ids = fields.Many2many(
        'measurement.device',
        string='Devices',
        help='Select devices for analysis'
    )
    
    date_from = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )
    
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.today
    )
    
    report_type = fields.Selection([
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Analysis'),
        ('quality', 'Quality Analysis'),
        ('trends', 'Trend Analysis'),
    ], string='Report Type', default='summary', required=True)
    
    include_charts = fields.Boolean(
        string='Include Charts',
        default=True,
        help='Include statistical charts in the report'
    )
    
    def action_generate_report(self):
        """Generate the analysis report"""
        self.ensure_one()
        
        # Get measurement records for the selected criteria
        domain = [
            ('measurement_date', '>=', self.date_from),
            ('measurement_date', '<=', self.date_to),
        ]
        
        if self.device_ids:
            domain.append(('device_id', 'in', self.device_ids.ids))
        
        records = self.env['measurement.record'].search(domain)
        
        if not records:
            raise UserError(_('No measurement records found for the selected criteria.'))
        
        # Generate report based on type
        if self.report_type == 'summary':
            return self._generate_summary_report(records)
        elif self.report_type == 'detailed':
            return self._generate_detailed_report(records)
        elif self.report_type == 'quality':
            return self._generate_quality_report(records)
        elif self.report_type == 'trends':
            return self._generate_trends_report(records)
    
    def _generate_summary_report(self, records):
        """Generate summary report"""
        return {
            'type': 'ir.actions.report',
            'report_name': 'measurement_data_management.measurement_summary_report',
            'report_type': 'qweb-pdf',
            'data': {
                'record_ids': records.ids,
                'wizard_data': {
                    'date_from': self.date_from,
                    'date_to': self.date_to,
                    'device_ids': self.device_ids.ids,
                    'report_type': self.report_type,
                }
            },
            'context': self.env.context,
        }
    
    def _generate_detailed_report(self, records):
        """Generate detailed analysis report"""
        pass
    
    def _generate_quality_report(self, records):
        """Generate quality analysis report"""
        pass
    
    def _generate_trends_report(self, records):
        """Generate trends analysis report"""
        pass
