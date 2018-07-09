package org.sba_research.demonstrator.iiotgateway.sm;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.ModbusTcpMaster;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt.MqttClient;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt.MqttException;

public class ConnectedState extends GatewayState {

    private static final Logger logger = LogManager.getLogger(ConnectedState.class);

    public ConnectedState() {
        this.setNextState(new SubscribedState());
    }

    @Override
    public void execute(MqttClient mqttClient, ModbusTcpMaster modbusTcpMaster) {
        try {
            mqttClient.subscribe("candy/#", 2);
        } catch (MqttException e) {
            logger.error(e);
            this.setNextState(new ConnectedState());
            try {
                logger.info("Retrying to subscribe to topic in 5 seconds.");
                Thread.sleep(5000);
            } catch (InterruptedException ex) {
                logger.error(ex);
            }
        }
    }

}
