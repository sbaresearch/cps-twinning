package org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus;

import com.digitalpetri.modbus.codec.Modbus;
import io.netty.util.ReferenceCountUtil;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests.ReadCoilsRequest;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests.ReadHoldingRegistersRequest;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests.WriteMultipleRegistersRequest;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests.WriteSingleHoldingRegisterRequest;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses.ReadCoilsResponse;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses.ReadHoldingRegistersResponse;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses.WriteMultipleRegistersResponse;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses.WriteSingleHoldingRegisterResponse;

import java.util.concurrent.CompletableFuture;

public class DigitalpetriModbusMaster implements ModbusTcpMaster {

    private static final Logger logger = LogManager.getLogger(DigitalpetriModbusMaster.class);

    private com.digitalpetri.modbus.master.ModbusTcpMaster master;
    private com.digitalpetri.modbus.master.ModbusTcpMasterConfig config;

    public DigitalpetriModbusMaster(ModbusTcpConnectionProfile connectionProfile) {
        this.config = new com.digitalpetri.modbus.master.ModbusTcpMasterConfig.Builder(connectionProfile.getAddress())
                .setPort(connectionProfile.getPort())
                .build();
    }

    public DigitalpetriModbusMaster() {
        this(new ModbusTcpConnectionProfile());
    }

    @Override
    public void connect() {
        if (this.master == null)
            this.master = new com.digitalpetri.modbus.master.ModbusTcpMaster(config);
    }

    @Override
    @SuppressWarnings("unchecked")
    public <T extends org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses.ModbusResponse> CompletableFuture<T>
    sendRequest(org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests.ModbusRequest request, int unitId) {
        if (request == null)
            throw new IllegalArgumentException("Parameter 'request' is null!");

        com.digitalpetri.modbus.requests.ModbusRequest dpR;

        if (request instanceof ReadHoldingRegistersRequest) {
            ReadHoldingRegistersRequest r = (ReadHoldingRegistersRequest) request;
            dpR = new com.digitalpetri.modbus.requests.ReadHoldingRegistersRequest(r.getAddress(), r.getQuantity());
        } else if (request instanceof org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests.ReadCoilsRequest) {
            ReadCoilsRequest r = (ReadCoilsRequest) request;
            dpR = new com.digitalpetri.modbus.requests.ReadCoilsRequest(r.getAddress(), r.getQuantity());
        } else if (request instanceof WriteSingleHoldingRegisterRequest) {
            WriteSingleHoldingRegisterRequest r = (WriteSingleHoldingRegisterRequest) request;
            dpR = new com.digitalpetri.modbus.requests.WriteSingleRegisterRequest(r.getAddress(), r.getValue());
        } else if (request instanceof WriteMultipleRegistersRequest) {
            WriteMultipleRegistersRequest r = (WriteMultipleRegistersRequest) request;
            dpR = new com.digitalpetri.modbus.requests.WriteMultipleRegistersRequest(r.getAddress(), r.getQuantity(), r.getValues());
        } else
            throw new UnsupportedOperationException();

        CompletableFuture<com.digitalpetri.modbus.responses.ModbusResponse> dpFuture = master.sendRequest(dpR, unitId);

        return dpFuture
                .whenCompleteAsync((response, ex) -> {
                    if (response == null)
                        logger.error("Completed exceptionally, message={}", ex.getMessage(), ex);
                })
                .thenApplyAsync(modbusResponse -> {
                    T r;
                    if (modbusResponse instanceof com.digitalpetri.modbus.responses.ReadHoldingRegistersResponse) {
                        com.digitalpetri.modbus.responses.ReadHoldingRegistersResponse response = (com.digitalpetri.modbus.responses.ReadHoldingRegistersResponse) modbusResponse;
                        r = (T) new ReadHoldingRegistersResponse(response.getRegisters().nioBuffer());
                    } else if (modbusResponse instanceof com.digitalpetri.modbus.responses.ReadCoilsResponse) {
                        com.digitalpetri.modbus.responses.ReadCoilsResponse response = (com.digitalpetri.modbus.responses.ReadCoilsResponse) modbusResponse;
                        r = (T) new ReadCoilsResponse(response.getCoilStatus().nioBuffer());
                    } else if (modbusResponse instanceof com.digitalpetri.modbus.responses.WriteSingleRegisterResponse) {
                        com.digitalpetri.modbus.responses.WriteSingleRegisterResponse response = (com.digitalpetri.modbus.responses.WriteSingleRegisterResponse) modbusResponse;
                        r = (T) new WriteSingleHoldingRegisterResponse(response.getAddress(), response.getValue());
                    } else if (modbusResponse instanceof com.digitalpetri.modbus.responses.WriteMultipleRegistersResponse) {
                        com.digitalpetri.modbus.responses.WriteMultipleRegistersResponse response = (com.digitalpetri.modbus.responses.WriteMultipleRegistersResponse) modbusResponse;
                        r = (T) new WriteMultipleRegistersResponse(response.getAddress(), response.getQuantity());
                    } else
                        throw new UnsupportedOperationException();
                    ReferenceCountUtil.release(modbusResponse);
                    return r;
                });
    }

    @Override
    public void disconnect() {
        if (master != null) {
            master.disconnect();
            logger.info("Modbus master disconnected from slave.");
        }
    }

    @Override
    public void shutdown() {
        this.disconnect();
        logger.info("Releasing Modbus shared resources...");
        Modbus.releaseSharedResources();
    }
}
