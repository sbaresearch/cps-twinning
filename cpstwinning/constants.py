import logging

# Logging
LOG_FILE_LOC = '/tmp/cps-twinning.log'
STATE_LOG_FILE_LOC = '/tmp/cps-twinning-states.log'
LOG_LEVEL = logging.DEBUG
LOG_FORMAT = '%(asctime)s.%(msecs)03d - p%(process)s {%(pathname)s:%(lineno)d} - %(name)s - %(levelname)s - %(message)s'
LOG_DATEFMT = '%Y-%m-%d,%H:%M:%S'
LOG_FORMATTER = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATEFMT)

# Kafka
KAFKA_BOOTSTRAP_SERVERS = '192.168.56.3:9092'
# Kafka Stimuli Consumer Topic
KAFKA_STIMULI_TOPIC = 'stimuli'
KAFKA_V_LOGS_TOPIC = 'v_logs'
