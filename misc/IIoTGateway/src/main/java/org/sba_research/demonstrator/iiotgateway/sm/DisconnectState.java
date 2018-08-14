package org.sba_research.demonstrator.iiotgateway.sm;

import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.ModbusTcpMaster;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt.MqttClient;

public class DisconnectState extends GatewayState {

    public DisconnectState() {
        this.setNextState(new DisconnectedState());
    }

    @Override
    public void execute(MqttClient mqttClient, ModbusTcpMaster modbusTcpMaster) {
        disconnect(mqttClient, modbusTcpMaster);
    }

    private void disconnect(MqttClient mqttClient, ModbusTcpMaster modbusTcpMaster) {
        if (mqttClient == null)
            throw new IllegalArgumentException("Parameter 'mqttClient' is null!");
        if (modbusTcpMaster == null)
            throw new IllegalArgumentException("Parameter 'modbusTcpMaster' is null!");
        mqttClient.disconnect();
        modbusTcpMaster.shutdown();
    }

}
