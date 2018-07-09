package org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt;

public class MqttException extends Exception {

    public MqttException() {
        super();
    }

    public MqttException(String message, Throwable cause) {
        super(message, cause);
    }

    public MqttException(Throwable cause) {
        super(cause);
    }

}
