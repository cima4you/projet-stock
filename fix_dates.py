import os
import sqlite3
from datetime import datetime, timedelta

def fix_stock_movements_dates(db_path):
    """Convert Excel serial numbers in stock_movements.created_at to proper ISO datetime strings."""
    def excel_to_iso(excel_num_str):
        try:
            num = float(excel_num_str)
            if num < 1:
                return None
            base_date = datetime(1899, 12, 30)
            days = int(num)
            seconds = int((num - days) * 86400)
            dt = base_date + timedelta(days=days, seconds=seconds)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"Error converting {excel_num_str}: {e}")
            return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, created_at FROM stock_movements")
    rows = cursor.fetchall()
    
    fixed_count = 0
    for row_id, created_at in rows:
        if not (isinstance(created_at, str) and len(created_at) >= 10 and created_at[4] == '-' and created_at[7] == '-'):
            iso_date = excel_to_iso(created_at)
            if iso_date:
                cursor.execute("UPDATE stock_movements SET created_at = ? WHERE id = ?", (iso_date, row_id))
                fixed_count += 1
                print(f"✅ Fixed row {row_id}: {created_at} → {iso_date}")
    
    conn.commit()
    conn.close()
    print(f"\n🎉 تم إصلاح {fixed_count} سجلًا في جدول stock_movements.")

if __name__ == '__main__':
    # نفس منطق main.py: stock.db في نفس مجلد هذا الملف
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'stock.db')
    print(f"Using database: {db_path}")
    if not os.path.exists(db_path):
        print("❌ خطأ: لم يتم العثور على ملف stock.db في نفس المجلد!")
        exit(1)
    fix_stock_movements_dates(db_path)