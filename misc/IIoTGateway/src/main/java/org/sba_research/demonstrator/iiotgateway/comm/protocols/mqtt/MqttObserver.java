package org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt;

import java.util.ArrayList;
import java.util.List;

public class MqttObserver {

    private List<MqttListener> listeners = new ArrayList<>();

    public void addListener(MqttListener listener) {
        if (listener == null)
            throw new IllegalArgumentException("Parameter 'listener' is null!");
        this.listeners.add(listener);
    }

    public void notifyConnectionLost(Throwable throwable) {
        listeners.forEach(l -> l.onConnectionLost(throwable));
    }

    public void notifyMessageArrived(String topic, MqttMessage message) {
        listeners.forEach(l -> l.onMessageArrived(topic, message));
    }

    public void notifyDeliveryComplete() {
        listeners.forEach(MqttListener::onDeliveryComplete);
    }


}
