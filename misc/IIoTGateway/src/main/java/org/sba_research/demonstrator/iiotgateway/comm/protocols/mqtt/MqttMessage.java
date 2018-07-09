package org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt;

public final class MqttMessage {

    private byte[] payload;

    private int qos = 1;

    public MqttMessage(byte[] payload, int qos) {
        if (qos < 0 || qos > 2)
            throw new IllegalArgumentException("Invalid QoS!");
        this.payload = payload;
        this.qos = qos;
    }

    public byte[] getPayload() {
        return payload;
    }

    public int getQos() {
        return qos;
    }

    @Override
    public String toString() {
        return new String(payload);
    }

}
