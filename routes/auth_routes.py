from flask import Blueprint, request, jsonify
from utils.db import users_collection
from werkzeug.security import generate_password_hash, check_password_hash


auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()

    name = data.get("name")
    regNo = data.get("regNo")
    email = data.get("email")
    password = data.get("password")
    year = data.get("year")      # "1-2", "3-4", "staff"
    linkedin = data.get("linkedin")

    # --------------------------
    # BASIC VALIDATIONS
    # --------------------------
    if not name or not year or not password:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    # --------------------------
    # YEAR / ROLE LOGIC
    # --------------------------
    if year == "1-2":
        role = "junior"
        if not regNo:
            return jsonify({"status": "error", "message": "Registration number required"}), 400
        email = None
        linkedin = None

    elif year == "3-4":
        role = "senior"
        if not regNo:
            return jsonify({"status": "error", "message": "Registration number required"}), 400
        if not linkedin:
            return jsonify({"status": "error", "message": "LinkedIn profile required for 3rd/4th year"}), 400
        email = None

    elif year == "staff":
        role = "staff"
        if not email:
            return jsonify({"status": "error", "message": "Email required for staff"}), 400
        regNo = None
        linkedin = None

    else:
        return jsonify({"status": "error", "message": "Invalid year value"}), 400

    # --------------------------
    # DUPLICATE CHECK
    # --------------------------
    # Students use regNo, staff use email

    if year == "staff":
        if users_collection.find_one({"email": email}):
            return jsonify({"status": "error", "message": "Email already registered"}), 400
    else:
        if users_collection.find_one({"regNo": regNo}):
            return jsonify({"status": "error", "message": "Registration number already registered"}), 400

    # --------------------------
    # SAVE USER
    # --------------------------
    hashed_pw = generate_password_hash(password)

    user_doc = {
        "name": name,
        "regNo": regNo,
        "email": email,
        "password": hashed_pw,
        "year": year,
        "role": role,
        "linkedin": linkedin
    }

    users_collection.insert_one(user_doc)

    return jsonify({
        "status": "success",
        "message": "User registered successfully",
        "role": role
    }), 201

# -------------------------
# LOGIN ROUTE
# -------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    regNo = data.get("regNo")
    email = data.get("email")
    password = data.get("password")
    year = data.get("year")  # only for students

    if not password:
        return jsonify({"status": "error", "message": "Password required"}), 400

    user = None

    if email:
        user = users_collection.find_one({"email": email})
    elif regNo:
        user = users_collection.find_one({"regNo": regNo})
    else:
        return jsonify({"status": "error", "message": "Invalid login data"}), 400

    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    if not check_password_hash(user["password"], password):
        return jsonify({"status": "error", "message": "Incorrect password"}), 401

    return jsonify({
        "status": "success",
        "message": "Login successful",
        "role": user["role"],
        "name": user["name"]
    }), 200