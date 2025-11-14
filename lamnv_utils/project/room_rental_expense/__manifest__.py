{
    'name': 'Room Rental Expense Management',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Personal room rental expense and payment tracking',
    'description': """
        Module để quản lý chi phí phòng trọ cá nhân.
        
        Tính năng chính:
        - Quản lý thông tin phòng trọ và chủ phòng
        - Ghi chỉ số điện, nước hàng tháng
        - Tính hóa đơn tự động
        - Ghi nhận thanh toán
        - Quản lý chi phí phát sinh (sửa chữa, vệ sinh...)
        - Quản lý tiền cọc
        - Theo dõi sự cố phòng
        - Báo cáo và thống kê
        - Dashboard tổng hợp
    """,
    'author': 'lamnv',
    'depends': ['base', 'web'],
    'data': [
        # ================ SECURITY ================
        'security/ir.model.access.csv',
        # ================ VIEWS ================
        'views/rental_room_views.xml',
        'views/meter_reading_views.xml',
        'views/room_invoice_views.xml',
        'views/room_payment_views.xml',
        'views/room_expense_views.xml',
        'views/room_config_views.xml',
        'views/room_history_views.xml',
        'views/room_deposit_views.xml',
        'views/room_issue_views.xml',
        # ================ MENUS ================
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
