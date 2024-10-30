
from pymodbus.client import AsyncModbusTcpClient
import logging

logger = logging.getLogger("ModbusService")

class ModbusService:
    def __init__(self, host, port, unit_id=1):
        self.client = AsyncModbusTcpClient(host, port=port)
        self.unit_id = unit_id

    async def fetch_data(self, address, count):
        await self.client.connect()
        result = await self.client.read_input_registers(address, count, unit=self.unit_id)
        await self.client.close()
        return result.registers if result else []
