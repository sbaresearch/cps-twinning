package org.sba_research.demonstrator.iiotgateway.sm;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.ModbusTcpMaster;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt.MqttClient;

public class MqttConnectionErrorState extends GatewayState {

    private static final Logger logger = LogManager.getLogger(MqttConnectionErrorState.class);

    public MqttConnectionErrorState() {
        this.setNextState(new InitialState());
    }

    @Override
    public void execute(MqttClient mqttClient, ModbusTcpMaster modbusTcpMaster) {
        logger.info("Retrying to connect to MQTT broker in 5 seconds.");
        try {
            Thread.sleep(5000);
        } catch (InterruptedException e) {
            logger.error("Could not sleep thread for five seconds.", e);
        }
    }

}
