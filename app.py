from flask import Flask, render_template, request, jsonify, send_from_directory
from chatbot import PropertyGraphChatbot
import config
import os

app = Flask(__name__, static_folder='.', static_url_path='')

# Initialize the chatbot
print("Initializing Sierra Madre Property Graph Chatbot...")
chatbot = PropertyGraphChatbot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    user_query = data.get('query', '')
    if not user_query:
        return jsonify({'response': 'Please enter a query.'})
    
    try:
        response = chatbot.query(user_query)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'response': f"Error: {str(e)}"})

@app.route('/data/<path:filename>')
def serve_data(filename):
    return send_from_directory('data', filename)

if __name__ == '__main__':
    print("\nChatbot interface running at http://localhost:5001")
    import webbrowser
    from threading import Timer
    Timer(1.5, lambda: webbrowser.open("http://localhost:5001")).start()
    app.run(host='0.0.0.0', port=5001, debug=False)
