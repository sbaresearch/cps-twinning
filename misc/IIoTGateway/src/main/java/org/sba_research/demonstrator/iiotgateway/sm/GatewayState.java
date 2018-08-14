package org.sba_research.demonstrator.iiotgateway.sm;

import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.ModbusTcpMaster;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt.MqttClient;

public abstract class GatewayState {

    private GatewayState nextState;

    public abstract void execute(MqttClient mqttClient, ModbusTcpMaster modbusTcpMaster);

    public void setNextState(GatewayState nextState) {
        this.nextState = nextState;
    }

    public GatewayState getNextState() {
        return nextState;
    }

};
