let myChart;
let isInitialLoad = true;

async function fetchDataAndUpdate() {
    try {
        const response = await fetch('/data');
        const data = await response.json();
        updateUI(data);
        updateChart(data);
        isInitialLoad = false;
    } catch (error) {
        console.error('Failed to fetch data:', error);
    }
}

function updateUI(data) {
    document.getElementById('left-clicks').innerHTML = `Left Clicks <span class="logger-value">${formatNumber(data['clicks_left'])}</span>`;
    document.getElementById('right-clicks').innerHTML = `Right Clicks <span class="logger-value">${formatNumber(data['clicks_right'])}</span>`;
    document.getElementById('middle-clicks').innerHTML = `Middle Clicks <span class="logger-value">${formatNumber(data['clicks_middle'])}</span>`;
    document.getElementById('key-presses').innerHTML = `Keypresses <span class="logger-value">${formatNumber(data['key_presses'])}</span>`;
    document.getElementById('gamepad-actions').innerHTML = `Gamepad Actions <span class="logger-value">${formatNumber(data['gamepad_actions'])}</span>`;
    document.getElementById('mouse-movement').innerHTML = `Mouse Movement ${randomInchesConversion(data['mouse_movement'], false)}`;
    document.getElementById('log-file-size').innerHTML = `Log File Size <span class="logger-value">${formatFileSize(data['__logging_size__'])}</span>`;
    document.getElementById('logging-since').innerHTML = `Logging Since <span class="logger-value"><br />${data['__logging_since__']}</span>`;
}

function formatFileSize(sizeInKB) {
    if (sizeInKB >= 1024 * 1024) {
        return Math.round(sizeInKB / (1024 * 1024)) + 'GB';
    } else if (sizeInKB >= 1024) {
        return Math.round(sizeInKB / 1024) + 'MB';
    } else {
        return Math.round(sizeInKB) + 'KB';
    }
}

const formatNumber = (num) => {
    if (num < 1000) {
        return num.toFixed(0);
    } else {
        const rounded = Math.round(num / 1000);
        return `${rounded}k`;
    }
};

const randomInchesConversion = (inches, includeCommas = true) => {
    const wrapValue = (value, unit, singularUnit) => {
        const isSingular = parseFloat(value) === 1 && !value.includes('.');
        const appropriateUnit = isSingular ? singularUnit : unit;

        if (includeCommas) {
            value = value.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        }

        const combinedLength = value.length + appropriateUnit.length;
        if (combinedLength >= 22) {
            return `<br /><span class="logger-value">${value}</span><br />${appropriateUnit}`;
        }
        return `<span class="logger-value">${value}</span> ${appropriateUnit}`;
    };

    const conversionFunctions = {
        inchesToInches: (inches) => {
            return wrapValue(inches.toString(), "inches", "inch");
        },
        inchesToFeet: (inches) => {
            const feet = (inches / 12).toFixed(3);
            return wrapValue(feet.toString(), "feet", "foot");
        },
        inchesToMiles: (inches) => {
            const miles = (inches / 63360).toFixed(3);
            return wrapValue(miles.toString(), "miles", "mile");
        },
        inchesToMeters: (inches) => {
            const meters = (inches / 39.3701).toFixed(3);
            return wrapValue(meters.toString(), "meters", "meter");
        },
        inchesToYards: (inches) => {
            const yards = (inches / 36).toFixed(3);
            return wrapValue(yards.toString(), "yards", "yard");
        },
        inchesToFootballFields: (inches) => {
            const fields = (inches / 3600).toFixed(3);
            return wrapValue(fields.toString(), "football fields", "football field");
        },
        inchesToOlympicPools: (inches) => {
            const pools = (inches / 1968.5).toFixed(3);
            return wrapValue(pools, "Olympic swimming pools", "Olympic swimming pool");
        },
        inchesToBasketballCourts: (inches) => {
            const courts = (inches / 1128).toFixed(3);
            return wrapValue(courts, "basketball courts", "basketball court");
        },
        inchesToEiffelTowers: (inches) => {
            const towers = (inches / 12756).toFixed(3);
            return wrapValue(towers, "Eiffel Towers", "Eiffel Tower");
        },
        inchesToFastAndTheFuriousRunWays: (inches) => {
            const runWays = (inches / 63360 / 18.37).toFixed(3);
            return wrapValue(runWays, "Fast & Furious 6 runways", "Fast & Furious 6 runway");
        },
        inchesToRealLife: (inches) => {
            // we just divide our inches by the dpi of the mouse (400)
            const realLife = (inches / 400).toFixed(3);
            return wrapValue(realLife, "real life inches", "real life inch");
        }
    };

    const conversionKeys = Object.keys(conversionFunctions);

    const weights = {
        inchesToInches: 100,
        inchesToFeet: 100,
        inchesToMiles: 100,
        inchesToMeters: 100,
        inchesToYards: 25,
        inchesToFootballFields: 1,
        inchesToOlympicPools: 1,
        inchesToBasketballCourts: 1,
        inchesToEiffelTowers: 1,
        inchesToFastAndTheFuriousRunWays: 0.5,
        inchesToRealLife: 5
    };

    const weightedConversions = [];

    for (const key of conversionKeys) {
        for (let i = 0; i < weights[key]; i++) {
            weightedConversions.push(conversionFunctions[key]);
        }
    }

    const randomConversion = weightedConversions[Math.floor(Math.random() * weightedConversions.length)];
    return randomConversion(inches);
};



