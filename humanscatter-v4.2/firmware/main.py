import time
import machine
from machine import Pin, SPI

# ====================== SAFE IMPORTS ======================
try:
    from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY, PEN_P4
except ImportError:
    print("[ERROR] PicoGraphics module not found! Check your UF2 firmware.")
    PicoGraphics = None

try:
    import carrier
    import receiver
    import display
except Exception as e:
    print("[ERROR] Failed to import local modules:", e)
    carrier = None
    receiver = None
    display = None

# ====================== BOOT DELAY ======================
print("[DEBUG] Waiting 3s before starting...")
time.sleep(3)

# ====================== PINS ======================
LED_CARRIER_PIN = 1   # GPIO1 → Carrier active LED
LED_MESSAGE_PIN = 0   # GPIO0 → Message received LED

RX_SCK = 10
RX_MISO = 8
RX_MOSI = 11
CS_RX_PIN = 22
GDO0_PIN = 2
GD2_PIN = 3   # optional

carrier_timeout = 20  # seconds

# ====================== LED SETUP ======================
try:
    LED_CARRIER = Pin(LED_CARRIER_PIN, Pin.OUT)
    LED_MESSAGE = Pin(LED_MESSAGE_PIN, Pin.OUT)

    # Reset LEDs
    LED_CARRIER.value(0)
    LED_MESSAGE.value(0)

    print("[DEBUG] LEDs initialized successfully!")

    # Test LEDs separately at boot
    print("[DEBUG] Testing LEDs...")
    LED_CARRIER.value(1)
    time.sleep(0.3)
    LED_CARRIER.value(0)
    time.sleep(0.2)
    LED_MESSAGE.value(1)
    time.sleep(0.3)
    LED_MESSAGE.value(0)
    print("[DEBUG] LED test complete!")

except Exception as e:
    print("[ERROR] Failed to initialize LEDs:", e)

# ====================== VBUS / POWER DETECTION ======================
VBUS_PIN = 24   # Physical pin 40 → VBUS sense
try:
    VBUS = machine.Pin(VBUS_PIN, machine.Pin.IN)
except:
    VBUS = None
    print("[WARN] VBUS pin not available!")

def is_usb_powered():
    if VBUS is None:
        return False
    return VBUS.value() == 1

# ====================== POWER LED INDICATOR ======================
try:
    if is_usb_powered():
        print("[DEBUG] USB power detected → Turning GPIO0 LED ON")
        LED_MESSAGE.value(1)
    else:
        print("[DEBUG] VSYS (external) power detected → Turning GPIO0 LED ON")
        LED_MESSAGE.value(1)
except Exception as e:
    print("[ERROR] Failed to set power LED:", e)


# ====================== DISPLAY SETUP ======================
display_humanscatter = None
color = None

if display and PicoGraphics:
    try:
        print("[DEBUG] Initializing Pico Display...")
        display_humanscatter, color = display.setup_screen()
        print("[DEBUG] Pico Display initialized successfully!")
    except Exception as e:
        print("[ERROR] Failed to initialize display:", e)
else:
    print("[WARN] Skipping display setup — PicoGraphics or display.py missing!")

# ====================== SPI RECEIVER SETUP ======================
radio = None
CS_RX = None
try:
    print("[DEBUG] Setting up SPI for CC2500 receiver...")
    radio = SPI(
        1,
        baudrate=5_000_000,
        polarity=0,
        phase=0,
        bits=8,
        firstbit=SPI.MSB,
        sck=Pin(RX_SCK),
        mosi=Pin(RX_MOSI),
        miso=Pin(RX_MISO)
    )
    CS_RX = Pin(CS_RX_PIN, Pin.OUT)
    print("[DEBUG] SPI configured successfully!")
except Exception as e:
    print("[ERROR] Failed to configure SPI:", e)

# ====================== CARRIER SETUP ======================
if carrier:
    try:
        print("[DEBUG] Setting up ADF4351 carrier...")
        carrier.setup_TX()
        print("[DEBUG] ADF4351 setup complete!")
    except Exception as e:
        print("[ERROR] Carrier setup failed:", e)

