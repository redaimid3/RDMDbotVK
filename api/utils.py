from functools import wraps
from flask import request, jsonify
from database import get_player_info

def validate_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 403

        user_id = get_user_id_from_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 403

        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated_function

def get_user_id_from_token(token):
    # Implement token validation and return user_id
    pass