package org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus.requests;

public class WriteMultipleRegistersRequest implements ModbusRequest {

    private final int address;
    private final int quantity;
    private final byte[] values;

    public WriteMultipleRegistersRequest(int address, int quantity, byte[] values) {
        if (values.length != quantity * 2)
            throw new IllegalArgumentException("Length of values must equal 2 * quantity.");
        this.address = address;
        this.quantity = quantity;
        this.values = values;
    }

    public int getAddress() {
        return address;
    }

    public int getQuantity() {
        return quantity;
    }

    public byte[] getValues() {
        return values;
    }

}
