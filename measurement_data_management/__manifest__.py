{
    'name': 'Measurement Data Management',
    'version': '16.0.0.0.0',
    'category': 'Manufacturing',
    'summary': 'Manage measurement data from devices with CSV import capability',
    'description': """
        Measurement Data Management Module
        ==================================
                
        Key Features:
        * Device management with serial numbers and types
        * Manual measurement record entry
        * CSV import for data
        * Advanced search and filtering
        * Excel/PDF export capability
    """,
    'author': 'Yasaman Rashida',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/measurement_device_views.xml',
        'views/measurement_record_views.xml',
        'wizard/measurement_import_wizard_views.xml',  
        'report/measurement_report_template.xml',
        'views/menu_views.xml',                       
        'data/measurement_device_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
