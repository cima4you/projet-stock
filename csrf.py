import secrets
from functools import wraps
from flask import session, request, abort, current_app

def init_csrf(app):
    app.jinja_env.globals['csrf_token'] = _get_token

    @app.before_request
    def csrf_check():
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            if request.path.startswith('/static'):
                return
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not token or token != session.get('_csrf_token'):
                abort(403)


def _get_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']
