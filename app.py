from flask import Flask, jsonify
from flask_cors import CORS
from utils.db import db, users_collection
import os

# -------------------------
#   CREATE FLASK APP
# -------------------------
app = Flask(__name__)
CORS(app, supports_credentials=True)
   # Enable CORS for all routes

# -------------------------
#   IMPORT AND REGISTER ROUTES
# -------------------------
from routes.auth_routes import auth_bp
app.register_blueprint(auth_bp, url_prefix="/api/auth")

from routes.blog_routes import blog_bp
app.register_blueprint(blog_bp, url_prefix="/api")

# -------------------------
#   TEST ROUTES
# -------------------------
@app.route("/test")
def test():
    return jsonify({"message": "Backend connected successfully!"})

@app.route("/test-db")
def test_db():
    try:
        collections = db.list_collection_names()
        return jsonify({
            "status": "success",
            "collections": collections
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# -------------------------
#   START SERVER
# -------------------------


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

