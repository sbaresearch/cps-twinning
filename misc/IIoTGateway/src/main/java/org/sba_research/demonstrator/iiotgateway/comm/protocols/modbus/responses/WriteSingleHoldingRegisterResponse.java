package org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses;

public class WriteSingleHoldingRegisterResponse implements ModbusResponse {

    private final int address;
    private final int value;

    public WriteSingleHoldingRegisterResponse(int address, int value) {
        this.address = address;
        this.value = value;
    }

    public int getAddress() {
        return this.address;
    }

    public int getValue() {
        return this.value;
    }

}
