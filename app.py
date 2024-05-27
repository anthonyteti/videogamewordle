from flask import Flask, render_template, request, jsonify
import requests
import random

app = Flask(__name__)

CLIENT_ID = 'mscoikc64qpjmrv8ban9q1bccvddh9'
CLIENT_SECRET = '861eai7r1loh9p0s7x9vsx9ifvuiyi'

def get_access_token(client_id, client_secret):
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, params=params)
    access_token = response.json()['access_token']
    return access_token

def get_game_details(access_token, limit=100):
    url = 'https://api.igdb.com/v4/games'
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {access_token}',
    }
    payload = f'''
    fields name, first_release_date, genres.name, involved_companies.company.name, age_ratings.rating, cover.url;
    limit {limit};
    where first_release_date != null & genres != null & involved_companies != null & age_ratings != null;
    '''
    response = requests.post(url, data=payload, headers=headers)
    games = response.json()
    
    # Parse the game details
    game_list = []
    for game in games:
        game_info = {
            'name': game['name'],
            'release_year': game['first_release_date'] // 31556926 + 1970,  # Convert epoch to year
            'genres': [genre['name'] for genre in game.get('genres', [])],
            'publisher': game['involved_companies'][0]['company']['name'] if game.get('involved_companies') else 'Unknown',
            'age_rating': game['age_ratings'][0]['rating'] if game.get('age_ratings') else 'Unknown',
            'cover_url': game['cover']['url'] if game.get('cover') else ''
        }
        game_list.append(game_info)
    
    return game_list

access_token = get_access_token(CLIENT_ID, CLIENT_SECRET)
game_details = get_game_details(access_token, limit=100)
chosen_game = random.choice(game_details)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/guess', methods=['POST'])
def guess():
    guess_name = request.form['guess']
    guess_count = int(request.form['guesses'])
    feedback = check_guess(guess_name, chosen_game, guess_count)
    return jsonify(feedback)

@app.route('/game_names')
def game_names():
    names = [game['name'] for game in game_details]
    return jsonify({'game_names': names})

@app.route('/correct_game_cover')
def correct_game_cover():
    return jsonify({'cover_url': chosen_game['cover_url'] if 'cover_url' in chosen_game else ''})

def check_guess(guess_name, chosen_game, guess_count):
    for game in game_details:
        if game['name'].lower() == guess_name.lower():
            guess = game
            break
    else:
        guess = {
            'name': guess_name,
            'release_year': 'Unknown',
            'genres': 'Unknown',
            'publisher': 'Unknown',
            'age_rating': 'Unknown'
        }

    year_diff = abs(guess['release_year'] - chosen_game['release_year'])
    age_diff = abs(int(guess['age_rating']) - int(chosen_game['age_rating']))

    feedback = {
        'name': guess['name'],
        'release_year': guess['release_year'],
        'genres': ', '.join(guess['genres']),
        'publisher': guess['publisher'],
        'age_rating': guess['age_rating'],
        'release_year_class': get_color_class(year_diff, 5),  # Check year difference
        'genres_class': 'correct' if any(genre in chosen_game['genres'] for genre in guess['genres']) else 'incorrect',
        'publisher_class': 'correct' if guess['publisher'].lower() == chosen_game['publisher'].lower() else 'incorrect',
        'age_rating_class': get_color_class(age_diff, 3),  # Check age rating difference
        'game_over': False,
        'correct_game': ''
    }

    if guess_name.lower() == chosen_game['name'].lower():
        feedback['game_over'] = True
        feedback['correct_game'] = chosen_game['name']

    if guess_count >= 10:
        feedback['game_over'] = True
        feedback['correct_game'] = chosen_game['name']

    return feedback

def get_color_class(diff, threshold):
    if diff == 0:
        return 'correct'  # Correct guess
    elif diff <= threshold:
        return 'close'  # Close guess
    else:
        return 'incorrect'  # Incorrect guess

if __name__ == '__main__':
    print(chosen_game['name'])
    app.run(debug=True)
