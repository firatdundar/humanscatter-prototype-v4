import time
import carrier
import machine
import math
from machine import Pin, SPI, ADC, Timer
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY, PEN_P4

#================ VARIABLES =============

# Print Receiver Radio Configuration
config_prints = False

# Radio Parameters
BAUDRATE = 100000
F_XOSC = 26000000
CARRIER_FEQ = 2450000000
RX_BUFFER_SIZE = 64

# Values
r_data = 100000
bw = 794444
f_dev = 347222
f_carrier = 6597222

# --- NEW PIN CONFIGURATION ---
PIN_SCK = 10
PIN_MOSI = 11
PIN_MISO = 8
PIN_CS = 22
PIN_GDO0 = 2
PIN_GD2 = 3

# SPI initialization
spi_rx = SPI(
    1,
    baudrate=BAUDRATE,
    polarity=0,
    phase=0,
    bits=8,
    firstbit=SPI.MSB,
    sck=Pin(PIN_SCK),
    mosi=Pin(PIN_MOSI),
    miso=Pin(PIN_MISO)
)

# Chip Select Pin
cs_rx = Pin(PIN_CS, Pin.OUT)
cs_rx.value(1)  # Active low

# Interrupt pins
gdo0_pin = Pin(PIN_GDO0, Pin.IN)
gd2_pin = Pin(PIN_GD2, Pin.IN)

#================ REST OF CODE =============

# Strobes
SIDLE = 0x36    #Idle mode of radio
SRX = 0x34      #Receive mode of radio
SFRX = 0x3A     #Clear FIFO
SRES = 0x30     #Reset radio

# Registers
cc2500_receiver_settings=[[0x02, 0x06],
                          [0x08, 0x05],
                          [0x0b, 0x0A],
                          [0x0e, 0x7C],
                          [0x0f, 0x08],
                          [0x10, 0x0B],
                          [0x11, 0xF1],
                          [0x12, 0x03],
                          [0x13, 0x23],
                          [0x14, 0xFF],
                          [0x15, 0x76],
                          [0x18, 0x18],
                          [0x19, 0x1D],
                          [0x1a, 0x1C],
                          [0x1b, 0xC7],
                          [0x1c, 0x00],
                          [0x1d, 0xB0],
                          [0x21, 0xB6],
                          [0x25, 0x00],
                          [0x26, 0x11]]


class Message:
    data = ""
    overflow = 0
    RSSI = 0
    CRC = 0
    length = 0
    sequence = 0
    link_quality_indicator = 0

#================ FUNCTIONS =============

#-------------- setup functions --------------

def setup_RX(spi, CS, Pin_interrupt):
    write_strobe_RX(spi, CS, SRES)
    time.sleep_us(100)
    write_strobe_RX(spi, CS, SIDLE)
    
    write_register_RX(spi, CS, cc2500_receiver_settings)
    if (config_prints):
        print("set spi config  RX:")
        print([f"0x{byte:02X}" for pair in cc2500_receiver_settings for byte in pair])
        print(cc2500_receiver_settings)
    set_irq_RX(Pin_interrupt)
    set_frequency_RX(spi, CS, f_carrier + CARRIER_FEQ)
    set_freq_deviation_RX(spi, CS, f_dev)
    set_datarate_RX(spi, CS, r_data)
    set_filter_bandwidth_RX(spi, CS, bw)
    write_register_RX(spi, CS, [[0x10,0x0B]])

def interrupt_handler_RX(Pin):
    global event
    event = "reception"
    
def set_irq_RX(Pin_interrupt):
    interrupt_pin = machine.Pin(Pin_interrupt, mode=Pin.IN)
    interrupt_pin.irq(trigger=Pin.IRQ_FALLING,handler=interrupt_handler_RX)

#-------------- radio config functions --------------
    
def set_datarate_RX(spi, CS, r_data):
    write_strobe_RX(spi, CS, SIDLE)
    drate_e = int(math.log2((r_data * (1 << 20)) / F_XOSC))
    drate_m = int((r_data * (1<<28)) / (F_XOSC * (1 << drate_e)) - 256.0)
    r_data_calculated = int(((256.0 + drate_m) * (1<<drate_e) * F_XOSC) / (1<<28)) 
    mdmcfg3 = read_register_RX(spi, CS, 0x10)[0];
    msg = [[0x10, (mdmcfg3 & 0xf0) + (drate_e & 0x0f)], [0x11, drate_m]]
    write_register_RX(spi, CS, msg)
    if (config_prints):
        print(f"set RX r_data : [{drate_e} {drate_m}] {r_data_calculated}")
        print("\nset_datarate RX")
        print([f"0x{byte:02X}" for pair in msg for byte in pair])
        print(msg)

