from flask import Blueprint, jsonify
import time

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Flask Agent is running"
    })

@health_bp.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "healthy",
        "service": "Flask AI Assistant",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "available_endpoints": [
            "/chat (POST)",
            "/clear_history (POST)",
            "/status (GET)",
            "/health (GET)"
        ]
    })
