package org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests;

public class WriteSingleHoldingRegisterRequest implements ModbusRequest {

    private final int address;
    private final int value;

    public WriteSingleHoldingRegisterRequest(int address, int value) {
        this.address = address;
        this.value = value;
    }

    public int getAddress() {
        return address;
    }

    public int getValue() {
        return value;
    }

}
