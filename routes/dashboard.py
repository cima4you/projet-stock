import json
from datetime import datetime, timedelta
from flask import render_template, session
from db import get_db
from utils import login_required
from notifications import check_expiring_products
from translations import TRANSLATIONS


def register_dashboard_routes(app):

    @app.route('/dashboard')
    @login_required
    def dashboard():
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as cnt FROM products WHERE deleted_at IS NULL')
            total_products = cursor.fetchone()['cnt']
            cursor.execute('SELECT COUNT(*) as cnt FROM products WHERE deleted_at IS NULL AND quantity <= 10')
            low_stock_items = cursor.fetchone()['cnt']
            cursor.execute('SELECT COUNT(*) as cnt FROM stock_movements')
            total_movements = cursor.fetchone()['cnt']
            cursor.execute('SELECT COUNT(*) as cnt FROM stock_movements WHERE movement_type = "entry"')
            total_entries = cursor.fetchone()['cnt']
            cursor.execute('SELECT COUNT(*) as cnt FROM stock_movements WHERE movement_type = "exit"')
            total_exits = cursor.fetchone()['cnt']
            cursor.execute('''
                SELECT sm.movement_type, sm.quantity, sm.notes, sm.created_at, p.name, u.username
                FROM stock_movements sm
                JOIN products p ON sm.product_id = p.id
                JOIN users u ON sm.user_id = u.id
                ORDER BY sm.created_at DESC LIMIT 10
            ''')
            recent_movements = cursor.fetchall()
            cursor.execute('SELECT code, name, quantity FROM products WHERE deleted_at IS NULL AND quantity <= 10 ORDER BY quantity ASC')
            low_stock_products = cursor.fetchall()
            cursor.execute('SELECT COUNT(*) FROM products WHERE deleted_at IS NULL AND quantity = 0')
            zero_stock_count = cursor.fetchone()[0]
            cursor.execute('''
                SELECT code, name, expiration_date
                FROM products
                WHERE deleted_at IS NULL AND expiration_date IS NOT NULL AND expiration_date < ?
                ORDER BY expiration_date DESC
            ''', (datetime.now().date().strftime('%Y-%m-%d'),))
            expired_products = cursor.fetchall()
            expired_count = len(expired_products)

            last_30 = []
            for i in range(29, -1, -1):
                last_30.append((datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'))

            chart_labels = []
            chart_entries = []
            chart_exits = []
            for day in last_30:
                chart_labels.append(day[-5:])
                cursor.execute("SELECT COUNT(*), COALESCE(SUM(quantity), 0) FROM stock_movements WHERE movement_type = 'entry' AND DATE(created_at) = ?", (day,))
                e = cursor.fetchone()
                chart_entries.append(e[1] or 0)
                cursor.execute("SELECT COUNT(*), COALESCE(SUM(quantity), 0) FROM stock_movements WHERE movement_type = 'exit' AND DATE(created_at) = ?", (day,))
                x = cursor.fetchone()
                chart_exits.append(x[1] or 0)

            cursor.execute("SELECT category, COUNT(*) as cnt FROM products WHERE deleted_at IS NULL AND category IS NOT NULL AND category != '' GROUP BY category ORDER BY cnt DESC LIMIT 10")
            cat_data = cursor.fetchall()
            cat_labels = [r[0] for r in cat_data]
            cat_counts = [r[1] for r in cat_data]

            cursor.execute('''
                SELECT p.name, SUM(sm.quantity) as total
                FROM stock_movements sm JOIN products p ON sm.product_id = p.id
                WHERE sm.movement_type = 'exit'
                GROUP BY sm.product_id ORDER BY total DESC LIMIT 10
            ''')
            top_moved = cursor.fetchall()
            top_moved_labels = [r[0][:20] for r in top_moved]
            top_moved_data = [r[1] for r in top_moved]

            cursor.execute('''
                SELECT supplier_name, COUNT(*) as cnt FROM products
                WHERE deleted_at IS NULL AND supplier_name IS NOT NULL AND supplier_name != ''
                GROUP BY supplier_name ORDER BY cnt DESC LIMIT 10
            ''')
            top_supps = cursor.fetchall()
            top_supp_labels = [r[0] for r in top_supps]
            top_supp_data = [r[1] for r in top_supps]

        expiring_products = check_expiring_products(30)

        expiring_count = len(expiring_products) if expiring_products else 0

        return render_template('dashboard.html',
                             total_products=total_products,
                             low_stock_items=low_stock_items,
                             total_movements=total_movements,
                             total_entries=total_entries,
                             total_exits=total_exits,
                             recent_movements=recent_movements,
                             low_stock_products=low_stock_products,
                             expiring_products=expiring_products,
                             expired_products=expired_products,
                             expired_count=expired_count,
                             expiring_count=expiring_count,
                             zero_stock_count=zero_stock_count,
                             chart_labels=json.dumps(chart_labels),
                             chart_entries=json.dumps(chart_entries),
                             chart_exits=json.dumps(chart_exits),
                             cat_labels=json.dumps(cat_labels),
                             cat_counts=json.dumps(cat_counts),
                             top_moved_labels=json.dumps(top_moved_labels),
                             top_moved_data=json.dumps(top_moved_data),
                             top_supp_labels=json.dumps(top_supp_labels),
                             top_supp_data=json.dumps(top_supp_data),
                             translations=TRANSLATIONS[session.get('lang', 'fr')],
                             lang=session.get('lang', 'fr'))
