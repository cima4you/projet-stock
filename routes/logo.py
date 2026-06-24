import os
import logging
from flask import render_template, request, redirect, url_for, session, flash, send_file
from PIL import Image
from utils import admin_required, allowed_logo_file, get_translation
from translations import TRANSLATIONS
from config import LOGO_FOLDER

logger = logging.getLogger(__name__)


def register_logo_routes(app):

    @app.route('/logo_management')
    @admin_required
    def logo_management():
        logo_path = os.path.join(LOGO_FOLDER, 'logo.png')
        return render_template('logo_management.html', logo_exists=os.path.exists(logo_path),
                             translations=TRANSLATIONS[session.get('lang', 'fr')],
                             lang=session.get('lang', 'fr'))

    @app.route('/upload_logo', methods=['POST'])
    @admin_required
    def upload_logo():
        if 'logo_file' not in request.files:
            flash(get_translation('no_file_selected'), 'error')
            return redirect(url_for('logo_management'))
        file = request.files['logo_file']
        if file.filename == '':
            flash(get_translation('no_file_selected'), 'error')
            return redirect(url_for('logo_management'))
        if file and allowed_logo_file(file.filename):
            try:
                image = Image.open(file.stream)
                if image.mode in ('RGBA', 'LA', 'P'):
                    bg = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    mask = image.split()[-1] if image.mode == 'RGBA' else None
                    bg.paste(image, mask=mask)
                    image = bg
                image.thumbnail((500, 500), Image.Resampling.LANCZOS)
                image.save(os.path.join(LOGO_FOLDER, 'logo.png'), 'PNG', optimize=True)
                flash(get_translation('logo_uploaded_successfully'), 'success')
            except Exception as e:
                logger.error(f"Error uploading logo: {e}")
                flash(f"{get_translation('error_uploading_logo')}: {str(e)}", 'error')
        else:
            flash(get_translation('invalid_file_type'), 'error')
        return redirect(url_for('logo_management'))

    @app.route('/logo')
    def get_logo():
        logo_path = os.path.join(LOGO_FOLDER, 'logo.png')
        if os.path.exists(logo_path):
            return send_file(logo_path)
        return '', 404
