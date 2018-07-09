package org.sba_research.demonstrator.iiotgateway.comm.protocols.mqtt;

import org.jasypt.encryption.pbe.StandardPBEStringEncryptor;
import org.jasypt.encryption.pbe.config.EnvironmentPBEConfig;
import org.jasypt.properties.EncryptableProperties;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

public final class MqttConnectionProfile {

    private String brokerAddress;
    private String clientId;
    private String username;
    private char[] password;

    public MqttConnectionProfile(String brokerAddress, String clientId, String username, char[] password) {
        initConnectionProfile(brokerAddress, clientId, username, password);
    }

    public MqttConnectionProfile() {
        initFromConfigFile();
    }

    private void initConnectionProfile(String brokerAddress, String clientId, String username, char[] password) {
        this.brokerAddress = brokerAddress;
        this.clientId = clientId;
        this.username = username;
        this.password = password;
    }

    private void initFromConfigFile() {
        ClassLoader loader = Thread.currentThread().getContextClassLoader();
        try (InputStream resourceStream = loader.getResourceAsStream("main.properties")) {
            EnvironmentPBEConfig pbeConfig = new EnvironmentPBEConfig();
            pbeConfig.setPasswordEnvName(getPasswordEnvNameFromProperties());
            StandardPBEStringEncryptor encryptor = new StandardPBEStringEncryptor();
            encryptor.setConfig(pbeConfig);
            Properties encProps = new EncryptableProperties(encryptor);
            encProps.load(resourceStream);
            this.brokerAddress = encProps.getProperty("mqtt.address");
            this.clientId = encProps.getProperty("mqtt.clientId");
            this.username = encProps.getProperty("mqtt.username");
            String password = encProps.getProperty("mqtt.password");
            if (password == null)
                this.password = new char[]{};
            else
                this.password = password.toCharArray();
        } catch (IOException e) {
            throw new IllegalStateException("Could not retrieve properties file.", e);
        }

        if (!(this.brokerAddress != null && this.clientId != null && this.username != null && this.password.length != 0))
            throw new IllegalStateException("Invalid MQTT config.");
    }

    private String getPasswordEnvNameFromProperties() {
        ClassLoader loader = Thread.currentThread().getContextClassLoader();
        try (InputStream resourceStream = loader.getResourceAsStream("main.properties")) {
            Properties props = new Properties();
            props.load(resourceStream);
            final String pwEnvName = props.getProperty("main.jasypt.pbe.pwenvname");
            if (pwEnvName == null)
                throw new IllegalStateException("Missing property main.jasypt.pbe.pwenvname.");
            return pwEnvName;
        } catch (IOException e) {
            throw new IllegalStateException("Could not retrieve properties file.", e);
        }
    }

    public String getBrokerAddress() {
        return brokerAddress;
    }

    public String getClientId() {
        return clientId;
    }

    public String getUsername() {
        return username;
    }

    public char[] getPassword() {
        return password;
    }

}
