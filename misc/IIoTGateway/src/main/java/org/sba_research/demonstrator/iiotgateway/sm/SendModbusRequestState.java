package org.sba_research.demonstrator.iiotgateway.sm;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.ModbusTcpMaster;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests.WriteMultipleRegistersRequest;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses.WriteMultipleRegistersResponse;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt.MqttClient;

import java.util.concurrent.CompletableFuture;

public class SendModbusRequestState extends GatewayState {

    private static final Logger logger = LogManager.getLogger(SendModbusRequestState.class);

    private final byte value;

    public SendModbusRequestState(String message) {
        /* Change state back to subscribed after request has been sent. */
        this.setNextState(new SubscribedState());
        this.value = getValueByMessageCode(message);
    }

    private byte getValueByMessageCode(String message) {
        switch (message) {
            case "Cherry":
                return 0x01;
            case "Mint":
                return 0x02;
            default:
                return 0x00;
        }
    }

    @Override
    public void execute(MqttClient mqttClient, ModbusTcpMaster modbusTcpMaster) {
        modbusTcpMaster.connect();
        // TODO: Parse from specification
        logger.info(String.format("Sending Modbus request (fc: 16), value: %d.", value));
        CompletableFuture<WriteMultipleRegistersResponse> fRegisters = modbusTcpMaster.sendRequest(new WriteMultipleRegistersRequest(4, 1, new byte[]{0, value}), 1);
        fRegisters.whenCompleteAsync((response, ex) -> {
            if (response != null)
                logger.info(String.format("Received Modbus response for function 16, affecting address %d.", response.getAddress()));
            else
                logger.error("Could not send request, message={}", ex.getMessage(), ex);
            modbusTcpMaster.disconnect();
        });
    }

}
