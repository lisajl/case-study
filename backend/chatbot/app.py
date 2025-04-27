from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS to handle cross-origin requests
from chain import get_answer  

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route("/api/get_answer", methods=["POST", "OPTIONS"])
def get_answer_route():
    if request.method == "OPTIONS":
        return "", 200  # Respond to preflight request with 200 OK
    
    try:
        data = request.get_json()  # Get data from frontend
        user_query = data.get("query")  # Extract query from JSON

        if not user_query:
            return jsonify({"error": "Query is required"}), 400  # Handle missing query

        print(f"Received query: {user_query}")  # Log the received query

        # Get the answer from chain.py using the conversation history
        answer = get_answer(user_query)

        if answer:
            return jsonify({"answer": answer})  # Send the answer back to frontend
        else:
            return jsonify({"error": "No answer generated."}), 500  # If no answer is found
    except Exception as e:
        print(f"Error: {str(e)}")  # Log any errors for debugging
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500  # Handle errors

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)  # Run the app on all available interfaces and port 5000
