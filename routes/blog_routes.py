from flask import Blueprint, request, jsonify
from bson import ObjectId
from utils.db import db
from datetime import datetime
from nlp.sentiment_analyzer import analyze_sentiment

blogs_collection = db.blogs  # MongoDB collection
blog_bp = Blueprint("blogs", __name__)

# -------------------------
# POST NEW BLOG (3rd/4th year only)
# -------------------------
@blog_bp.route("/blogs", methods=["POST"])
def post_blog():
    data = request.get_json()

    author_name = data.get("author_name")
    author_year = data.get("author_year")
    author_role = (data.get("author_role") or "").strip().lower()  # ✅ normalize
    linkedin = data.get("linkedin")
    title = data.get("title")
    company = data.get("company")
    content = data.get("content")

    # Check permission: senior, staff, coordinator
    if author_role not in ["senior", "staff", "coordinator"]:
        return jsonify({"status": "error", "message": "Only senior students, staff, or coordinators can post blogs"}), 403

    if not all([author_name, title, company, content]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    # Sentiment analysis
    sentiment_result = analyze_sentiment(content)

    # Block if strongly negative
    if sentiment_result["status"] == "warning":
        return jsonify(sentiment_result), 400

    # Blog document with sentiment scores
    blog_doc = {
        "title": title,
        "company": company,
        "content": content,
        "author_name": author_name,
        "author_year": author_year,
        "author_role": author_role,  # ✅ normalized value stored
        "linkedin": linkedin,
        "created_at": datetime.utcnow(),
        "likes": [],
        "dislikes": [],
        "sentiment": sentiment_result["scores"]
    }

    blogs_collection.insert_one(blog_doc)
    return jsonify({"status": "success", "message": "Blog posted successfully!"})

# -------------------------
# GET ALL BLOGS (Everyone)
# -------------------------
@blog_bp.route("/blogs", methods=["GET"])
def get_blogs():
    blogs = list(blogs_collection.find({}, {
        "_id": 1, "title": 1, "company": 1, "content": 1,
        "author_name": 1, "author_role": 1, "author_year": 1,
        "linkedin": 1, "likes": 1, "dislikes": 1, "created_at": 1
    }))
    # Convert ObjectId to string for JSON
    for blog in blogs:
        blog["_id"] = str(blog["_id"])
        blog["likes"] = len(blog.get("likes", []))      # ✅ convert to count
        blog["dislikes"] = len(blog.get("dislikes", []))

    return jsonify({"status": "success", "blogs": blogs})


# -------------------------
# GET SINGLE BLOG (by ID)
# -------------------------
# -------------------------
# GET SINGLE BLOG (by ID)
# -------------------------
@blog_bp.route("/blogs/<string:id>", methods=["GET"])
def get_blog(id):
    try:
        blog = blogs_collection.find_one({"_id": ObjectId(id)})
        if not blog:
            return jsonify({"status": "error", "message": "Blog not found"}), 404

        # Convert ObjectId to string for JSON
        blog["_id"] = str(blog["_id"])
        blog["likes"] = len(blog.get("likes", []))      # ✅ convert to count
        blog["dislikes"] = len(blog.get("dislikes", []))
        return jsonify({"status": "success", "blog": blog}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# EDIT BLOG (Author or Coordinator)
# -------------------------
@blog_bp.route("/blogs/<string:id>", methods=["PUT"])
def edit_blog(id):
    data = request.get_json()
    editor_name = data.get("editor_name")
    editor_role = data.get("editor_role")

    blog = blogs_collection.find_one({"_id": ObjectId(id)})
    if not blog:
        return jsonify({"status": "error", "message": "Blog not found"}), 404

    # Permission check
    if editor_role != "coordinator" and editor_name != blog["author_name"]:
        return jsonify({"status": "error", "message": "Permission denied"}), 403

    # Update fields (exclude likes/dislikes from editing)
    updated_fields = {}
    for field in ["title", "company", "content", "linkedin"]:
        if data.get(field):
            if field == "content":
                # Recalculate sentiment
                sentiment_result = analyze_sentiment(data.get(field))
                if sentiment_result["status"] == "warning":
                    return jsonify(sentiment_result), 400
                updated_fields[field] = data.get(field)
                updated_fields["sentiment"] = sentiment_result["scores"]
            else:
                updated_fields[field] = data.get(field)

    if updated_fields:
        blogs_collection.update_one({"_id": ObjectId(id)}, {"$set": updated_fields})
        return jsonify({"status": "success", "message": "Blog updated successfully!"})
    else:
        return jsonify({"status": "error", "message": "No fields to update"}), 400

# -------------------------
# DELETE BLOG (Author or Coordinator)
# -------------------------
@blog_bp.route("/blogs/<string:id>", methods=["DELETE"])
def delete_blog(id):
    data = request.get_json()
    editor_name = data.get("editor_name")
    editor_role = data.get("editor_role")

    blog = blogs_collection.find_one({"_id": ObjectId(id)})
    if not blog:
        return jsonify({"status": "error", "message": "Blog not found"}), 404

    if editor_role != "coordinator" and editor_name != blog["author_name"]:
        return jsonify({"status": "error", "message": "Permission denied"}), 403

    blogs_collection.delete_one({"_id": ObjectId(id)})
    return jsonify({"status": "success", "message": "Blog deleted successfully!"})
# -------------------------
# LIKE a blog
# -------------------------
@blog_bp.route("/blogs/<string:id>/like", methods=["POST"])
def like_blog(id):
    # Use silent=True so it doesn't throw if body is missing
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")  # e.g. regNo or email

    if not user_id:
        return jsonify({"status": "error", "message": "Missing user_id"}), 400

    blog = blogs_collection.find_one({"_id": ObjectId(id)})
    if not blog:
        return jsonify({"status": "error", "message": "Blog not found"}), 404

    # Remove from dislikes if present
    blogs_collection.update_one(
        {"_id": ObjectId(id)},
        {"$pull": {"dislikes": user_id}}
    )

    # Check if already liked
    if user_id in blog.get("likes", []):
        return jsonify({"status": "error", "message": "Already liked"}), 400

    # Add to likes
    blogs_collection.update_one(
        {"_id": ObjectId(id)},
        {"$addToSet": {"likes": user_id}}
    )

    updated = blogs_collection.find_one({"_id": ObjectId(id)})
    return jsonify({
    "status": "success",
    "message": "Blog liked!",
    "likes": len(updated.get("likes", [])),      # ✅ number
    "dislikes": len(updated.get("dislikes", [])) # ✅ number
})


# -------------------------
# DISLIKE a blog
# -------------------------
@blog_bp.route("/blogs/<string:id>/dislike", methods=["POST"])
def dislike_blog(id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing user_id"}), 400

    blog = blogs_collection.find_one({"_id": ObjectId(id)})
    if not blog:
        return jsonify({"status": "error", "message": "Blog not found"}), 404

    # Remove from likes if present
    blogs_collection.update_one(
        {"_id": ObjectId(id)},
        {"$pull": {"likes": user_id}}
    )

    # Check if already disliked
    if user_id in blog.get("dislikes", []):
        return jsonify({"status": "error", "message": "Already disliked"}), 400

    # Add to dislikes
    blogs_collection.update_one(
        {"_id": ObjectId(id)},
        {"$addToSet": {"dislikes": user_id}}
    )

    updated = blogs_collection.find_one({"_id": ObjectId(id)})
    return jsonify({
    "status": "success",
    "message": "Blog disliked!",
    "likes": len(updated.get("likes", [])),      # ✅ number
    "dislikes": len(updated.get("dislikes", [])) # ✅ number
})
# -------------------------
# ANALYTICS: Company-wise blog count
# -------------------------
@blog_bp.route("/analytics/company-count", methods=["GET"])
def company_count():
    pipeline = [
        {"$group": {"_id": "$company", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    result = list(blogs_collection.aggregate(pipeline))
    data = [{"company": r["_id"], "count": r["count"]} for r in result]
    return jsonify({"status": "success", "data": data})

# -------------------------
# ANALYTICS: Average sentiment per company
# -------------------------
@blog_bp.route("/analytics/company-sentiment", methods=["GET"])
def company_sentiment():
    pipeline = [
        {"$group": {"_id": "$company", "avg_compound": {"$avg": "$sentiment.compound"}}},
        {"$sort": {"avg_compound": -1}}
    ]
    result = list(blogs_collection.aggregate(pipeline))
    data = [{"company": r["_id"], "avg_compound": round(r["avg_compound"], 3)} for r in result]
    return jsonify({"status": "success", "data": data})

# -------------------------
# ANALYTICS: Likes vs Dislikes per blog
# -------------------------
@blog_bp.route("/analytics/engagement", methods=["GET"])
def engagement_metrics():
    blogs = list(blogs_collection.find({}, {"title": 1, "likes": 1, "dislikes": 1}))
    for blog in blogs:
        if "_id" in blog:
            blog["_id"] = str(blog["_id"])   # ✅ convert ObjectId
            blog["likes"] = len(blog.get("likes", []))      # ✅ convert to count
            blog["dislikes"] = len(blog.get("dislikes", []))

    return jsonify({"status": "success", "data": blogs})


# -------------------------
# ANALYTICS: Top 5 most liked blogs
# -------------------------
@blog_bp.route("/analytics/top-liked", methods=["GET"])
def top_liked():
    pipeline = [
        {
            "$project": {
                "title": 1,
                "company": 1,
                "likes_count": {"$size": {"$ifNull": ["$likes", []]}}
            }
        },
        {"$sort": {"likes_count": -1}},
        {"$limit": 5}
    ]
    result = list(blogs_collection.aggregate(pipeline))
    for blog in result:
        blog["_id"] = str(blog["_id"])
    return jsonify({"status": "success", "data": result})
# -------------------------
# ANALYTICS: Timeline (blogs per month)
# -------------------------
@blog_bp.route("/analytics/timeline", methods=["GET"])
def timeline():
    pipeline = [
        {"$group": {
            "_id": {"year": {"$year": "$created_at"}, "month": {"$month": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]
    result = list(blogs_collection.aggregate(pipeline))
    data = [
        {"year": r["_id"]["year"], "month": r["_id"]["month"], "count": r["count"]}
        for r in result
    ]
    return jsonify({"status": "success", "data": data})