let consumptionChart = null; // Variable globale pour le graphique

document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    console.log("Événement 'submit' détecté");
    e.preventDefault(); // Empêche le rafraîchissement automatique

    const fileInput = document.getElementById('fileInput');
    const submitButton = document.getElementById('predictButton');
    const graphContainer = document.getElementById('graphContainer');
    const chartCanvas = document.getElementById('consumptionChart');

    // Vérification : Alerter si aucun fichier n'est sélectionné
    if (!fileInput.files.length) {
        alert('Veuillez sélectionner un fichier.');
        return;
    }

    // Désactiver le bouton pour éviter les clics multiples
    submitButton.disabled = true;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        console.log("Envoi de la requête à l'API Flask");
        const response = await fetch(`http://127.0.0.1:5000/predict?cache_buster=${new Date().getTime()}`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Erreur serveur : ${errorText}`);
        }

        const data = await response.json();
        console.log("Réponse reçue de l'API :", data);

        if (data.error) {
            throw new Error(data.error);
        }

        // Préparer les données pour le graphique
        const labels = data.predictions.map((_, index) => `Entrée ${index + 1}`);
        const predictionData = data.predictions;

        // Si un graphique existe déjà, le détruire
        if (consumptionChart) {
            console.log("Un graphique existe déjà, il sera mis à jour.");
            consumptionChart.destroy();
        }

        // Rendre le conteneur du graphique visible
        graphContainer.style.display = 'block';

        // Créer le nouveau graphique
        const ctx = chartCanvas.getContext('2d');
        consumptionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Consommation Prédite (kWh)',
                    data: predictionData,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    fill: false,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: { display: true, text: 'Entrées' }
                    },
                    y: {
                        title: { display: true, text: 'Consommation (kWh)' },
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (err) {
        console.error('Erreur détectée :', err);
        alert(`Erreur : ${err.message}`);
        graphContainer.style.display = 'none'; // Cacher le graphique en cas d'erreur
    } finally {
        submitButton.disabled = false; // Réactiver le bouton après traitement
    }
});
