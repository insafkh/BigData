from flask import Flask, jsonify, request
import pandas as pd
import os
from flask_cors import CORS
import joblib
import logging
import numpy as np
from elasticsearch import Elasticsearch
from datetime import datetime

# Configuration de l'application Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Configuration CORS plus explicite

# Configuration Elasticsearch
try:
    es = Elasticsearch("http://localhost:9200")
    # Vérifier la connexion à Elasticsearch
    if not es.ping():
        raise ConnectionError("Impossible de se connecter à Elasticsearch")
except Exception as e:
    print(f"Erreur de connexion Elasticsearch : {e}")
    es = None

# Index pour stocker les résultats
index_name = 'predictions'

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', mode='a')  # Mode append pour ne pas écraser les logs précédents
    ]
)
logger = logging.getLogger(__name__)

# Fonction pour charger le modèle LightGBM
def load_lightgbm_model(model_path="lgbm_model.joblib"):
    try:
        if not os.path.exists(model_path):
            logger.error(f"Le fichier de modèle {model_path} n'existe pas.")
            return None
        
        lgbm_model = joblib.load(model_path)
        logger.info("Modèle LightGBM chargé avec succès.")
        return lgbm_model
    except Exception as e:
        logger.error(f"Erreur lors du chargement du modèle LightGBM : {str(e)}")
        return None

# Chargement du modèle LightGBM
lightgbm_model = load_lightgbm_model()
if lightgbm_model is None:
    logger.critical("Impossible de charger le modèle LightGBM. Arrêt du serveur.")
    exit(1)

@app.route('/')
def index():
    logger.info("Route '/' accédée.")
    return jsonify({"message": "Flask API pour les prédictions avec LightGBM.", "status": "ok"})

@app.route('/predict', methods=['GET'])
def predict():
    try:
        logger.info("Route '/predict' appelée.")

        # Chemin vers le fichier test
        test_data_path = "test1_data.csv"
        if not os.path.exists(test_data_path):
            logger.error(f"Le fichier {test_data_path} est introuvable.")
            return jsonify({"error": "Le fichier test_data.csv est introuvable."}), 404
        
        # Lecture des données
        data = pd.read_csv(test_data_path)
        logger.info(f"Données de test chargées, {len(data)} lignes lues.")

        # Colonnes nécessaires
        feature_columns = [
            'Global_reactive_power', 'Voltage', 
            'Sub_metering_1', 'Sub_metering_2', 'Sub_metering_3'
        ]
        
        # Vérification des colonnes
        missing_columns = [col for col in feature_columns + ['Global_active_power'] if col not in data.columns]
        if missing_columns:
            return jsonify({
                'error': f"Colonnes manquantes : {', '.join(missing_columns)}"
            }), 400
        
        # Préparation des features pour les modèles
        X = data[feature_columns]
        real_values = data['Global_active_power'].tolist()

        # Traiter les valeurs manquantes (imputer avec la moyenne)
        if X.isnull().values.any():
            logger.info("Des valeurs manquantes ont été trouvées dans les données d'entrée. Imputation avec la moyenne.")
            X = X.fillna(X.mean())

        # Prédictions LightGBM
        predictions_lightgbm = lightgbm_model.predict(X)

        # Calcul des métriques pour LightGBM
        mse_lightgbm = np.mean((np.array(real_values) - np.array(predictions_lightgbm)) ** 2)
        rmse_lightgbm = np.sqrt(mse_lightgbm)
        mae_lightgbm = np.mean(np.abs(np.array(real_values) - np.array(predictions_lightgbm)))

        # Réponse JSON
        response = {
            "predictions_lightgbm": [float(pred) for pred in predictions_lightgbm],
            "real_values": real_values,
            "metrics": {
                "LightGBM": {"MSE": float(mse_lightgbm), "RMSE": float(rmse_lightgbm), "MAE": float(mae_lightgbm)}
            },
            "features": {
                "global_reactive_power": X['Global_reactive_power'].tolist(),
                "voltage": X['Voltage'].tolist(),
                "sub_metering_1": X['Sub_metering_1'].tolist(),
                "sub_metering_2": X['Sub_metering_2'].tolist(),
                "sub_metering_3": X['Sub_metering_3'].tolist(),
                "global_active_power": real_values
            }
        }

        logger.info("Prédictions générées avec succès.")
        
        # Indexer les résultats dans Elasticsearch (facultatif)
        if es:
            doc = {
                "timestamp": datetime.now(),
                "model": "LGBM",
                "prediction": predictions_lightgbm.tolist(),
                "accuracy": {"MSE": mse_lightgbm, "RMSE": rmse_lightgbm, "MAE": mae_lightgbm},
                "real_values": real_values,
                "features": {
                    "global_reactive_power": X['Global_reactive_power'].tolist(),
                    "voltage": X['Voltage'].tolist(),
                    "sub_metering_1": X['Sub_metering_1'].tolist(),
                    "sub_metering_2": X['Sub_metering_2'].tolist(),
                    "sub_metering_3": X['Sub_metering_3'].tolist(),
                    "global_active_power": real_values
                }
            }
            es.index(index=index_name, document=doc)
            logger.info("Résultats indexés dans Elasticsearch.")

        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Erreur pendant les prédictions : {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)