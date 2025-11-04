from flask import Blueprint, request, jsonify
from utils.common import clear_session_history

history_bp = Blueprint('history', __name__)

@history_bp.route('/clear_history', methods=['POST'])
def clear_history():
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        if clear_session_history(session_id):
            return jsonify({
                "success": True,
                "message": f"History cleared for session {session_id or 'default'}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to clear history"
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
