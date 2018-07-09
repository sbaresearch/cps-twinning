package org.sba_research.demonstrator.iiotgateway;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

public class IIoTGateway {

    private static final Logger logger = LogManager.getLogger(IIoTGateway.class);

    public static void main(String[] args) {
        GatewayStateMachine gw = new GatewayStateMachine();
        gw.runStateMachine();
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("Shutting down...");
            try {
                gw.stopStateMachine();
                gw.join();
            } catch (InterruptedException e) {
                gw.interrupt();
                logger.error(e);
            }
        }));
    }

}
