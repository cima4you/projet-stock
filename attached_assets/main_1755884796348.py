import os
import sqlite3
import logging
import smtplib
import secrets
import pandas as pd
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify, send_from_directory, Response
from flask_moment import Moment
from dotenv import load_dotenv
from PIL import Image
import io
import json
from io import BytesIO
import xlsxwriter
from translations import TRANSLATIONS
import numpy as np
from datetime import date, datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback_secret_key_change_in_production")
moment = Moment(app)

# Email Configuration - Now using environment variables
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
NOTIFICATION_EMAIL = os.environ.get('NOTIFICATION_EMAIL', EMAIL_ADDRESS)

# Debug print to check if variables are loaded
logger.debug(f"Loaded EMAIL_ADDRESS: {EMAIL_ADDRESS is not None}")
logger.debug(f"Loaded EMAIL_PASSWORD: {EMAIL_PASSWORD is not None}")

# Upload configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
LOGO_FOLDER = os.path.join(os.getcwd(), 'static', 'logos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'xlsx', 'xls'}
LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['LOGO_FOLDER'] = LOGO_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOGO_FOLDER, exist_ok=True)
os.makedirs('email_templates', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('static/images', exist_ok=True)
os.makedirs('static/logos', exist_ok=True)
os.makedirs('templates', exist_ok=True)

def allowed_file(filename, extensions=None):
    if extensions is None:
        extensions = ALLOWED_EXTENSIONS
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions

def allowed_logo_file(filename):
    return allowed_file(filename, LOGO_EXTENSIONS)

def allowed_excel_file(filename):
    excel_extensions = {'xlsx', 'xls'}
    return allowed_file(filename, excel_extensions)

class StockManagementSystem:
    def __init__(self, db_path=None):
        self.db_path = "stock.db"
        self.init_database()
        
    def init_database(self):
        """Initialize the database with all required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                reset_token TEXT,
                reset_token_expires TIMESTAMP
            )
        ''')
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                unit TEXT,
                quantity INTEGER DEFAULT 0,
                brand TEXT,
                condition_status TEXT,
                chanter TEXT,
                storage_zone TEXT,
                notes TEXT,
                supplier_name TEXT,
                bc_number TEXT,
                bl_number TEXT,
                n_facture TEXT,
                type_achat TEXT,
                expiration_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Stock movements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                notes TEXT,
                user_id INTEGER NOT NULL,
                supplier_name TEXT,
                bc_number TEXT,
                bl_number TEXT,
                n_facture TEXT,
                type_achat TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Notification recipients table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                notify_achat_par_bc INTEGER DEFAULT 1,
                notify_achat_par_caisse INTEGER DEFAULT 1,
                notify_achat_a_regulariser INTEGER DEFAULT 1,
                notify_transfert INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if default user exists, if not create one with default password
        cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
        if cursor.fetchone()[0] == 0:
            default_password = 'bj319260'
            password_hash = generate_password_hash(default_password)
            cursor.execute('''
                INSERT INTO users (username, password_hash, email, role) 
                VALUES (?, ?, ?, ?)
            ''', ('admin', password_hash, 'bazigherachid@gmail.com', 'principal_admin'))
            logger.info("Created default admin user with password: bj319260")
        
        conn.commit()
        conn.close()
        
    def send_email(self, to_email, subject, body, html_body=None):
        """Send an email using configured SMTP settings."""
        try:
            if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
                logger.error("Email credentials not configured properly")
                return False
                
            logger.info(f"Attempting to send email to {to_email}")
            
            msg = MIMEMultipart('alternative')
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            if html_body:
                msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL_ADDRESS, to_email, text)
            server.quit()

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_password_reset_email(self, to_email, reset_token, lang='fr'):
        """Send password reset email"""
        reset_url = f"{request.host_url}reset_password/{reset_token}"
        
        if lang == 'ar':
            subject = "إعادة تعيين كلمة المرور - نظام إدارة المخزون"
            
            try:
                with open('email_templates/password_reset_ar.html', 'r', encoding='utf-8') as f:
                    html_template = f.read()
                html_body = html_template.replace('{{reset_url}}', reset_url)
            except FileNotFoundError:
                html_body = f"""
                <html dir="rtl">
                <body style="font-family: Arial, sans-serif; direction: rtl; text-align: right;">
                    <h2>إعادة تعيين كلمة المرور</h2>
                    <p>تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بك.</p>
                    <p>انقر على الرابط أدناه لإعادة تعيين كلمة المرور:</p>
                    <p><a href="{reset_url}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">إعادة تعيين كلمة المرور</a></p>
                    <p>إذا لم تطلب إعادة تعيين كلمة المرور، يرجى تجاهل هذا البريد الإلكتروني.</p>
                    <p>الرابط صالح لمدة ساعة واحدة فقط.</p>
                </body>
                </html>
                """
            
            body = f"""
إعادة تعيين كلمة المرور

تلقينا طلباً لإعادة تعيين كلمة المرور الخاصة بك.

انسخ الرابط التالي والصقه في متصفحك لإعادة تعيين كلمة المرور:
{reset_url}

إذا لم تطلب إعادة تعيين كلمة المرور، يرجى تجاهل هذا البريد الإلكتروني.
الرابط صالح لمدة ساعة واحدة فقط.
            """
        else:
            subject = "Réinitialisation du mot de passe - Système de gestion de stock"
            
            try:
                with open('email_templates/password_reset_fr.html', 'r', encoding='utf-8') as f:
                    html_template = f.read()
                html_body = html_template.replace('{{reset_url}}', reset_url)
            except FileNotFoundError:
                html_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Réinitialisation du mot de passe</h2>
                    <p>Nous avons reçu une demande de réinitialisation de votre mot de passe.</p>
                    <p>Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe :</p>
                    <p><a href="{reset_url}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Réinitialiser le mot de passe</a></p>
                    <p>Si vous n'avez pas demandé de réinitialisation, veuillez ignorer cet email.</p>
                    <p>Ce lien est valide pendant une heure seulement.</p>
                </body>
                </html>
                """
            
            body = f"""
Réinitialisation du mot de passe

Nous avons reçu une demande de réinitialisation de votre mot de passe.

Copiez et collez le lien suivant dans votre navigateur pour réinitialiser votre mot de passe :
{reset_url}

Si vous n'avez pas demandé de réinitialisation, veuillez ignorer cet email.
Ce lien est valide pendant une heure seulement.
            """
        
        return self.send_email(to_email, subject, body, html_body)

    def import_products_from_excel(self, file_path, user_id):
        """Import products from Excel file"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Define expected columns and their mappings
            column_mapping = {
                'كود المنتج': 'code',
                'Product Code': 'code',
                'code': 'code',
                'اسم المنتج': 'name',
                'Product Name': 'name',
                'name': 'name',
                'الفئة': 'category',
                'Category': 'category',
                'category': 'category',
                'الوحدة': 'unit',
                'Unit': 'unit',
                'unit': 'unit',
                'الكمية': 'quantity',
                'Quantity': 'quantity',
                'quantity': 'quantity',
                'الماركة': 'brand',
                'Brand': 'brand',
                'brand': 'brand',
                'الحالة': 'condition_status',
                'Condition': 'condition_status',
                'condition_status': 'condition_status',
                'الورشة': 'chanter',
                'Workshop': 'chanter',
                'chanter': 'chanter',
                'منطقة التخزين': 'storage_zone',
                'Storage Zone': 'storage_zone',
                'storage_zone': 'storage_zone',
                'ملاحظات': 'notes',
                'Notes': 'notes',
                'notes': 'notes',
                'اسم المورد': 'supplier_name',
                'Supplier Name': 'supplier_name',
                'supplier_name': 'supplier_name',
                'رقم أمر الشراء': 'bc_number',
                'BC Number': 'bc_number',
                'bc_number': 'bc_number',
                'رقم بوليصة الشحن': 'bl_number',
                'BL Number': 'bl_number',
                'bl_number': 'bl_number',
                'رقم الفاتورة': 'n_facture',
                'Invoice Number': 'n_facture',
                'n_facture': 'n_facture',
                'نوع الشراء': 'type_achat',
                'Purchase Type': 'type_achat',
                'type_achat': 'type_achat',
                'تاريخ انتهاء الصلاحية': 'expiration_date',
                'Expiration Date': 'expiration_date',
                'expiration_date': 'expiration_date'
            }
            
            # Normalize column names
            df_normalized = df.copy()
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df_normalized = df_normalized.rename(columns={old_col: new_col})
            
            # Check for required columns
            required_columns = ['code', 'name']
            missing_columns = [col for col in required_columns if col not in df_normalized.columns]
            if missing_columns:
                return False, f"Missing required columns: {', '.join(missing_columns)}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            imported_count = 0
            skipped_count = 0
            errors = []
            
            for index, row in df_normalized.iterrows():
                try:
                    # Check for required fields
                    if pd.isna(row['code']) or pd.isna(row['name']):
                        errors.append(f"Row {index + 2}: Missing required fields (code or name)")
                        continue
                    
                    # Check if product code already exists
                    cursor.execute('SELECT COUNT(*) FROM products WHERE code = ?', (str(row['code']),))
                    if cursor.fetchone()[0] > 0:
                        skipped_count += 1
                        errors.append(f"Row {index + 2}: Product code '{row['code']}' already exists")
                        continue
                    
                    # Prepare product data
                    product_data = {
                        'code': str(row['code']),
                        'name': str(row['name']),
                        'category': str(row.get('category', '')) if pd.notna(row.get('category')) else '',
                        'unit': str(row.get('unit', '')) if pd.notna(row.get('unit')) else '',
                        'quantity': int(row.get('quantity', 0)) if pd.notna(row.get('quantity')) else 0,
                        'brand': str(row.get('brand', '')) if pd.notna(row.get('brand')) else '',
                        'condition_status': str(row.get('condition_status', '')) if pd.notna(row.get('condition_status')) else '',
                        'chanter': str(row.get('chanter', '')) if pd.notna(row.get('chanter')) else '',
                        'storage_zone': str(row.get('storage_zone', '')) if pd.notna(row.get('storage_zone')) else '',
                        'notes': str(row.get('notes', '')) if pd.notna(row.get('notes')) else '',
                        'supplier_name': str(row.get('supplier_name', '')) if pd.notna(row.get('supplier_name')) else '',
                        'bc_number': str(row.get('bc_number', '')) if pd.notna(row.get('bc_number')) else '',
                        'bl_number': str(row.get('bl_number', '')) if pd.notna(row.get('bl_number')) else '',
                        'n_facture': str(row.get('n_facture', '')) if pd.notna(row.get('n_facture')) else '',
                        'type_achat': str(row.get('type_achat', '')) if pd.notna(row.get('type_achat')) else '',
                        'expiration_date': None
                    }
                    
                    # Handle expiration date
                    if pd.notna(row.get('expiration_date')):
                        try:
                            exp_date = pd.to_datetime(row['expiration_date'])
                            product_data['expiration_date'] = exp_date.strftime('%Y-%m-%d')
                        except:
                            pass  # Keep as None if conversion fails
                    
                    # Insert product
                    cursor.execute('''
                        INSERT INTO products (
                            code, name, category, unit, quantity, brand, condition_status,
                            chanter, storage_zone, notes, supplier_name, bc_number,
                            bl_number, n_facture, type_achat, expiration_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        product_data['code'], product_data['name'], product_data['category'],
                        product_data['unit'], product_data['quantity'], product_data['brand'],
                        product_data['condition_status'], product_data['chanter'],
                        product_data['storage_zone'], product_data['notes'],
                        product_data['supplier_name'], product_data['bc_number'],
                        product_data['bl_number'], product_data['n_facture'],
                        product_data['type_achat'], product_data['expiration_date']
                    ))
                    
                    product_id = cursor.lastrowid
                    
                    # Create initial stock movement if quantity > 0
                    if product_data['quantity'] > 0:
                        cursor.execute('''
                            INSERT INTO stock_movements (
                                product_id, movement_type, quantity, notes, user_id,
                                supplier_name, bc_number, bl_number, n_facture, type_achat
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            product_id, 'entry', product_data['quantity'],
                            'Initial stock from Excel import', user_id,
                            product_data['supplier_name'], product_data['bc_number'],
                            product_data['bl_number'], product_data['n_facture'],
                            product_data['type_achat']
                        ))
                    
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    continue
            
            conn.commit()
            conn.close()
            
            # Prepare result message
            result_message = f"Imported {imported_count} products successfully."
            if skipped_count > 0:
                result_message += f" Skipped {skipped_count} products (duplicate codes)."
            if errors:
                result_message += f" {len(errors)} errors occurred."
            
            return True, result_message, errors
            
        except Exception as e:
            logger.error(f"Error importing Excel file: {str(e)}")
            return False, f"Error reading Excel file: {str(e)}", []

# Initialize the system
stock_system = StockManagementSystem()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') not in ['admin', 'principal_admin']:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def principal_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'principal_admin':
            flash('Access denied. Principal admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function for translations
def _(key, lang=None):
    if lang is None:
        lang = session.get('language', 'fr')
    return TRANSLATIONS.get(lang, {}).get(key, key)

# Language switching
@app.route('/set_language/<language>')
def set_language(language):
    if language in ['ar', 'fr']:
        session['language'] = language
    return redirect(request.referrer or url_for('dashboard'))

# Home page redirects to login
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(stock_system.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, password_hash, email, role, active FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user and user[5] == 1 and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = user[3]
            session['role'] = user[4]
            
            # Update last login
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user[0],))
            conn.commit()
            
            flash(_('login_successful'), 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(_('invalid_credentials'), 'error')
        
        conn.close()
    
    return render_template('login.html', _=_)

@app.route('/logout')
def logout():
    session.clear()
    flash(_('logged_out_successfully'), 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()

    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM products')
    total_products = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM products WHERE quantity <= 5 AND quantity > 0')
    low_stock_items = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM stock_movements')
    total_movements = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM stock_movements WHERE movement_type = 'entry'")
    total_entries = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM stock_movements WHERE movement_type = 'exit'")
    total_exits = cursor.fetchone()[0]

    # === ✅ تحديث الاستعلام لتشمل username ===
    cursor.execute('''
        SELECT sm.movement_type, sm.quantity, sm.notes, sm.created_at,
               p.name, p.code, u.username
        FROM stock_movements sm
        JOIN products p ON sm.product_id = p.id
        JOIN users u ON sm.user_id = u.id
        ORDER BY sm.created_at DESC
        LIMIT 10
    ''')
    recent_movements = cursor.fetchall()
    # الآن كل حركة تحتوي على 7 عناصر: [0] إلى [6]

    # Get low stock products
    cursor.execute('''
        SELECT code, name, quantity, category
        FROM products
        WHERE quantity <= 5 AND quantity > 0
        ORDER BY quantity ASC
        LIMIT 10
    ''')
    low_stock_products = cursor.fetchall()

    # Expiring products
    cursor.execute('''
        SELECT code, name, expiration_date, quantity
        FROM products
        WHERE expiration_date IS NOT NULL 
        AND date(expiration_date) BETWEEN date('now') AND date('now', '+30 days')
        ORDER BY expiration_date ASC
        LIMIT 10
    ''')
    expiring_products = cursor.fetchall()

    conn.close()

    return render_template('dashboard.html', 
                         total_products=total_products,
                         low_stock_items=low_stock_items,
                         total_movements=total_movements,
                         total_entries=total_entries,
                         total_exits=total_exits,
                         recent_movements=recent_movements,
                         low_stock_products=low_stock_products,
                         expiring_products=expiring_products,
                         _=_)

# Products routes
@app.route('/products')
@login_required
def products():
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()
    
    # Get filter parameters
    search = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    
    # Build query
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (code LIKE ? OR name LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if category_filter:
        query += ' AND category = ?'
        params.append(category_filter)
    
    query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    
    # Get categories for filter
    cursor.execute('SELECT DISTINCT category FROM products WHERE category != "" ORDER BY category')
    categories = [cat[0] for cat in cursor.fetchall()]
    
    conn.close()
    
    return render_template('products.html', 
                         products=products,
                         categories=categories,
                         search=search,
                         category_filter=category_filter,
                         _=_)

@app.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        try:
            conn = sqlite3.connect(stock_system.db_path)
            cursor = conn.cursor()
            
            # Check if product code already exists
            cursor.execute('SELECT COUNT(*) FROM products WHERE code = ?', (request.form['code'],))
            if cursor.fetchone()[0] > 0:
                flash(_('product_code_already_exists'), 'error')
                return render_template('add_product.html', _=_)
            
            # Insert product
            cursor.execute('''
                INSERT INTO products (
                    code, name, category, unit, quantity, brand, condition_status,
                    chanter, storage_zone, notes, supplier_name, bc_number,
                    bl_number, n_facture, type_achat, expiration_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request.form['code'],
                request.form['name'],
                request.form.get('category', ''),
                request.form.get('unit', ''),
                int(request.form.get('quantity', 0)),
                request.form.get('brand', ''),
                request.form.get('condition_status', ''),
                request.form.get('chanter', ''),
                request.form.get('storage_zone', ''),
                request.form.get('notes', ''),
                request.form.get('supplier_name', ''),
                request.form.get('bc_number', ''),
                request.form.get('bl_number', ''),
                request.form.get('n_facture', ''),
                request.form.get('type_achat', ''),
                request.form.get('expiration_date') if request.form.get('expiration_date') else None
            ))
            
            product_id = cursor.lastrowid
            
            # Create initial stock movement if quantity > 0
            quantity = int(request.form.get('quantity', 0))
            if quantity > 0:
                cursor.execute('''
                    INSERT INTO stock_movements (
                        product_id, movement_type, quantity, notes, user_id,
                        supplier_name, bc_number, bl_number, n_facture, type_achat
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product_id, 'entry', quantity, 'Initial stock', session['user_id'],
                    request.form.get('supplier_name', ''),
                    request.form.get('bc_number', ''),
                    request.form.get('bl_number', ''),
                    request.form.get('n_facture', ''),
                    request.form.get('type_achat', '')
                ))
            
            conn.commit()
            conn.close()
            
            flash(_('product_added_successfully'), 'success')
            return redirect(url_for('products'))
        
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('add_product.html', _=_)

# Import products route
@app.route('/products/import', methods=['GET', 'POST'])
@login_required
def import_products():
    if request.method == 'POST':
        try:
            # Check if file was uploaded
            if 'file' not in request.files:
                flash(_('no_file_selected'), 'error')
                return redirect(request.url)
            
            file = request.files['file']
            
            if file.filename == '':
                flash(_('no_file_selected'), 'error')
                return redirect(request.url)
            
            if file and allowed_excel_file(file.filename):
                # Secure filename
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = timestamp + filename
                
                # Save file
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                try:
                    # Import products
                    success, message, errors = stock_system.import_products_from_excel(
                        file_path, session['user_id']
                    )
                    
                    if success:
                        flash(_('products_imported_successfully') + ' ' + message, 'success')
                        if errors:
                            # Store errors in session to show on next page
                            session['import_errors'] = errors[:20]  # Limit to 20 errors
                    else:
                        flash(_('error_importing_products') + ': ' + message, 'error')
                    
                except Exception as e:
                    flash(_('error_importing_products') + ': ' + str(e), 'error')
                
                finally:
                    # Clean up uploaded file
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                return redirect(url_for('products'))
            
            else:
                flash(_('invalid_file_type'), 'error')
        
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('import_products.html', _=_)

# Show import errors
@app.route('/products/import_errors')
@login_required
def import_errors():
    errors = session.pop('import_errors', [])
    return render_template('import_errors.html', errors=errors, _=_)

# Edit product route
@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            # Check if product code already exists (excluding current product)
            cursor.execute('SELECT COUNT(*) FROM products WHERE code = ? AND id != ?', 
                         (request.form['code'], product_id))
            if cursor.fetchone()[0] > 0:
                flash(_('product_code_already_exists'), 'error')
                cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
                product = cursor.fetchone()
                conn.close()
                return render_template('edit_product.html', product=product, _=_)
            
            # Update product
            cursor.execute('''
                UPDATE products SET 
                code=?, name=?, category=?, unit=?, brand=?, condition_status=?,
                chanter=?, storage_zone=?, notes=?, supplier_name=?, bc_number=?,
                bl_number=?, n_facture=?, type_achat=?, expiration_date=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (
                request.form['code'],
                request.form['name'],
                request.form.get('category', ''),
                request.form.get('unit', ''),
                request.form.get('brand', ''),
                request.form.get('condition_status', ''),
                request.form.get('chanter', ''),
                request.form.get('storage_zone', ''),
                request.form.get('notes', ''),
                request.form.get('supplier_name', ''),
                request.form.get('bc_number', ''),
                request.form.get('bl_number', ''),
                request.form.get('n_facture', ''),
                request.form.get('type_achat', ''),
                request.form.get('expiration_date') if request.form.get('expiration_date') else None,
                product_id
            ))
            
            conn.commit()
            conn.close()
            
            flash(_('product_updated_successfully'), 'success')
            return redirect(url_for('products'))
        
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    # Get product details
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if not product:
        flash(_('product_not_found'), 'error')
        return redirect(url_for('products'))
    
    conn.close()
    return render_template('edit_product.html', product=product, _=_)

# Delete product route
@app.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    try:
        conn = sqlite3.connect(stock_system.db_path)
        cursor = conn.cursor()
        
        # Delete related stock movements first
        cursor.execute('DELETE FROM stock_movements WHERE product_id = ?', (product_id,))
        
        # Delete product
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        
        conn.commit()
        conn.close()
        
        flash(_('product_deleted_successfully'), 'success')
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('products'))

# Stock movements routes
@app.route('/movements')
@login_required
def movements():
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()
    
    # Get filter parameters
    search = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    
    # Build query
    query = '''
        SELECT sm.id, sm.movement_type, sm.quantity, sm.notes, sm.created_at,
               p.code, p.name, u.username, sm.supplier_name, sm.type_achat
        FROM stock_movements sm
        JOIN products p ON sm.product_id = p.id
        JOIN users u ON sm.user_id = u.id
        WHERE 1=1
    '''
    params = []
    
    if search:
        query += ' AND (p.code LIKE ? OR p.name LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if type_filter:
        query += ' AND sm.movement_type = ?'
        params.append(type_filter)
    
    query += ' ORDER BY sm.created_at DESC'
    
    cursor.execute(query, params)
    movements = cursor.fetchall()
    
    conn.close()
    
    return render_template('movements.html', 
                         movements=movements,
                         search=search,
                         type_filter=type_filter,
                         _=_)

@app.route('/movements/add', methods=['GET', 'POST'])
@login_required
def add_movement():
    if request.method == 'POST':
        try:
            conn = sqlite3.connect(stock_system.db_path)
            cursor = conn.cursor()
            
            product_id = request.form['product_id']
            movement_type = request.form['movement_type']
            quantity = int(request.form['quantity'])
            
            # Check current stock for exit movements
            if movement_type == 'exit':
                cursor.execute('SELECT quantity FROM products WHERE id = ?', (product_id,))
                current_stock = cursor.fetchone()[0]
                
                if current_stock < quantity:
                    flash(_('insufficient_stock'), 'error')
                    return redirect(request.url)
            
            # Insert movement
            cursor.execute('''
                INSERT INTO stock_movements (
                    product_id, movement_type, quantity, notes, user_id,
                    supplier_name, bc_number, bl_number, n_facture, type_achat
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product_id, movement_type, quantity,
                request.form.get('notes', ''),
                session['user_id'],
                request.form.get('supplier_name', ''),
                request.form.get('bc_number', ''),
                request.form.get('bl_number', ''),
                request.form.get('n_facture', ''),
                request.form.get('type_achat', '')
            ))
            
            # Update product quantity
            if movement_type == 'entry':
                cursor.execute('UPDATE products SET quantity = quantity + ? WHERE id = ?', 
                             (quantity, product_id))
            else:  # exit
                cursor.execute('UPDATE products SET quantity = quantity - ? WHERE id = ?', 
                             (quantity, product_id))
            
            conn.commit()
            conn.close()
            
            flash(_('movement_added_successfully'), 'success')
            return redirect(url_for('movements'))
        
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    # Get products for dropdown
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT id, code, name FROM products ORDER BY name')
    products = cursor.fetchall()
    conn.close()
    
    return render_template('add_movement.html', products=products, _=_)

# User management routes (admin only)
@app.route('/users')
@admin_required
def users():
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    
    conn.close()
    
    return render_template('users.html', users=users, _=_)

@app.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        try:
            # Principal admin restriction
            if request.form['role'] == 'principal_admin' and session.get('role') != 'principal_admin':
                flash(_('cannot_create_principal_admin'), 'error')
                return render_template('add_user.html', _=_)
            
            conn = sqlite3.connect(stock_system.db_path)
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute('SELECT COUNT(*) FROM users WHERE username = ? OR email = ?', 
                         (request.form['username'], request.form['email']))
            if cursor.fetchone()[0] > 0:
                flash(_('username_or_email_already_exists'), 'error')
                return render_template('add_user.html', _=_)
            
            # Insert user
            password_hash = generate_password_hash(request.form['password'])
            cursor.execute('''
                INSERT INTO users (username, password_hash, email, role, active)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                request.form['username'],
                password_hash,
                request.form['email'],
                request.form['role'],
                1 if request.form.get('active') == 'on' else 0
            ))
            
            conn.commit()
            conn.close()
            
            flash(_('user_added_successfully'), 'success')
            return redirect(url_for('users'))
        
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('add_user.html', _=_)

# Rest of the routes remain exactly the same as in the original file...
# (I'll continue with the remaining routes but they are unchanged from the original)

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        try:
            # Get current user data
            cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
            current_user = cursor.fetchone()
            
            if not current_user:
                flash(_('user_not_found'), 'error')
                return redirect(url_for('users'))
            
            new_role = request.form['role']
            new_active = 1 if request.form.get('active') == 'on' else 0
            
            # Principal admin restrictions
            if current_user[0] == 'principal_admin' and session.get('role') != 'principal_admin':
                flash(_('cannot_demote_principal_admin'), 'error')
                return redirect(request.url)
            
            if new_role == 'principal_admin' and session.get('role') != 'principal_admin':
                flash(_('cannot_promote_to_principal_admin'), 'error')
                return redirect(request.url)
            
            if current_user[0] == 'principal_admin' and new_active == 0:
                flash(_('cannot_deactivate_principal_admin'), 'error')
                return redirect(request.url)
            
            # Check if username or email already exists (excluding current user)
            cursor.execute('SELECT COUNT(*) FROM users WHERE (username = ? OR email = ?) AND id != ?', 
                         (request.form['username'], request.form['email'], user_id))
            if cursor.fetchone()[0] > 0:
                flash(_('username_or_email_already_exists'), 'error')
                cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                conn.close()
                return render_template('edit_user.html', user=user, _=_)
            
            # Update user
            if request.form.get('password'):
                password_hash = generate_password_hash(request.form['password'])
                cursor.execute('''
                    UPDATE users SET username=?, email=?, password_hash=?, role=?, active=?
                    WHERE id=?
                ''', (
                    request.form['username'],
                    request.form['email'],
                    password_hash,
                    new_role,
                    new_active,
                    user_id
                ))
            else:
                cursor.execute('''
                    UPDATE users SET username=?, email=?, role=?, active=?
                    WHERE id=?
                ''', (
                    request.form['username'],
                    request.form['email'],
                    new_role,
                    new_active,
                    user_id
                ))
            
            conn.commit()
            conn.close()
            
            flash(_('user_updated_successfully'), 'success')
            return redirect(url_for('users'))
        
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    # Get user details
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        flash(_('user_not_found'), 'error')
        return redirect(url_for('users'))
    
    conn.close()
    return render_template('edit_user.html', user=user, _=_)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    try:
        # Prevent deleting own account
        if user_id == session['user_id']:
            flash(_('cannot_delete_own_account'), 'error')
            return redirect(url_for('users'))
        
        conn = sqlite3.connect(stock_system.db_path)
        cursor = conn.cursor()
        
        # Check if user is principal admin
        cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if user and user[0] == 'principal_admin':
            flash(_('cannot_delete_principal_admin'), 'error')
            return redirect(url_for('users'))
        
        # Delete user
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        flash('User deleted successfully.', 'success')
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('users'))

# Email management routes
@app.route('/email_management')
@admin_required
def email_management():
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM notification_recipients ORDER BY created_at DESC')
    recipients = cursor.fetchall()
    
    conn.close()
    
    return render_template('email_management.html', recipients=recipients, _=_)

@app.route('/email_management/add_recipient', methods=['POST'])
@admin_required
def add_recipient():
    try:
        conn = sqlite3.connect(stock_system.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO notification_recipients (
                name, email, notify_achat_par_bc, notify_achat_par_caisse,
                notify_achat_a_regulariser, notify_transfert
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            request.form['name'],
            request.form['email'],
            1 if request.form.get('notify_achat_par_bc') == 'on' else 0,
            1 if request.form.get('notify_achat_par_caisse') == 'on' else 0,
            1 if request.form.get('notify_achat_a_regulariser') == 'on' else 0,
            1 if request.form.get('notify_transfert') == 'on' else 0
        ))
        
        conn.commit()
        conn.close()
        
        flash(_('recipient_added_successfully'), 'success')
    
    except Exception as e:
        flash(_('error_adding_recipient') + f': {str(e)}', 'error')
    
    return redirect(url_for('email_management'))

@app.route('/email_management/test_email', methods=['POST'])
@admin_required
def test_email():
    test_email_address = request.form.get('test_email')
    
    if not test_email_address:
        flash(_('please_provide_test_email'), 'error')
        return redirect(url_for('email_management'))
    
    try:
        success = stock_system.send_email(
            test_email_address,
            _('test_email_subject'),
            _('test_email_body')
        )
        
        if success:
            flash(_('test_email_sent_successfully'), 'success')
        else:
            flash(_('error_sending_test_email'), 'error')
    
    except Exception as e:
        flash(_('error_sending_test_email') + f': {str(e)}', 'error')
    
    return redirect(url_for('email_management'))

# Logo management routes
@app.route('/logo_management')
@admin_required
def logo_management():
    # Check if logo exists
    logo_files = ['logo.png', 'logo.jpg', 'logo.jpeg']
    current_logo = None
    
    for logo_file in logo_files:
        logo_path = os.path.join(app.config['LOGO_FOLDER'], logo_file)
        if os.path.exists(logo_path):
            current_logo = logo_file
            break
    
    return render_template('logo_management.html', current_logo=current_logo, _=_)

@app.route('/logo_management/upload', methods=['POST'])
@admin_required
def upload_logo():
    try:
        if 'logo' not in request.files:
            flash(_('no_file_selected'), 'error')
            return redirect(url_for('logo_management'))
        
        file = request.files['logo']
        
        if file.filename == '':
            flash(_('no_file_selected'), 'error')
            return redirect(url_for('logo_management'))
        
        if file and allowed_logo_file(file.filename):
            # Remove existing logo files
            logo_files = ['logo.png', 'logo.jpg', 'logo.jpeg']
            for logo_file in logo_files:
                logo_path = os.path.join(app.config['LOGO_FOLDER'], logo_file)
                if os.path.exists(logo_path):
                    os.remove(logo_path)
            
            # Save new logo
            filename = 'logo.' + file.filename.rsplit('.', 1)[1].lower()
            file_path = os.path.join(app.config['LOGO_FOLDER'], filename)
            file.save(file_path)
            
            # Resize logo if needed
            try:
                with Image.open(file_path) as img:
                    # Resize to max 200x100 while maintaining aspect ratio
                    img.thumbnail((200, 100), Image.Resampling.LANCZOS)
                    img.save(file_path)
            except Exception as e:
                logger.warning(f"Could not resize logo: {e}")
            
            flash(_('logo_uploaded_successfully'), 'success')
        else:
            flash(_('invalid_file_type'), 'error')
    
    except Exception as e:
        flash(_('error_uploading_logo') + f': {str(e)}', 'error')
    
    return redirect(url_for('logo_management'))

@app.route('/static/logos/<filename>')
def logo_file(filename):
    return send_from_directory(app.config['LOGO_FOLDER'], filename)

# Reports routes
@app.route('/reports')
@login_required
def reports():
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()

    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM products')
    total_products = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM products WHERE quantity <= 5 AND quantity > 0')
    low_stock_count = cursor.fetchone()[0]  # لاحظ: تم تغيير الاسم ليطابق القالب

    cursor.execute('SELECT COUNT(*) FROM stock_movements')
    total_movements = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM stock_movements WHERE movement_type = 'entry'")
    total_entries = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM stock_movements WHERE movement_type = 'exit'")
    total_exits = cursor.fetchone()[0]

    conn.close()

    # تمرير الإحصائيات ككائن stats
    stats = {
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'total_movements': total_movements,
        'total_entries': total_entries,
        'total_exits': total_exits
    }

    lang = session.get('language', 'fr')
    logo_path = os.path.join(app.config['LOGO_FOLDER'], 'logo.png')
    logo_exists = os.path.exists(logo_path)

    return render_template('reports.html', 
                         stats=stats,
                         lang=lang,
                         logo_exists=logo_exists,
                         _=_)

@app.route('/reports/products')
@login_required
def product_reports():
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()
    
    # Get filter parameters
    category_filter = request.args.get('category', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Build query
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    if category_filter:
        query += ' AND category = ?'
        params.append(category_filter)
    if start_date:
        query += ' AND date(created_at) >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date(created_at) <= ?'
        params.append(end_date)
    query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    
    # Get categories for filter
    cursor.execute('SELECT DISTINCT category FROM products WHERE category != "" ORDER BY category')
    categories = [cat[0] for cat in cursor.fetchall()]
    
    conn.close()
    
    # --- ✅ Calculate expiration status for each product ---
    today = date.today()
    products_with_status = []
    
    for p in products:
        # افترض أن الحقول: code=1, name=2, ..., expiration_date=16, created_at=17
        exp_date_str = p[16]  # الحقل رقم 16 (ابدأ من 0)
        status = 'no_expiry'
        
        if exp_date_str:
            try:
                exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                days_diff = (exp_date - today).days
                
                if days_diff < 0:
                    status = 'expired'
                elif days_diff <= 30:
                    status = 'expiring_soon'
                else:
                    status = 'valid'
            except (ValueError, TypeError):
                status = 'no_expiry'
        else:
            status = 'no_expiry'
        
        # أضف الحالة كحقل إضافي (سيكون الفهرس 18)
        products_with_status.append(p + (status,))
    
    return render_template('product_reports.html', 
                         products=products_with_status,
                         categories=categories,
                         category_filter=category_filter,
                         start_date=start_date,
                         end_date=end_date,
                         _=_)
                         
@app.route('/reports/movements')
@login_required
def movement_reports():
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()
    # الحصول على فلاتر البحث
    type_filter = request.args.get('type', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # بناء الاستعلام الأساسي
    query = '''
        SELECT sm.id, sm.movement_type, sm.quantity, sm.notes, sm.created_at,
               p.code, p.name, u.username, sm.supplier_name, sm.type_achat
        FROM stock_movements sm
        JOIN products p ON sm.product_id = p.id
        JOIN users u ON sm.user_id = u.id
        WHERE 1=1
    '''
    params = []
    if type_filter:
        query += ' AND sm.movement_type = ?'
        params.append(type_filter)
    if start_date:
        query += ' AND date(sm.created_at) >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date(sm.created_at) <= ?'
        params.append(end_date)
    query += ' ORDER BY sm.created_at DESC'

    cursor.execute(query, params)
    movements = cursor.fetchall()

    # === 🔍 حساب الإحصائيات (الملخص) ===
    # إجمالي الحركات
    count_query = 'SELECT COUNT(*) FROM stock_movements WHERE 1=1'
    count_params = []
    if type_filter:
        count_query += ' AND movement_type = ?'
        count_params.append(type_filter)
    if start_date:
        count_query += ' AND date(created_at) >= ?'
        count_params.append(start_date)
    if end_date:
        count_query += ' AND date(created_at) <= ?'
        count_params.append(end_date)
    cursor.execute(count_query, count_params)
    total_movements = cursor.fetchone()[0]

    # الحركات الداخلة (Entry)
    entry_query = count_query.replace('COUNT(*)', 'COUNT(*)') + ' AND movement_type = "entry"'
    entry_params = count_params.copy()
    cursor.execute(entry_query, entry_params)
    total_entries = cursor.fetchone()[0]

    # الحركات الخارجة (Exit)
    exit_query = count_query.replace('COUNT(*)', 'COUNT(*)') + ' AND movement_type = "exit"'
    exit_params = count_params.copy()
    cursor.execute(exit_query, exit_params)
    total_exits = cursor.fetchone()[0]

    # إنشاء كائن الملخص
    summary = {
        'total_movements': total_movements,
        'total_entries': total_entries,
        'total_exits': total_exits
    }

    conn.close()

    # تمرير البيانات + الملخص إلى القالب
    return render_template('movement_reports.html', 
                         movements=movements,
                         summary=summary,
                         type_filter=type_filter,
                         start_date=start_date,
                         end_date=end_date,
                         _=_)

# Export routes
@app.route('/export/products')
@login_required
def export_products():
    try:
        conn = sqlite3.connect(stock_system.db_path)
        df = pd.read_sql_query('SELECT * FROM products', conn)
        conn.close()

        # --- ✅ تغيير أسماء الأعمدة إلى الفرنسية ---
        french_headers = {
            'id': 'ID',
            'code': 'Code Produit',
            'name': 'Nom du Produit',
            'category': 'Catégorie',
            'unit': 'Unité',
            'quantity': 'Quantité',
            'brand': 'Marque',
            'condition_status': 'État',
            'chanter': 'Chantier',
            'storage_zone': 'Zone de Stockage',
            'notes': 'Notes',
            'supplier_name': 'Fournisseur',
            'bc_number': 'N° Bon de Commande',
            'bl_number': 'N° Bon de Livraison',
            'n_facture': 'N° Facture',
            'type_achat': 'Type d\'Achat',
            'expiration_date': 'Date d\'Expiration',
            'created_at': 'Créé le',
            'updated_at': 'Mis à jour le'
        }
        
        # إعادة تسمية الأعمدة
        df = df.rename(columns=french_headers)
        
        # --- ترتيب الأعمدة حسب الرغبة (اختياري) ---
        desired_order = [
            'ID', 'Code Produit', 'Nom du Produit', 'Catégorie', 'Unité', 'Quantité',
            'Marque', 'État', 'Chantier', 'Zone de Stockage','Notes', 'Fournisseur',
            'N° Bon de Commande', 'N° Bon de Livraison', 'N° Facture',
            'Type d\'Achat', 'Date d\'Expiration', 'Créé le', 'Mis à jour le'
        ]
        
        # تأكد من أن جميع الأعمدة المطلوبة موجودة
        df = df[desired_order]

        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)
        
        output.seek(0)
        
        # Return file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    
    except Exception as e:
        flash(f'Error exporting products: {str(e)}', 'error')
        return redirect(url_for('product_reports'))
        
@app.route('/export/movements')
@login_required
def export_movements():
    try:
        conn = sqlite3.connect(stock_system.db_path)
        
        # الحصول على الفلاتر من الطلب
        type_filter = request.args.get('type', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        product_id = request.args.get('product_id', '')

        # بناء الاستعلام
        query = '''
            SELECT 
                sm.id, 
                p.code as product_code, 
                p.name as product_name, 
                sm.movement_type, 
                sm.quantity, 
                sm.notes, 
                sm.created_at, 
                u.username, 
                sm.supplier_name, 
                sm.type_achat
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.id
            JOIN users u ON sm.user_id = u.id
            WHERE 1=1
        '''
        params = []

        if type_filter:
            query += ' AND sm.movement_type = ?'
            params.append(type_filter)

        if start_date:
            query += ' AND date(sm.created_at) >= ?'
            params.append(start_date)

        if end_date:
            query += ' AND date(sm.created_at) <= ?'
            params.append(end_date)

        if product_id:
            query += ' AND sm.product_id = ?'
            params.append(product_id)

        query += ' ORDER BY sm.created_at DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        # --- ✅ تعيين أسماء الأعمدة باللغة الفرنسية ---
        french_headers = {
            'id': 'ID',
            'product_code': 'Code Produit',
            'product_name': 'Nom du Produit',
            'movement_type': 'Type de Mouvement',
            'quantity': 'Quantité',
            'notes': 'Notes',
            'created_at': 'Date',
            'username': 'Utilisateur',
            'supplier_name': 'Nom du Fournisseur',
            'type_achat': 'Type d\'Achat'
        }
        
        df = df.rename(columns=french_headers)

        # --- ✅ ترتيب الأعمدة ---
        desired_order = [
            'ID', 'Code Produit', 'Nom du Produit', 'Type de Mouvement', 'Quantité',
            'Type d\'Achat', 'Nom du Fournisseur', 'Date', 'Utilisateur', 'Notes'
        ]
        df = df[desired_order]

        # --- إنشاء ملف إكسل ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Mouvements', index=False)
        output.seek(0)

        # --- إرسال الملف ---
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'mouvements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )

    except Exception as e:
        flash(f'Erreur lors de l\'exportation des mouvements : {str(e)}', 'error')
        return redirect(url_for('movement_reports'))


# Password reset routes
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        
        conn = sqlite3.connect(stock_system.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username FROM users WHERE email = ? AND active = 1', (email,))
        user = cursor.fetchone()
        
        if user:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=1)
            
            cursor.execute('''
                UPDATE users SET reset_token = ?, reset_token_expires = ?
                WHERE id = ?
            ''', (reset_token, expires_at, user[0]))
            
            conn.commit()
            
            # Send reset email
            lang = session.get('language', 'fr')
            success = stock_system.send_password_reset_email(email, reset_token, lang)
            
            if success:
                flash(_('password_reset_email_sent'), 'success')
            else:
                flash(_('error_sending_email'), 'error')
        else:
            # Don't reveal if email exists or not
            flash(_('password_reset_email_sent'), 'success')
        
        conn.close()
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html', _=_)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = sqlite3.connect(stock_system.db_path)
    cursor = conn.cursor()
    
    # Check if token is valid and not expired
    cursor.execute('''
        SELECT id, username FROM users 
        WHERE reset_token = ? AND reset_token_expires > ?
    ''', (token, datetime.now()))
    
    user = cursor.fetchone()
    
    if not user:
        flash(_('invalid_or_expired_token'), 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash(_('passwords_do_not_match'), 'error')
            return render_template('reset_password.html', token=token, _=_)
        
        if len(password) < 6:
            flash(_('password_too_short'), 'error')
            return render_template('reset_password.html', token=token, _=_)
        
        # Update password and clear reset token
        password_hash = generate_password_hash(password)
        cursor.execute('''
            UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expires = NULL
            WHERE id = ?
        ''', (password_hash, user[0]))
        
        conn.commit()
        conn.close()
        
        flash(_('password_reset_successful'), 'success')
        return redirect(url_for('login'))
    
    conn.close()
    return render_template('reset_password.html', token=token, _=_)

# Make translation function available in templates
@app.context_processor
def inject_translation():
    return dict(_=_)

@app.template_filter('todatetime')
def to_datetime(date_string):
    """
    تحويل سلسلة نصية إلى كائن datetime (يدعم DATE وDATETIME).
    """
    if not date_string:
        return None
    formats = [
        '%Y-%m-%d %H:%M:%S',  # 2024-10-01 14:25:30
        '%Y-%m-%d %H:%M',     # 2024-10-01 14:25
        '%Y-%m-%d',           # 2024-10-01
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except (ValueError, TypeError):
            continue
    return None
 

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
