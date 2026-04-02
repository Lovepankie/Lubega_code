def get_client(cfg):
    backend = cfg["modbus"]["backend"]

    if backend == "mbpoll":
        from .mbpoll_client import MBPollClient
        return MBPollClient(cfg["port"])

    elif backend == "pymodbus":
        from .modbus_client import ModbusClient
        return ModbusClient(cfg)

    else:
        raise ValueError("Invalid backend")