import os

from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()


def init_cors(app):
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
    CORS(
        app,
        resources={r"/*": {"origins": origins}},
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
