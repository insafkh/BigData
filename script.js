document.addEventListener("DOMContentLoaded", function () {
    // Liste des métriques à visualiser (sans prédictions)
    const metrics = [
        { id: 'Voltage', label: 'Voltage', color: 'rgba(255, 206, 86, 1)' }
    ];

    // Fonction pour créer la configuration des graphiques de prédiction LGBM
    function createPredictionChartConfig(label, predictionColor) {
        return {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: `Prédictions (${label})`,
                        data: [],
                        borderColor: predictionColor,
                        backgroundColor: predictionColor.replace('1)', '0.2)'),
                        borderWidth: 2,
                        fill: false
                    },
                    {
                        label: 'Valeurs Réelles',
                        data: [],
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderWidth: 2,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false, // Disable animations for real-time charts
                parsing: false, // Optimize dataset parsing
                plugins: {
                    title: { display: true, text: label }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Temps (minutes)' },
                        ticks: { autoSkip: true, maxTicksLimit: 20 }
                    },
                    y: {
                        title: { display: true, text: 'Volte' },
                        min: 0,
                        max: 500
                    }
                }
            }
            
        };
    }

    // Fonction pour créer la configuration des graphiques pour les valeurs réelles
    function createRealValuesChartConfig(label, color) {
        return {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: label,
                        data: [],
                        borderColor: color,
                        backgroundColor: color.replace('1)', '0.2)'),
                        borderWidth: 2,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                plugins: {
                    title: { display: true, text: label }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Temps (minutes)' },
                        ticks: { autoSkip: true, maxTicksLimit: 20 }
                    },
                    y: {
                        title: { display: true, text: 'Volte' },
                        min: 0,
                        max: 500
                    }
                }
            }
        };
    }

    // Création des graphiques
    const charts = {};
    const configs = {};

    // Création du graphique LGBM Global Active Power avec prédictions
    const ctx_lgbm = document.getElementById('predictionChartLGBM').getContext('2d');
    configs['LGBM'] = createPredictionChartConfig('LGBM', 'rgba(54, 162, 235, 1)');
    const chart_lgbm = new Chart(ctx_lgbm, configs['LGBM']);

    // Création des graphiques pour les autres métriques (Voltage uniquement)
    metrics.forEach(metric => {
        const ctx = document.getElementById('predictionChartVoltage').getContext('2d');
        configs[metric.id] = createRealValuesChartConfig(metric.label, metric.color);
        charts[metric.id] = new Chart(ctx, configs[metric.id]);
    });

    // Variables pour stocker les données
    let currentIndex = 0;
    let allPredictionsLGBM = [];
    let allRealValues = {};

    // Fonction pour mettre à jour les graphiques
    function updateCharts() {
        if (currentIndex >= allPredictionsLGBM.length) {
            console.log("Toutes les données ont été affichées");
            return;
        }

        // Mise à jour du graphique LGBM avec prédictions
        chart_lgbm.data.labels.push(currentIndex);
        chart_lgbm.data.datasets[0].data.push(allPredictionsLGBM[currentIndex]);
        chart_lgbm.data.datasets[1].data.push(allRealValues.global_active_power[currentIndex]);

        // Gestion de la fenêtre glissante pour LGBM
        const maxDataPoints = 50;
        if (chart_lgbm.data.labels.length > maxDataPoints) {
            chart_lgbm.data.labels.shift();
            chart_lgbm.data.datasets.forEach(dataset => dataset.data.shift());
        }
        chart_lgbm.update('none');

        // Mise à jour des graphiques pour les autres métriques
        metrics.forEach(metric => {
            const normalizedId = metric.id.toLowerCase();
            charts[metric.id].data.labels.push(currentIndex);
            charts[metric.id].data.datasets[0].data.push(allRealValues[normalizedId][currentIndex]);

            if (charts[metric.id].data.labels.length > maxDataPoints) {
                charts[metric.id].data.labels.shift();
                charts[metric.id].data.datasets[0].data.shift();
            }
            charts[metric.id].update('none');
        });

        currentIndex++;
    }

    // Récupérer les données depuis l'API Flask
    fetch('http://localhost:5000/predict')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data.predictions_lightgbm || !data.features) {
                throw new Error("Données manquantes dans la réponse.");
            }

            allPredictionsLGBM = data.predictions_lightgbm;
            allRealValues = data.features;

            // Vérification supplémentaire pour les données attendues
            if (!Array.isArray(allPredictionsLGBM) || typeof allRealValues !== 'object') {
                throw new Error("Format de données inattendu.");
            }

            // Démarrer l'intervalle pour mettre à jour les graphiques
            const updateInterval = setInterval(updateCharts, 100);
            setTimeout(() => clearInterval(updateInterval), allPredictionsLGBM.length * 100);
        })
        .catch(error => {
            console.error("Erreur lors de la récupération des données :", error);
            document.getElementById('errorMessage').textContent = `Erreur : ${error.message}`;
        });
});
