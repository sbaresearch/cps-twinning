package org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses;

import java.nio.ByteBuffer;

public class ReadHoldingRegistersResponse implements ModbusResponse {

    private final ByteBuffer registers;

    public ReadHoldingRegistersResponse(ByteBuffer registers) {
        this.registers = registers;
    }

    public ByteBuffer getRegisters() {
        return registers;
    }

}
