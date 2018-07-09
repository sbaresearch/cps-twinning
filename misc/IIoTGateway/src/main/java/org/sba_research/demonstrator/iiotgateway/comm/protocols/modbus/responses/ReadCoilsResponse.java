package org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses;

import java.nio.ByteBuffer;

public class ReadCoilsResponse implements ModbusResponse {

    private final ByteBuffer coils;

    public ReadCoilsResponse(ByteBuffer coils) {
        this.coils = coils;
    }

    public ByteBuffer getCoils() {
        return coils;
    }

}
