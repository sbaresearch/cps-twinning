package org.sba_research.demonstrator.iiotgateway;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.*;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt.*;
import org.sba_research.demonstrator.iiotgateway.sm.*;

public class GatewayStateMachine extends Thread implements StateMachine {

    private static final Logger logger = LogManager.getLogger(GatewayStateMachine.class);

    private GatewayState state = new InitialState();

    private volatile boolean stop;

    private final Object waiter = new Object();

    @Override
    public void runStateMachine() {
        this.stop = false;
        this.start();
    }

    @Override
    public void stopStateMachine() {
        this.state = new DisconnectState();
        wakeUp();
    }

    @Override
    public void run() {

        MqttObserver observer = new MqttObserver();
        observer.addListener(new MqttListener() {
            @Override
            public void onConnectionLost(Throwable throwable) {
                logger.error("Connection to MQTT broker lost. Trying to reconnect in 5 seconds...", throwable);
                try {
                    Thread.sleep(5000);
                } catch (InterruptedException e) {
                    logger.error("Could not sleep for five seconds.", e);
                }
                stop = false;
                state = new InitialState();
                wakeUp();
            }

            @Override
            public void onMessageArrived(String topic, MqttMessage message) {
                logger.info(String.format("MQTT message arrived for topic '%s': '%s'.", topic, message));
                state = new SendModbusRequestState(message.toString());
                wakeUp();
            }

            @Override
            public void onDeliveryComplete() {
                logger.info("MQTT message delivery complete.");
            }
        });

        /* MQTT client: */
        MqttClient mqttClient = new PahoMqttClient(new PahoMqttListener(observer));
        /* Modbus master: */
        ModbusTcpMaster modbusTcpMaster = new DigitalpetriModbusMaster();

        while (!stop && !Thread.currentThread().isInterrupted()) {
            try {
                state.execute(mqttClient, modbusTcpMaster);
                state = state.getNextState();
                /* In case previous state does not have a next state, wait for state change. */
                if (state == null) waitForStateChange();
                /* In case gateway is disconnected, stop thread immediately. */
                if (state instanceof DisconnectedState) this.stop = true;
            } catch (Exception ex) {
                logger.error("Unexpected error. Stopping IIoT Gateway.", ex);
                stopStateMachine();
            }
        }

    }

    private void waitForStateChange() {
        synchronized (waiter) {
            try {
                waiter.wait();
            } catch (InterruptedException e) {
                logger.error("Could not wait for state change.");
            }
        }
    }

    private void wakeUp() {
        synchronized (waiter) {
            waiter.notify();
        }
    }

}
