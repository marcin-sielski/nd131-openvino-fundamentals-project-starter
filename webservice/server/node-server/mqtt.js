var config;
const aedes = require('aedes')()
const server = require('net').createServer(aedes.handle)
const httpServer = require('http').createServer()
const ws = require('websocket-stream')

module.exports = {
    configure: function (c) {
        config = c;
    },

    start: function () {
        server.listen(config.mqtt.port, function () {
            console.log('server listening on port', config.mqtt.port)
        })

        ws.createServer({
            server: httpServer
        }, aedes.handle)

        httpServer.listen(config.mqtt.http.port, function () {
            console.log('websocket server listening on port', config.mqtt.http.port)
        })

        aedes.on('client', connecting);
        aedes.on('clientReady', connected)
        aedes.on('clientDisconnect', disconnected);
        aedes.on('publish', published);
        aedes.on('subscribe', subscribed);
        aedes.on('unsubscribe', unsubscribed);
    },

    publish: function (topic, message) {
        var payload = {
            topic: topic,
            payload: message,
            qos: 0,
            retain: false
        };

        server.publish(payload, function () {
            console.log('Published callback complete.');
        });
    }
};

function connecting(client) {
    console.log(`Client ${client.id} is connecting`);
}

function connected(client) {
    console.log(`Client ${client.id} connected`);
}

function subscribed(subscriptions, client) {
    for (var i = 0; i < subscriptions.length; i++) {
        console.log(`Client ${client.id} subscribed to ${subscriptions[i].topic}.`);
    }
}

function unsubscribed(subscriptions, client) {
    for (var i = 0; i < subscriptions.length; i++) {
        console.log(`Client ${client.id} unsubscribed from ${subscriptions[i].topic}.`);
    }
}

function disconnected(client) {
    console.log(`Client ${client.id}`);
}

function published(packet, client) {
    console.log(`Published to ${packet.topic} <- ${packet.payload}`);
}
