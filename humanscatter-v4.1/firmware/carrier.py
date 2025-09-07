import time
from machine import Pin, SPI

# =================== PINS ====================
ADF4351_SCK = 10    # SPI Clock
ADF4351_MOSI = 11   # SPI Data
ADF4351_LE = 9      # Latch Enable

# =================== SPI SETUP ====================
spi_tx = SPI(
    1,
    baudrate=5000000,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=Pin(ADF4351_SCK),
    mosi=Pin(ADF4351_MOSI),
    miso=None
)

LE = Pin(ADF4351_LE, Pin.OUT)
LE.value(1)

# =================== ADF4351 REGISTERS ====================
ADF4351_REGISTERS = [
    0x00620000,  # R0
    0x08008011,  # R1
    0x004B3CC2,  # R2
    0x000004B3,  # R3
    0x00AC803C,  # R4
    0x00580005   # R5
]

# =================== FUNCTIONS ====================

def adf4351_write_reg(reg):
    """Send a 32-bit register to ADF4351"""
    data = reg.to_bytes(4, "big")
    LE.value(0)
    spi_tx.write(data)
    LE.value(1)
    time.sleep_us(1)

def setup_TX():
    """Initialize ADF4351 with precomputed registers"""
    for reg in reversed(ADF4351_REGISTERS):  # Must write R5 → R0
        adf4351_write_reg(reg)
    time.sleep_ms(10)

def set_frequency(f_out_hz, ref_clk=25000000):
    """
    Set output frequency dynamically in INT-N mode.
    """
    INT = int(f_out_hz / ref_clk)
    FRAC = 0
    MOD = 1

    # Update R0 with new INT value
    ADF4351_REGISTERS[0] = (INT << 15) | (FRAC << 3) | 0
    setup_TX()

def start_carrier_TX():
    """Enable RF output"""
    setup_TX()

def stop_carrier_TX():
    """Disable RF output (power down)"""
    reg4 = ADF4351_REGISTERS[4] & ~(3 << 3)  # Clear power bits
    adf4351_write_reg(reg4)

def test_adf4351():
    print("Initializing ADF4351 at 2.45 GHz...")
    setup_TX()
    print("Carrier ON at 2.45 GHz")
