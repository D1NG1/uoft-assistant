from flask import Flask, request, jsonify, send_from_directory

from search_engine import answer_question

app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.post("/ask")
def ask():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    result = answer_question(question, top_k=3)
    return jsonify(result)


if __name__ == "__main__":
    # 調試用啓動方式
    app.run(host="127.0.0.1", port=5000, debug=True)
