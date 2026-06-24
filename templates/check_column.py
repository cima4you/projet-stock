import sqlite3

# مسار قاعدة البيانات
db_path = 'stock.db'

def check_notify_exit_column():
    try:
        # الاتصال بقاعدة البيانات
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # استعراض أعمدة الجدول notification_recipients
        cursor.execute("PRAGMA table_info(notification_recipients)")
        columns = cursor.fetchall()

        # إغلاق الاتصال
        conn.close()

        # عرض الأعمدة
        print("📋 الأعمدة الموجودة في جدول notification_recipients:")
        column_names = []
        for col in columns:
            print(f"  - {col[1]} (نوع: {col[2]}, افتراضي: {col[4]})")
            column_names.append(col[1])

        # التحقق من وجود notify_exit
        print("\n🔍 التحقق من وجود العمود notify_exit:")
        if 'notify_exit' in column_names:
            print("✅ نعم، العمود 'notify_exit' موجود.")
        else:
            print("❌ لا، العمود 'notify_exit' غير موجود.")

    except Exception as e:
        print(f"❌ خطأ: {e}")

# تشغيل الدالة
if __name__ == '__main__':
    check_notify_exit_column()