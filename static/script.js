const ctx = document.getElementById('winChart').getContext('2d');

// Initialize chart
const winChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Team ORDER Win %',
                data: [],
                borderColor: 'blue',
                fill: false
            },
            {
                label: 'Team CHAOS Win %',
                data: [],
                borderColor: 'red',
                fill: false
            }
        ]
    },
    options: {
        scales: {
            x: { title: { display: true, text: 'Time' } },
            y: { title: { display: true, text: 'Win Percentage (%)' } }
        }
    }
});

// Function to fetch live data
async function fetchLiveData() {
    try {
        const response = await fetch('/live-data');
        const data = await response.json();

        // Update team stats
        document.getElementById('team-order-stats').innerHTML = `
            <h3>Team ORDER</h3>
            <p>Kills: ${data.team_order_stats.kills}</p>
            <p>Deaths: ${data.team_order_stats.deaths}</p>
            <p>Assists: ${data.team_order_stats.assists}</p>
        `;
        document.getElementById('team-chaos-stats').innerHTML = `
            <h3>Team CHAOS</h3>
            <p>Kills: ${data.team_chaos_stats.kills}</p>
            <p>Deaths: ${data.team_chaos_stats.deaths}</p>
            <p>Assists: ${data.team_chaos_stats.assists}</p>
        `;

        // Update chart
        const currentTime = new Date().toLocaleTimeString();
        winChart.data.labels.push(currentTime);
        winChart.data.datasets[0].data.push(data.predictions.team_order_win);
        winChart.data.datasets[1].data.push(data.predictions.team_chaos_win);
        winChart.update();
    } catch (err) {
        console.error("Error fetching live data:", err);
    }
}

// Poll every 1 second
setInterval(fetchLiveData, 1000);
