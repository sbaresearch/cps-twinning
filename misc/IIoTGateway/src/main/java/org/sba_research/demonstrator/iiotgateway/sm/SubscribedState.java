package org.sba_research.demonstrator.iiotgateway.sm;

import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.ModbusTcpMaster;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt.MqttClient;

public class SubscribedState extends GatewayState {

    public SubscribedState() {
        /* Explicitly set next state to 'null'. */
        this.setNextState(null);
    }

    @Override
    public void execute(MqttClient mqttClient, ModbusTcpMaster modbusTcpMaster) {
        // Empty on purpose
    }

}