def set_filter_bandwidth_RX(spi, CS, bw):
    write_strobe_RX(spi, CS, SIDLE)
    chanbw_e = int(math.log2(F_XOSC / ((1<<5) * bw) / math.log2(2.0)))
    chanbw_m = int(F_XOSC / (8.0 * bw * (1<<chanbw_e)) - 4.0)
    bw_calculated = int(F_XOSC / (8.0 * (4.0 + chanbw_m) * (1<<chanbw_e)))
    mdmcfg3 = read_register_RX(spi, CS, 0x10)[0];
    msg = [[0x10, ((chanbw_e & 0x03)<<6) + ((chanbw_m & 0x03)<<4) + (mdmcfg3 & 0x0f)]]
    write_register_RX(spi, CS, msg)
    if (config_prints):
        print(f"set RX bw: [{chanbw_e} {chanbw_m}] {bw_calculated}")
        print("\nset_filter_bandwidth RX")
        print([f"0x{byte:02X}" for pair in msg for byte in pair])
        print(msg)

def set_freq_deviation_RX(spi, CS, f_dev):
    write_strobe_RX(spi, CS, SIDLE)  
    deviation_e = int(math.log2(f_dev * (1<<14) / F_XOSC))
    deviation_m = int(f_dev * (1<<17) / ((1<<deviation_e) * F_XOSC) - 8.0)
    f_dev_calculated = int(F_XOSC * (8.0 + deviation_m + 1.0) * (1<<deviation_e) / (1<<17))
    msg = [[0x15, ((deviation_e & 0x07)<<4) + (deviation_m & 0x07)]]
    write_register_RX(spi, CS, msg)
    if (config_prints):
        print(f"set RX f_dev: [{deviation_e} {deviation_m}] {f_dev_calculated}")
        print("\nset_frequency_deviation RX")
        print([f"0x{byte:02X}" for pair in msg for byte in pair])
        print(msg)

def set_frequency_RX(spi, CS, frequency):
    write_strobe_RX(spi, CS, SIDLE)
    freq = int(frequency * ((1<<16) / F_XOSC))
    channel = 0
    channspc_e = 0
    channspc_m = int(((frequency * (1 << 16)) / F_XOSC - freq - (1 << 6)) * (1 << 2))
    frequency_calculated = int(F_XOSC * (freq + channel * (256 + channspc_m) / (1 << 2)) / (1 << 16))
    #
    mdmcfg1 = read_register_RX(spi, CS, 0x13)[0];
    msg = [[0x0a, channel],
           [0x0d, ((freq & 0x007f0000)>>16)],
           [0x0e, ((freq & 0x0000ff00)>>8)],
           [0x0f, (freq & 0x000000ff) - 1],
           [0x13, (mdmcfg1 & 0xf0) + (channspc_e & 0X03) + 32],
           [0x14, (channspc_m)]]
    write_register_RX(spi, CS, msg)
    if (config_prints):
        print(f"set RX frequency [{freq} {channel} {channspc_e} {channspc_m}] {frequency_calculated}")
        print("\nset_frequency RX")
        print([f"0x{byte:02X}" for pair in msg for byte in pair])
        print(msg)

def bytes_to_utf8_string(byte_data):
    utf8_string = ""
    i = 0
    while i < len(byte_data):
        byte = byte_data[i]
        if byte <= 0x7F:
            utf8_string += chr(byte)
            i += 1
        elif 0xC0 <= byte <= 0xDF and i + 1 < len(byte_data) and 0x80 <= byte_data[i+1] <= 0xBF:
            utf8_string += chr((byte & 0x1F) << 6 | (byte_data[i+1] & 0x3F))
            i += 2
        elif 0xE0 <= byte <= 0xEF and i + 2 < len(byte_data) and all(0x80 <= byte_data[i+j] <= 0xBF for j in range(1, 3)):
            utf8_string += chr((byte & 0x0F) << 12 | (byte_data[i+1] & 0x3F) << 6 | (byte_data[i+2] & 0x3F))
            i += 3
        elif 0xF0 <= byte <= 0xF7 and i + 3 < len(byte_data) and all(0x80 <= byte_data[i+j] <= 0xBF for j in range(1, 4)):
            utf8_string += chr((byte & 0x07) << 18 | (byte_data[i+1] & 0x3F) << 12 | (byte_data[i+2] & 0x3F) << 6 | (byte_data[i+3] & 0x3F))
            i += 4
        else:
            i += 1
    return utf8_string

    
