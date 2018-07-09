package org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt;

public interface MqttClient {

    void connect() throws MqttException;

    void disconnect();

    void subscribe(String topicName, int qos) throws MqttException;

    void unsubscribe(String topicName);

}
