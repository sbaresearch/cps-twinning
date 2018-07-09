package org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests;

public class ReadCoilsRequest implements ModbusRequest {

    private final int address;
    private final int quantity;

    public ReadCoilsRequest(int address, int quantity) {
        this.address = address;
        this.quantity = quantity;
    }

    public int getAddress() {
        return address;
    }

    public int getQuantity() {
        return quantity;
    }

}
