function getCells(data, type) {
    cells="";
    for (const property in data) {
        cells += `<${type}>${data[property]}</${type}>`;
    }
    return cells;
}

function createBody(data) {
    return data.map(row => `<tr>${getCells(row, 'td')}</tr>`).join('');
}

function createTable(data) {

    // Destructure the headings (first row) from
    // all the rows
    const [headings, ...rows] = data;

    // Return some HTML that uses `getCells` to create
    // some headings, but also to create the rows
    // in the tbody.
    return `
            <thead>${getCells(headings, 'th')}</thead>
            <tbody>${createBody(rows)}</tbody>
    `;
}

function fillTable(data) {
    if (Array.isArray(data)) {
        data.unshift({"number": "number", "name": "name"});
        let tablerender = createTable(data);
        document.getElementById("entries").innerHTML = tablerender;
        console.log("it works?");
    }
}


// const socket = new WebSocket("ws://localhost:5678");
const socket = new WebSocket("ws://216.164.205.34:64209");

function refresh_queue() {
    socket.send("send_queue");
}

// Send a message to the server to trigger the queue send
socket.onopen = function() {
    refresh_queue();
    window.setInterval(refresh_queue, 2000);
};

// Receive the queue from the server
socket.onmessage = function(event) {
    jsondata = JSON.parse(event.data);
    console.log(jsondata);
    fillTable(jsondata);
};