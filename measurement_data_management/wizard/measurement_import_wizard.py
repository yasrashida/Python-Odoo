# -*- coding: utf-8 -*-
import base64
import csv
import io
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class MeasurementImportWizard(models.TransientModel):
    _name = 'measurement.import.wizard'
    _description = 'Measurement Data Import Wizard'

    name = fields.Char(string='Import Name', required=True, default='CSV Import')
    csv_file = fields.Binary(string='CSV File', required=True)
    filename = fields.Char(string='Filename')
    delimiter = fields.Selection([
        (',', 'Comma (,)'),
        (';', 'Semicolon (;)'),
        ('\t', 'Tab'),
        ('|', 'Pipe (|)'),
    ], string='Delimiter', default=',', required=True)
    
    has_header = fields.Boolean(string='Has Header Row', default=True)
    device_id = fields.Many2one('measurement.device', string='Default Device')
    unit = fields.Char(string='Default Unit')
    operator = fields.Char(string='Default Operator')
    
    preview_data = fields.Text(string='Preview Data', readonly=True)
    import_summary = fields.Text(string='Import Summary', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('preview', 'Preview'),
        ('done', 'Done'),
    ], default='draft')
    
    def action_preview(self):
        self.ensure_one()
        if not self.csv_file:
            raise UserError(_('Please select a CSV file to import.'))
        
        try:
            csv_data = base64.b64decode(self.csv_file).decode('utf-8')
            csv_reader = csv.reader(io.StringIO(csv_data), delimiter=self.delimiter)
            
            rows = list(csv_reader)
            if not rows:
                raise UserError(_('The CSV file is empty.'))
            
            # Generate preview
            preview_lines = []
            max_preview_rows = 10
            
            if self.has_header and len(rows) > 0:
                header = rows[0]
                preview_lines.append(f"Header: {', '.join(header)}")
                preview_lines.append("-" * 50)
                data_rows = rows[1:max_preview_rows+1]
            else:
                data_rows = rows[:max_preview_rows]
            
            for i, row in enumerate(data_rows):
                preview_lines.append(f"Row {i+1}: {', '.join(row)}")
            
            if len(rows) > max_preview_rows + (1 if self.has_header else 0):
                preview_lines.append(f"... and {len(rows) - max_preview_rows - (1 if self.has_header else 0)} more rows")
            
            self.preview_data = '\\n'.join(preview_lines)
            self.state = 'preview'
            
        except Exception as e:
            raise UserError(_('Error reading CSV file: %s') % str(e))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'measurement.import.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
    
    def action_import(self):
        self.ensure_one()
        if not self.csv_file:
            raise UserError(_('Please select a CSV file to import.'))
        
        try:
            csv_data = base64.b64decode(self.csv_file).decode('utf-8')
            csv_reader = csv.reader(io.StringIO(csv_data), delimiter=self.delimiter)
            
            rows = list(csv_reader)
            if not rows:
                raise UserError(_('The CSV file is empty.'))
            
            # Process header
            if self.has_header and len(rows) > 0:
                header = [h.strip().lower() for h in rows[0]]
                data_rows = rows[1:]
            else:
                header = None
                data_rows = rows
            
            # Generate import session ID
            import_session_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Import data
            created_records = []
            errors = []
            
            for row_num, row in enumerate(data_rows, start=2 if self.has_header else 1):
                try:
                    record_data = self._parse_row(row, header, import_session_id)
                    if record_data:
                        record = self.env['measurement.record'].create(record_data)
                        created_records.append(record)
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            
            # Generate summary
            summary_lines = [
                f"Import completed: {self.name}",
                f"File: {self.filename}",
                f"Total rows processed: {len(data_rows)}",
                f"Records created: {len(created_records)}",
                f"Errors: {len(errors)}",
            ]
            
            if errors:
                summary_lines.append("\\nErrors:")
                summary_lines.extend(errors[:10])  # Limit error display
                if len(errors) > 10:
                    summary_lines.append(f"... and {len(errors) - 10} more errors")
            
            self.import_summary = '\\n'.join(summary_lines)
            self.state = 'done'
            
            # Log import
            _logger.info(f"CSV import completed: {len(created_records)} records created, {len(errors)} errors")
            
        except Exception as e:
            raise UserError(_('Error importing CSV file: %s') % str(e))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'measurement.import.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
    
    def _parse_row(self, row, header, import_session_id):
        """Parse a single CSV row into measurement record data"""
        if not row or all(not cell.strip() for cell in row):
            return None
        
        # Map columns based on header or position
        if header:
            row_dict = dict(zip(header, row))
            
            # Extract data from named columns
            device_name = row_dict.get('device') or row_dict.get('device_name')
            serial_number = row_dict.get('serial_number') or row_dict.get('serial')
            measurement_date = row_dict.get('date') or row_dict.get('measurement_date') or row_dict.get('timestamp')
            value = row_dict.get('value') or row_dict.get('measurement_value')
            unit = row_dict.get('unit') or row_dict.get('measurement_unit')
            operator = row_dict.get('operator') or row_dict.get('user')
            notes = row_dict.get('notes') or row_dict.get('comment')
            
        else:
            # Use positional mapping: device, date, value, unit, operator, notes
            device_name = row[0] if len(row) > 0 else None
            serial_number = None
            measurement_date = row[1] if len(row) > 1 else None
            value = row[2] if len(row) > 2 else None
            unit = row[3] if len(row) > 3 else None
            operator = row[4] if len(row) > 4 else None
            notes = row[5] if len(row) > 5 else None
        
        # Find or use device
        device = None
        if device_name and device_name.strip():
            device = self.env['measurement.device'].search([
                ('name', '=', device_name.strip())
            ], limit=1)
            if not device and serial_number:
                device = self.env['measurement.device'].search([
                    ('serial_number', '=', serial_number.strip())
                ], limit=1)
        
        if not device:
            device = self.device_id
        
        if not device:
            raise ValidationError(_('Device not found: %s') % (device_name or 'Unknown'))
        
        # Parse measurement date
        if measurement_date and measurement_date.strip():
            try:
                # Try different date formats
                date_formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M',
                    '%Y-%m-%d',
                    '%d/%m/%Y %H:%M:%S',
                    '%d/%m/%Y %H:%M',
                    '%d/%m/%Y',
                    '%m/%d/%Y %H:%M:%S',
                    '%m/%d/%Y %H:%M',
                    '%m/%d/%Y',
                ]
                
                parsed_date = None
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(measurement_date.strip(), fmt)
                        break
                    except ValueError:
                        continue
                
                if not parsed_date:
                    raise ValidationError(_('Invalid date format: %s') % measurement_date)
                
                measurement_date = parsed_date
            except Exception as e:
                raise ValidationError(_('Error parsing date "%s": %s') % (measurement_date, str(e)))
        else:
            measurement_date = fields.Datetime.now()
        
        # Parse value
        if not value or not str(value).strip():
            raise ValidationError(_('Measurement value is required'))
        
        try:
            value = float(str(value).strip())
        except ValueError:
            raise ValidationError(_('Invalid measurement value: %s') % value)
        
        # Prepare record data
        record_data = {
            'device_id': device.id,
            'measurement_date': measurement_date,
            'value': value,
            'unit': (unit and unit.strip()) or self.unit or device.measurement_unit or '',
            'operator': (operator and operator.strip()) or self.operator or '',
            'notes': (notes and notes.strip()) or '',
            'measurement_type': 'imported',
            'import_session_id': import_session_id,
        }
        
        return record_data
    
    def action_view_imported_records(self):
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_('Import has not been completed yet.'))
        
        import_session_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Imported Records'),
            'res_model': 'measurement.record',
            'view_mode': 'tree,form',
            'domain': [('import_session_id', '=', import_session_id)],
            'context': {'create': False},
        }