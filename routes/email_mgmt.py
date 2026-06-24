import logging
from flask import render_template, request, redirect, url_for, session, flash
from db import get_db, execute
from utils import admin_required, get_translation
from notifications import send_email, check_expiring_products, send_expiring_products_notification
from translations import TRANSLATIONS
from config import SMTP_SERVER, EMAIL_ADDRESS, NOTIFICATION_EMAIL

logger = logging.getLogger(__name__)


def register_email_routes(app):

    @app.route('/email_management')
    @admin_required
    def email_management():
        email_status = "Configuré" if EMAIL_ADDRESS else "Non configuré"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, email, active, notify_achat_par_bc, notify_achat_par_caisse,
                       notify_achat_a_regulariser, notify_transfert, notify_product_deletion,
                       notify_product_expiration, notify_consumption
                FROM notification_recipients ORDER BY name
            ''')
            recipients = cursor.fetchall()
        return render_template('email_management.html', email_status=email_status,
                             smtp_server=SMTP_SERVER, email_address=EMAIL_ADDRESS,
                             recipients=recipients,
                             translations=TRANSLATIONS[session.get('lang', 'fr')],
                             lang=session.get('lang', 'fr'))

    @app.route('/test_email')
    @admin_required
    def test_email():
        try:
            test_email = NOTIFICATION_EMAIL or EMAIL_ADDRESS
            if not test_email:
                flash("Aucune adresse email configurée pour le test", 'error')
                return redirect(url_for('email_management'))
            from datetime import datetime
            subject = "Test de connexion email - Système de gestion de stock"
            body = f"Ceci est un email de test.\nHeure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            success = send_email(test_email, subject, body)
            flash("Email de test envoyé avec succès" if success else "Échec de l'envoi", 'success' if success else 'error')
        except Exception as e:
            logger.error(f"Error testing email: {e}")
            flash(f"Erreur: {str(e)}", 'error')
        return redirect(url_for('email_management'))

    @app.route('/add_recipient', methods=['POST'])
    @admin_required
    def add_recipient():
        try:
            name = request.form['name'].strip()
            email = request.form['email'].strip()
            notify_bc = 1 if 'notify_achat_par_bc' in request.form else 0
            notify_caisse = 1 if 'notify_achat_par_caisse' in request.form else 0
            notify_reg = 1 if 'notify_achat_a_regulariser' in request.form else 0
            notify_transfert = 1 if 'notify_transfert' in request.form else 0
            notify_consumption = 1 if 'notify_consumption' in request.form else 0
            notify_del = 1 if 'notify_product_deletion' in request.form else 0
            notify_exp = 1 if 'notify_product_expiration' in request.form else 0
            active = 1 if 'active' in request.form else 0
            execute('''
                INSERT INTO notification_recipients
                (name, email, active, notify_achat_par_bc, notify_achat_par_caisse,
                 notify_achat_a_regulariser, notify_transfert, notify_consumption,
                 notify_product_deletion, notify_product_expiration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, active, notify_bc, notify_caisse, notify_reg,
                  notify_transfert, notify_consumption, notify_del, notify_exp))
            flash(get_translation('recipient_added_successfully'), 'success')
        except Exception as e:
            logger.error(f"Error adding recipient: {e}")
            flash(f"Erreur: {str(e)}", 'error')
        return redirect(url_for('email_management'))

    @app.route('/edit_recipient/<int:recipient_id>', methods=['POST'])
    @admin_required
    def edit_recipient(recipient_id):
        try:
            name = request.form['name'].strip()
            email = request.form['email'].strip()
            notify_bc = 1 if 'notify_achat_par_bc' in request.form else 0
            notify_caisse = 1 if 'notify_achat_par_caisse' in request.form else 0
            notify_reg = 1 if 'notify_achat_a_regulariser' in request.form else 0
            notify_transfert = 1 if 'notify_transfert' in request.form else 0
            notify_consumption = 1 if 'notify_consumption' in request.form else 0
            notify_del = 1 if 'notify_product_deletion' in request.form else 0
            notify_exp = 1 if 'notify_product_expiration' in request.form else 0
            active = 1 if 'active' in request.form else 0
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE notification_recipients
                    SET name=?, email=?, active=?, notify_achat_par_bc=?, notify_achat_par_caisse=?,
                        notify_achat_a_regulariser=?, notify_transfert=?, notify_consumption=?,
                        notify_product_deletion=?, notify_product_expiration=?
                    WHERE id=?
                ''', (name, email, active, notify_bc, notify_caisse, notify_reg,
                      notify_transfert, notify_consumption, notify_del, notify_exp, recipient_id))
            flash("Destinataire mis à jour avec succès", 'success')
        except Exception as e:
            logger.error(f"Error updating recipient: {e}")
            flash(f"Erreur: {str(e)}", 'error')
        return redirect(url_for('email_management'))

    @app.route('/delete_recipient/<int:recipient_id>')
    @admin_required
    def delete_recipient(recipient_id):
        try:
            execute('DELETE FROM notification_recipients WHERE id = ?', (recipient_id,))
            flash("Destinataire supprimé avec succès", 'success')
        except Exception as e:
            logger.error(f"Error deleting recipient: {e}")
            flash(f"Erreur: {str(e)}", 'error')
        return redirect(url_for('email_management'))

    @app.route('/check_expiring_products_manual')
    @admin_required
    def check_expiring_products_manual():
        try:
            expiring = check_expiring_products(30)
            if expiring:
                send_expiring_products_notification(expiring, session.get('lang', 'fr'))
                flash(f"Vérification terminée. {len(expiring)} produits expirent bientôt.", 'info')
            else:
                flash("Aucun produit n'expire dans les 30 prochains jours.", 'info')
        except Exception as e:
            logger.error(f"Error: {e}")
            flash(f"Erreur: {str(e)}", 'error')
        return redirect(url_for('email_management'))
