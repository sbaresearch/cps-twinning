package org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt;

public interface MqttListener {

    void onConnectionLost(Throwable throwable);

    void onMessageArrived(String topic, MqttMessage message);

    void onDeliveryComplete();

}
