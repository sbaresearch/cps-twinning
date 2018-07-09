package org.sba_research.demonstrator.iiotgateway.sm;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.ModbusTcpMaster;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt.MqttClient;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt.MqttException;

public class InitialState extends GatewayState {

    private static final Logger logger = LogManager.getLogger(InitialState.class);

    public InitialState() {
        this.setNextState(new ConnectedState());
    }

    @Override
    public void execute(MqttClient mqttClient, ModbusTcpMaster modbusTcpMaster) {
        try {
            logger.info("Connecting to MQTT broker.");
            mqttClient.connect();
        } catch (MqttException ex) {
            logger.error(ex.getMessage(), ex.getCause());
            this.setNextState(new MqttConnectionErrorState());
        }
    }

}
