from app import create_app
from app.models import User, Project
from app.extensions import db
from flask_login import login_user
from flask import request

app = create_app()

@app.route('/test_vote')
def test_vote():
    # Fai login dell'utente di test
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        if user:
            return f'''
            <h1>Test Votazione</h1>
            <p>Utente: {user.username}</p>
            <button onclick="testVote()">Vota Progetto ID 3</button>
            
            <script>
            function testVote() {{
                fetch('/vote_project/3', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }}
                }})
                .then(response => {{
                    console.log('Status:', response.status);
                    return response.text();
                }})
                .then(data => {{
                    console.log('Response:', data);
                    alert('Response: ' + data);
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    alert('Error: ' + error.message);
                }});
            }}
            </script>
            '''
        return 'User not found'

if __name__ == '__main__':
    app.run(debug=True, port=5001)
