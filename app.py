from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import numpy as np
import joblib
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
@app.after_request
def apply_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
# Configurer le dossier de téléchargement
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'txt'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

import logging

@app.route('/predict', methods=['POST'])
def predict():
    try:
        if 'file' not in request.files:
            app.logger.error('Aucun fichier téléchargé.')
            return jsonify({'error': 'Aucun fichier téléchargé.'}), 400

        file = request.files['file']
        if file.filename == '':
            app.logger.error('Aucun fichier sélectionné.')
            return jsonify({'error': 'Aucun fichier sélectionné.'}), 400

        if not allowed_file(file.filename):
            app.logger.error('Type de fichier non autorisé.')
            return jsonify({'error': 'Type de fichier non autorisé. Utilisez .csv ou .txt'}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        app.logger.info(f"Fichier téléchargé et sauvegardé sous {file_path}")

        try:
            data = pd.read_csv(file_path, delimiter=";")
            app.logger.info(f"Colonnes lues : {data.columns}")
        except Exception as e:
            app.logger.error(f"Erreur de lecture du fichier : {str(e)}")
            return jsonify({'error': f'Erreur de lecture du fichier : {str(e)}'}), 400

        required_columns = ['global_reactive_power', 'voltage', 'sub_metering_1', 'sub_metering_2', 'sub_metering_3']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            app.logger.error(f"Colonnes manquantes : {', '.join(missing_columns)}")
            return jsonify({'error': f'Colonnes manquantes : {", ".join(missing_columns)}'}), 400

        input_data = data[required_columns].values

        try:
            model = joblib.load('model.pkl')
            app.logger.info("Modèle chargé avec succès.")
        except FileNotFoundError:
            app.logger.error("Modèle de prédiction non trouvé.")
            return jsonify({'error': 'Modèle de prédiction non trouvé.'}), 500

        predictions = model.predict(input_data)
        app.logger.info(f"Prédictions générées : {predictions.tolist()}")

        os.remove(file_path)  # Supprimer le fichier après traitement

        # Réponse JSON contenant les résultats des prédictions
        response_data = {
            'predictions': predictions.tolist(),
            'message': f'Prédictions générées pour {len(predictions)} entrées.'
        }
        app.logger.info(f"Réponse envoyée : {response_data}")
        return jsonify(response_data)

    except Exception as e:
        app.logger.error(f"Erreur inattendue : {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
