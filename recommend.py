from flask import Flask, send_file, request, jsonify
import mysql.connector as sql
import pandas as pd
import os
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Create the Flask app (API)
app = Flask(__name__)

# Connect to the database
conn = sql.connect(host="localhost",
                   database="finlove", 
                   user="root",
                   password="1234")

# Path to the folder where images are stored
IMAGE_FOLDER = os.path.join(os.getcwd(), 'assets', 'user')

@app.route('/api/recommend/<int:id>', methods=['GET'])
def recommend(id):
    # Fetch data from the userpreferences table
    sql_query = "SELECT * FROM userpreferences"
    x = pd.read_sql(sql_query, conn)

    # Pivot data so that each UserID is a row and PreferenceID is a column
    x = x.pivot_table(index='UserID', columns='PreferenceID', aggfunc='size', fill_value=0)

    # Separate the data for the logged-in user and other users
    x_login_user = x.loc[[id]]  # Data for the logged-in user
    x_other_users = x.drop([id])  # Data for other users

    # Check for matching preferences of at least one item
    recommended_user_ids = []
    for other_user_id, other_user_data in x_other_users.iterrows():
        # Calculate matching preferences between the logged-in user and other users
        common_preferences = (x_login_user.values[0] == other_user_data.values).sum()

        # If there is at least one matching preference, recommend that user
        if common_preferences >= 1:
            recommended_user_ids.append(other_user_id)

    # If no matching users are found, return an empty result
    if len(recommended_user_ids) == 0:
        return jsonify({"message": "No similar users found"}), 200

    # Convert recommended user IDs to a string for SQL Query
    recommended_user_ids_str = ', '.join(map(str, recommended_user_ids))

    if not conn.is_connected():
        conn.reconnect()

    # Fetch recommended users and exclude those already matched or blocked
    sql_query = f'''
    SELECT 
        u.UserID, 
        u.nickname, 
        u.imageFile,
        u.verify
    FROM user u
    LEFT JOIN matches m ON (m.user1ID = u.UserID AND m.user2ID = {id}) OR (m.user2ID = u.UserID AND m.user1ID = {id})
    LEFT JOIN blocked_chats b ON (b.user1ID = {id} AND b.user2ID = u.UserID) OR (b.user2ID = {id} AND b.user1ID = u.UserID)
    WHERE u.UserID IN ({recommended_user_ids_str})
      AND m.matchID IS NULL -- Exclude already matched users
      AND (b.isBlocked IS NULL OR b.isBlocked = 0) -- Exclude blocked users
    '''

    recommended_users = pd.read_sql(sql_query, conn)

    # Update the imageFile path to point to the API for loading images
    for index, user in recommended_users.iterrows():
        if user['imageFile']:
            recommended_users.at[index, 'imageFile'] = f"http://{request.host}/api/user/{user['imageFile']}"

    # Return recommended users as JSON with verify field
    return jsonify(recommended_users[['UserID', 'nickname', 'imageFile', 'verify']].to_dict(orient='records')), 200

@app.route('/api/user/<filename>', methods=['GET'])
def get_user_image(filename):
    # Full path to the image file
    image_path = os.path.join(IMAGE_FOLDER, filename)

    # Check if the file exists
    if os.path.exists(image_path):
        # Return the image file to the client
        return send_file(image_path, mimetype='image/jpeg')
    else:
        # If the file is not found, return 404
        return jsonify({"error": "File not found"}), 404

# Create Web server
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6000)
