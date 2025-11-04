from flask import Flask
from flask_cors import CORS
from routes.sheet_routes import sheet_bp
from routes.chat_routes import chat_bp
from routes.health_routes import health_bp
from routes.history_routes import history_bp
from routes.chart_routes import chart_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(sheet_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(health_bp)
app.register_blueprint(history_bp)
app.register_blueprint(chart_bp)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