def decode_packet_RX(spi,CS,RX_BUFFER_SIZE,message):
    CS.value(0)
    tmp_buf = spi.read(2,0xFB)
    CS.value(1)
    message.overflow = bool(tmp_buf[1] & 0x80)
    if(not message.overflow):
        size = (tmp_buf[1] & 0x7F) - 2
        CS.value(0)
        tmp_buf = spi.read(1,0xFF)
        #buf = spi.read(min(min(size,62),RX_BUFFER_SIZE),0xFF)
        buf = spi.read(62,0xFF)
        tmp_buf = spi.read(2,0xFF)
        CS.value(1)
        
        #Fill the message Class
        message.CRC_check = bool(tmp_buf[1] & 0x80)
        message.link_quality_indicator = (tmp_buf[1] & 0X7F)
        
        if(buf[0] >= 128):
            message.RSSI = (tmp_buf[0] - 256)/2 - 70
        else:
            message.RSSI = (tmp_buf[0])/2 - 70
            
        message.length = int(buf[0]) 
        message.sequence = int(buf[1])
        message.data = bytes_to_utf8_string(buf[2:message.length + 1])
    return(message)

#-------------- SPI functions --------------

def write_strobe_RX(spi, CS, data):
    msg = bytearray()
    msg.append(data)
    CS.value(0)
    spi.write(msg)
    CS.value(1)

def write_register_RX(spi, CS, data):
    msg = bytearray()
    CS.value(0)
    for i in range(len(data)):
        msg.append(data[i][0])
        msg.append(data[i][1])
        spi.write(msg)
        msg = bytearray()
    CS.value(1)

def read_register_RX(spi, CS, address):
    CS.value(0)
    buf = spi.read(2,address + 0x80)
    CS.value(1)
    time.sleep_ms(1)
    msg = [b for b in buf]
    return (msg)
        
def start_listen_RX(spi, CS):
    write_strobe_RX(spi, CS, SIDLE)
    msg = [[0x17, 0x00]]   #after receiving a packet, return to idle
    write_register_RX(spi, CS, msg)
    write_strobe_RX(spi, CS, SFRX)
    write_strobe_RX(spi, CS, SRX)
    
def stop_listen_RX(spi, CS):
    write_strobe_RX(spi, CS, SIDLE)

def print_RX(message):
    if not(message.CRC or message.overflow):
        print(message.length,end=" | ")
        print(message.sequence,end=" | ")
        print(message.data,end=" | ")
        print(message.RSSI)

#-------------- debug functions --------------
    
def test_RW(spi, CS):
    write_strobe_RX(spi, CS, SIDLE)
    buf_TX = [[0x10, 0x00]]
    write_register_RX(spi, CS, buf_TX)
    buf_RX = read_register_RX(spi, CS, buf_TX[0][0])
    print("\n==== TEST RW ====")
    print("\nInitial values (TX then RX)")
    print([f"0x{byte:02X}" for byte in buf_TX[0]])
    print([f"0x{byte:02X}" for byte in buf_RX])
    buf_TX = [[0x10, 0x0B]]
    write_register_RX(spi, CS, buf_TX)
    buf_RX = read_register_RX(spi, CS, buf_TX[0][0])
    print("\nAfter Change values (TX then RX)")
    print([f"0x{byte:02X}" for byte in buf_TX[0]])
    print([f"0x{byte:02X}" for byte in buf_RX])

def print_registers_RX(spi, CS):
    buf = bytearray(2)
    for r in range(0x00, 0x2F):  # Range from 0x00 to 0x2E
        CS.value(0)
        buf = spi.read(2,r + 0x80)
        CS.value(1)
        time.sleep_ms(1)
        print(f"{{.address = 0x{r:02X}, .value = 0x{buf[1]:02X}}},")
        
def dummy_event_update(timer):
    global event_RX
    event_RX = "reception"

def dummy_message_generator():
    tim = Timer()
    tim.init(mode=Timer.PERIODIC, callback=dummy_event_update, period=4000)
    