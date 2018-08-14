package org.sba_research.demonstrator.iiotgateway.comm.protocols.modbus;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

public final class ModbusTcpConnectionProfile {

    private String address;
    private int port = 502;

    public ModbusTcpConnectionProfile(String address, int port) {
        initConnectionProfile(address, port);
    }

    public ModbusTcpConnectionProfile() {
        initFromConfigFile();
    }

    private void initConnectionProfile(String address, int port) {
        this.address = address;
        this.port = port;
    }

    private void initFromConfigFile() {

        ClassLoader loader = Thread.currentThread().getContextClassLoader();
        Properties props = new Properties();
        try (InputStream resourceStream = loader.getResourceAsStream("main.properties")) {
            props.load(resourceStream);
            this.address = props.getProperty("modbus.address");
            this.port = Integer.valueOf(props.getProperty("modbus.port"));
        } catch (IOException e) {
            throw new IllegalStateException("Could not retrieve properties file.", e);
        }
        if (this.address == null)
            throw new IllegalStateException("Invalid Modbus config.");

    }

    public String getAddress() {
        return address;
    }

    public int getPort() {
        return port;
    }

}
