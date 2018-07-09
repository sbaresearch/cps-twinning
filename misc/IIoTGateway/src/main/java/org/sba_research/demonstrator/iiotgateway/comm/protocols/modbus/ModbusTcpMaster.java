package org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus;

import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests.ModbusRequest;
import org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses.ModbusResponse;

import java.util.concurrent.CompletableFuture;

public interface ModbusTcpMaster extends ModbusMaster {

    void connect();

    <T extends ModbusResponse> CompletableFuture<T> sendRequest(ModbusRequest request, int unitId);

    void disconnect();

    void shutdown();

}
