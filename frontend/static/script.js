async function fetchDataAndUpdate() {
    try {
        const response = await fetch('/data');
        const data = await response.json();
        updateUI(data);
        updateChart(data);
    } catch (error) {
        console.error('Failed to fetch data:', error);
    }
}

function updateUI(data) {
    document.getElementById('left-clicks').textContent = `Left Clicks: ${formatNumber(data['clicks_left'])}`;
    document.getElementById('right-clicks').textContent = `Right Clicks: ${formatNumber(data['clicks_right'])}`;
    document.getElementById('middle-clicks').textContent = `Middle Clicks: ${formatNumber(data['clicks_middle'])}`;
    document.getElementById('key-presses').textContent = `Keypresses: ${formatNumber(data['key_presses'])}`;
    document.getElementById('mouse-movement').textContent = `Mouse Movement: ${formatNumber(data['mouse_movement'])} inches`;
    document.getElementById('log-file-size').textContent = `Log File Size: ${formatFileSize(data['__logging_size__'])}`;
    document.getElementById('logging-since').textContent = `Logging Since: ${data['__logging_since__']}`;
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

function updateChart(data) {
    const labelMappings = {
        'clicks_left': 'Left Clicks',
        'clicks_middle': 'Middle Clicks',
        'clicks_right': 'Right Clicks',
        'key_presses': 'Keypresses',
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
            hoverBackgroundColor: 'rgba(255, 255, 255, 0.2)',
        });
    });

    var ctx = document.getElementById('activity-chart').getContext('2d');
    var myChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Current'],
            datasets: datasets,

        },
        options: {
            responsive: false,
            maintainAspectRatio: false,
            scales: {
                x: {
                    display: true,
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
                    }
                },
                title: {
                    display: false,
                    text: 'Activity Tracker',
                    color: '#fff'
                },
                tooltip: {
                    enabled: true
                },
                autocolors: true,
            }
        }
    });
}

function getBackgroundColor(index) {
    const colors = [
        'rgba(255, 99, 132, 0.7)',
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(153, 102, 255, 0.7)'
    ];
    return colors[index % colors.length];
}

setInterval(fetchDataAndUpdate, 10000);
fetchDataAndUpdate();