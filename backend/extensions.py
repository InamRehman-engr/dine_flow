from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO

db = SQLAlchemy()
migrate = Migrate()
# message_queue wired in create_app when REDIS_URL is set
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")
