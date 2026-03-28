"""
app.py - Flask web application for word etymology and cross-language root finding.

Routes:
    GET  /           – serves the main HTML page
    POST /api/analyze – accepts JSON {"word": "example"}, returns etymology + cross-language data
"""

from flask import Flask, jsonify, render_template, request

from etymology import get_word_info
from cross_language import find_cross_language_roots

app = Flask(__name__)


@app.route("/")
def index():
    """Serve the main single-page application."""
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Analyze a word's etymology and find cross-language root connections.

    Expects JSON body: {"word": "<word to analyze>"}

    Returns JSON:
        On success:
            {
                "word": str,
                "etymology_count": int,
                "etymology_texts": [str, ...],
                "roots": [{"root": str, "language": str, "meaning": str}, ...],
                "cross_language": [
                    {
                        "source_root": str,
                        "source_lang": str,
                        "source_meaning": str,
                        "cognates": [{"language": str, "word": str, "relationship": str}, ...]
                    },
                    ...
                ],
                "error": ""
            }
        On error:
            {"error": "<message>", "word": str}
    """
    data = request.get_json(silent=True)
    if not data or "word" not in data:
        return jsonify({"error": "Request body must be JSON with a 'word' key.", "word": ""}), 400

    word = str(data["word"]).strip()
    if not word:
        return jsonify({"error": "The 'word' field must not be empty.", "word": ""}), 400

    if len(word) > 100:
        return jsonify({"error": "Word is too long (max 100 characters).", "word": word}), 400

    word_info = get_word_info(word)

    if not word_info["found"]:
        return jsonify({
            "error": word_info["error"] or f"'{word}' was not found in Wiktionary.",
            "word": word,
        }), 404

    if not word_info["roots"] and not word_info["etymology_texts"]:
        return jsonify({
            "error": word_info["error"] or f"No etymology data available for '{word}'.",
            "word": word,
        }), 404

    cross_lang = find_cross_language_roots(word_info["roots"])

    return jsonify({
        "word": word_info["word"],
        "etymology_count": word_info["etymology_count"],
        "etymology_texts": word_info["etymology_texts"],
        "roots": word_info["roots"],
        "cross_language": cross_lang,
        "error": word_info["error"],
    })


@app.after_request
def add_cors_headers(response):
    """Add CORS headers to every response."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors with a JSON response."""
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    """Handle 405 errors with a JSON response."""
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(500)
def internal_error(e):
    """Handle unexpected server errors."""
    return jsonify({"error": "An internal server error occurred."}), 500


if __name__ == "__main__":
    import os

    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode, host="0.0.0.0", port=5000)
