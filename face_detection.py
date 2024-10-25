from flask import Flask, request, jsonify
import tensorflow as tf
import os
import cv2 as cv
import numpy as np
import mysql.connector
from werkzeug.utils import secure_filename
from threading import Timer

app = Flask(__name__)

# Load model and labels
MODEL_PATH = 'model.h5'
model = tf.keras.models.load_model(MODEL_PATH)

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",  # Your MySQL password
    database="finlove"
)

def update_verification(userID, is_verified):
    with db.cursor() as cursor:
        verify_status = 1 if is_verified else 0
        cursor.execute("UPDATE user SET verify = %s WHERE userID = %s", (verify_status, userID))
        db.commit()

@app.route('/verify', methods=['POST'])
def verify_user():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    # Get and save image
    file = request.files['image']
    userID = request.form['userID']  # Assuming userID is passed in form data
    filename = secure_filename(file.filename)
    filepath = os.path.join('uploads', filename)
    file.save(filepath)

    try:
        image = tf.keras.preprocessing.image.load_img(filepath, target_size=(224, 224))
        image = tf.keras.preprocessing.image.img_to_array(image)
        image = tf.expand_dims(image, axis=0)
        predictions = model.predict(image)
        is_human = int(tf.argmax(predictions, axis=1).numpy()[0]) == 1
        update_verification(userID, is_human)
        result = {"is_verified": is_human}
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
    return jsonify(result), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