# ====================== RECEIVER SETUP ======================
if receiver and radio and CS_RX:
    try:
        print("[DEBUG] Setting up CC2500 receiver...")
        receiver.setup_RX(radio, CS_RX, GDO0_PIN)
        print("[DEBUG] CC2500 receiver setup complete!")
    except Exception as e:
        print("[ERROR] Receiver setup failed:", e)

time.sleep_us(100)

# ====================== START CARRIER ======================
if carrier:
    try:
        print("[DEBUG] Starting carrier TX...")
        carrier.start_carrier_TX()
        LED_CARRIER.value(1)  # Turn carrier LED ON
        print("[DEBUG] Carrier started successfully!")
    except Exception as e:
        print("[ERROR] Failed to start carrier:", e)

# ====================== START RECEIVER ======================
if receiver and radio and CS_RX:
    try:
        print("[DEBUG] Starting receiver listening mode...")
        receiver.start_listen_RX(radio, CS_RX)
        receiver.event_RX = "no_reception"
        print("[DEBUG] Receiver listening mode active!")
    except Exception as e:
        print("[ERROR] Failed to start receiver:", e)

# ====================== INITIAL EVENTS ======================
if receiver and carrier:
    receiver.event_RX = "no_reception"
    carrier.event_TX = "no_timeout"
    print(f"[DEBUG] Initial RX event: {receiver.event_RX}")
    print(f"[DEBUG] Initial TX event: {carrier.event_TX}")

# ====================== MAIN LOOP ======================
cnt = 1
cnt2 = 0

if receiver and carrier:
    try:
        receiver.dummy_message_generator()
        carrier.carrier_timer(carrier_timeout)
    except Exception as e:
        print("[ERROR] Failed to start timers:", e)

print("[DEBUG] Entering main loop...")

try:
    while True:
        # If receiver got a message
        if receiver and receiver.event_RX == "reception":
            try:
                print("[DEBUG] Message received!")
                message = receiver.decode_packet_RX(
                    radio, CS_RX, receiver.RX_BUFFER_SIZE, receiver.Message()
                )

                # Blink message LED when message is received
                LED_MESSAGE.value(1)
                time.sleep_ms(100)
                LED_MESSAGE.value(0)

                # Demo messages
                if cnt2 == 0:
                    message.data = "Hello je backscatte comment ça va le sang"
                    message.RSSI += 5
                elif cnt2 == 1:
                    message.data = "Salut je suis Amaury, étudiant à RISE"
                    message.RSSI += 3
                elif cnt2 == 2:
                    message.data = "J'adore la Suède, super pays!"
                    message.RSSI += 8

                cnt2 = (cnt2 + 1) % 3

                receiver.print_RX(message)

                if display_humanscatter:
                    display.print_msg(display_humanscatter, message, color)

                time.sleep_ms(2000)
                receiver.start_listen_RX(radio, CS_RX)
                receiver.event_RX = "no_reception"
                cnt = 1
            except Exception as e:
                print("[ERROR] Failed during reception:", e)

        # If no messages yet
        elif receiver and receiver.event_RX == "no_reception":
            if cnt:
                print("[DEBUG] Waiting for messages...")
                if display_humanscatter:
                    display.print_waiting(display_humanscatter, "WAITING", color)
                cnt = 0

        # Carrier timeout
        elif carrier and carrier.event_TX == "timeout":
            print("[DEBUG] Carrier timeout! Stopping...")
            carrier.stop_carrier_TX()
            LED_CARRIER.value(0)  # Turn carrier LED OFF
            if display_humanscatter:
                display.print_carrier_timeout(display_humanscatter, color)
            break

        time.sleep(0.05)

except Exception as e:
    print("[FATAL] Crash in main loop:", e)
    print("[INFO] Entering safe idle mode...")
    while True:
        time.sleep(1)  # Keep USB REPL alive