function updateChart(data) {
    const labelMappings = {
        'clicks_left': 'Left Clicks',
        'clicks_middle': 'Middle Clicks',
        'clicks_right': 'Right Clicks',
        'key_presses': 'Keypresses',
        'gamepad_actions': 'Gamepad Actions',
        'mouse_movement': 'Mouse Movement',
    };

    const filteredKeys = Object.keys(data).filter(key => !['__logging_size__', '__logging_since__', '__current_time__'].includes(key));
    const labels = filteredKeys.map(key => labelMappings[key] || key); // Use mapped label if defined, otherwise use original key
    const datasets = [];

    labels.forEach((label, index) => {
        datasets.push({
            label: label,
            data: [data[filteredKeys[index]]],
            backgroundColor: getBackgroundColor(index),
            categoryPercentage: 0.75,
            hoverBackgroundColor: 'rgba(55, 250, 178, 1)',
        });
    });

    if (myChart) {
        myChart.data.datasets = datasets;
        myChart.options.animation = isInitialLoad ? {} : false; // Disable animation after the initial load
        myChart.update();
    } else {
        var ctx = document.getElementById('activity-chart').getContext('2d');
        myChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Current'],
                datasets: datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                animation: {
                    duration: 3000, // Animation duration for the initial load
                },
                scales: {
                    x: {
                        display: false,
                    },
                    y: {
                        type: "logarithmic",
                        suggestedMax: 100000,
                        beginAtZero: true,
                        display: false,
                    },
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#fff'
                        },
                        onClick: (e) => e.stopPropagation(), // Disable legend click behavior
                        title: {
                            display: true,
                            text: 'Shut-in Simulator',
                            color: '#37fab2',
                            font: {
                                size: 24,
                                family: 'Inconsolata, monospace',
                                weight: 'bold',
                            }
                        }
                    },
                    title: {
                        display: false,
                        text: 'Activity Tracker',
                        color: '#fff'
                    },
                    tooltip: {
                        enabled: true,
                    },
                    autocolors: true,
                    afterDraw: function(chart) {
                        const ctx = chart.ctx;
                        ctx.save();
                        ctx.shadowColor = '#37fab2';
                        ctx.shadowBlur = 5;
                        ctx.fillStyle = '#37fab2';
                        ctx.font = Chart.helpers.fontString(24, 'bold', 'Inconsolata, monospace');
                        ctx.fillText('Stalk Me', chart.width / 2, 40);
                        ctx.restore();
                    },
                }
            }
        });
    }
}

function getBackgroundColor(index) {
    const colors = [
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)',
        
    ];
    return colors[index % colors.length];
}

setInterval(fetchDataAndUpdate, 10000);
fetchDataAndUpdate();
