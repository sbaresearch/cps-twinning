package org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;

public final class PahoMqttClient implements MqttClient {

    private MqttConnectOptions connectionOptions;
    private org.eclipse.paho.client.mqttv3.MqttClient mqttClient;
    private MemoryPersistence persistence = new MemoryPersistence();

    private static final Logger logger = LogManager.getLogger(PahoMqttClient.class);

    public PahoMqttClient(MqttConnectionProfile connectionProfile, PahoMqttListener mqttListener) {
        try {
            mqttClient = new org.eclipse.paho.client.mqttv3.MqttClient(connectionProfile.getBrokerAddress(), connectionProfile.getClientId(), persistence);
            connectionOptions = new MqttConnectOptions();
            connectionOptions.setUserName(connectionProfile.getUsername());
            connectionOptions.setPassword(connectionProfile.getPassword());
            connectionOptions.setConnectionTimeout(5);
            mqttClient.setCallback(mqttListener);
        } catch (org.eclipse.paho.client.mqttv3.MqttException ex) {
            logger.error("Could not create MQTT client.", ex);
        }
    }

    public PahoMqttClient(PahoMqttListener mqttListener) {
        this(new MqttConnectionProfile(), mqttListener);
    }

    public void connect() throws MqttException {
        try {
            mqttClient.connect(connectionOptions);
            logger.info("Connection to MQTT broker established.");
        } catch (org.eclipse.paho.client.mqttv3.MqttException ex) {
            throw new MqttException("Could not connect to MQTT broker.", ex);
        }
    }

    public void disconnect() {
        if (mqttClient != null) {
            try {
                mqttClient.disconnect();
                logger.info("MQTT client disconnected from broker.");
                mqttClient.close();
            } catch (org.eclipse.paho.client.mqttv3.MqttException ex) {
                logger.error("Could not disconnect from MQTT broker.", ex);
            }
        }
    }

    public void subscribe(String topicName, int qos) throws MqttException {
        if (topicName == null)
            throw new IllegalArgumentException("Parameter 'topicName' is null!");
        logger.info(String.format("Subscribing to topic '%s'.", topicName));
        try {
            mqttClient.subscribe(topicName, qos);
        } catch (org.eclipse.paho.client.mqttv3.MqttException ex) {
            throw new MqttException(String.format("MQTT client could not subscribe to topic '%s'.", topicName), ex);
        }
    }

    public void unsubscribe(String topicName) {
        if (topicName == null)
            throw new IllegalArgumentException("Parameter 'topicName' is null!");
        try {
            mqttClient.unsubscribe(topicName);
            logger.info(String.format("Unsubscribed from topic '%s'.", topicName));
        } catch (org.eclipse.paho.client.mqttv3.MqttException ex) {
            logger.error(String.format("MQTT client could not unsubscribe from topic '%s'.", topicName), ex);
        }
    }

}
