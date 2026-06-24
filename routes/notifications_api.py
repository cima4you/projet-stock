from flask import session, jsonify
from db import query, execute


def register_notifications_api_routes(app):
    @app.route('/api/unread_notifications')
    def unread_notifications():
        username = session.get('username')
        if not username:
            return jsonify([])
        rows = query('''
            SELECT n.id, n.recipient_email, n.notification_type, n.subject,
                   n.content, n.sent_at as created_at, n.status
            FROM notification_logs n
            WHERE n.status = 'sent'
            ORDER BY n.sent_at DESC LIMIT 20
        ''') or []
        return jsonify([{
            'id': r['id'],
            'recipient_email': r['recipient_email'],
            'notification_type': r['notification_type'],
            'subject': r['subject'],
            'content': r['content'],
            'created_at': r['created_at'],
            'status': r['status'],
        } for r in rows])

    @app.route('/api/mark_notification_read/<int:notification_id>')
    def mark_notification_read(notification_id):
        execute('UPDATE notification_logs SET status = ? WHERE id = ?',
                ('read', notification_id))
        return jsonify({'ok': True})

    @app.route('/api/unread_count')
    def unread_count():
        username = session.get('username')
        if not username:
            return jsonify({'count': 0})
        row = query('SELECT COUNT(*) as cnt FROM notification_logs WHERE status = ?', ('sent',))
        return jsonify({'count': row[0]['cnt'] if row else 0})
