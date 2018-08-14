package org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.responses;

public class WriteMultipleRegistersResponse implements ModbusResponse {

    private final int address;
    private final int quantity;

    public WriteMultipleRegistersResponse(int address, int quantity) {
        this.address = address;
        this.quantity = quantity;
    }

    public int getAddress() {
        return this.address;
    }

    public int getQuantity() {
        return this.quantity;
    }

}
