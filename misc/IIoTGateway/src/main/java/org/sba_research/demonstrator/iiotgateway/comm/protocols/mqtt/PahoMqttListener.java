package org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt;

import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.MqttCallback;

public class PahoMqttListener implements MqttCallback {

    private MqttObserver observer;

    public PahoMqttListener(MqttObserver observer) {
        this.observer = observer;
    }

    @Override
    public void connectionLost(Throwable throwable) {
        this.observer.notifyConnectionLost(throwable);
    }

    @Override
    public void messageArrived(String topic, org.eclipse.paho.client.mqttv3.MqttMessage mqttMessage) throws Exception {
        this.observer.notifyMessageArrived(topic, new MqttMessage(mqttMessage.getPayload(), mqttMessage.getQos()));
    }

    @Override
    public void deliveryComplete(IMqttDeliveryToken iMqttDeliveryToken) {
        this.observer.notifyDeliveryComplete();
    }

}
