import time
import ustruct as struct
 
import board
import busio
import pulseio
 
import adafruit_motor.servo

uart = busio.UART(board.TX,board.RX, baudrate = 115200)
# Initialize PWM output for the servo (on pin D5):
pwm = pulseio.PWMOut(board.D0, frequency=50)


pwmMaxDuty = 2**16
pwmPeriod_ms = 20 #milliseconds
maxCCW_ms = 0.6
center_ms = 1.15
maxCW_ms = 1.8
#pwmHigh_ms = [center_ms]
#data_string = ''
#newData = False

def main():
    EspConnect("io.adafruit.com",1883)
    MQTTConnect()
    time.sleep(.5)
    MQTTSubscribe()
    #time.sleep(5)
    #EspClose()

def EspConnect(url,port):
    uart.write(bytearray("AT+CIPMODE=0\r\n"))
    time.sleep(.2)
    uart.write(bytearray("AT+CIPSTART=\"TCP\",\""+url+"\","+str(port)+"\r\n"))
    time.sleep(.2)
    uart.write(bytearray("AT+CIPMODE=1\r\n"))
    time.sleep(.2)
    uart.write(bytearray("AT+CIPSEND\r\n"))
    time.sleep(.5)

def MQTTConnect():
    protocol_name = bytearray(b"\x00\x04MQTT")
    protocol_lvl = bytearray(b"\x04")
    user_name_flag_bit = (1<<7)
    password_flag_bit  = (1<<6)
    clean_session_bit  = (1<<1)
    connect_flags_byte = user_name_flag_bit\
                        | password_flag_bit\
                        | clean_session_bit
    connect_flags = struct.pack("!B",connect_flags_byte)
    keep_alive = struct.pack("!H",200)
    client_id = bytearray(b"thermostat_controller")
    client_id_len = struct.pack("!H",len(client_id))
    username = bytearray(b"username")
    username_len = struct.pack("!H",len(username))
    password = bytearray(b"password")
    password_len = struct.pack("!H",len(password))
    msg_part_two = protocol_name\
                    + protocol_lvl\
                    + connect_flags\
                    + keep_alive\
                    + client_id_len + client_id\
                    + username_len + username\
                    + password_len + password
    msg_part_one = struct.pack("!B",1<<4) + struct.pack("!B",len(msg_part_two))

    uart.write(msg_part_one + msg_part_two)

def MQTTDisconnect():
    msg = bytearray(2)
    msg[0] = 0xE0 #Control Packet type 14 (0xE)
    uart.write(msg)

def MQTTSubscribe():
    pid = struct.pack('!H',0xDEAD)
    var_head = pid

    topic = b"username/feeds/ac-controller.button"
    topic_len = struct.pack("!H",len(topic))
    qos = struct.pack('!B',0x00)
    payload = topic_len + topic + qos

    ctrl_pkt = struct.pack('!B',0x82)
    remain_len = struct.pack('!B',len(var_head)+len(payload))
    fix_head = ctrl_pkt + remain_len

    msg = fix_head + var_head + payload
    uart.write(msg)

def MQTTPublish(val):

    topic = b"username/feeds/ac-controller.button"
    topic_len = struct.pack("!H",len(topic))
    msg_part_two = topic_len+topic+bytearray(val)
    msg_part_one = struct.pack("!B",0x30) + struct.pack("!B",len(msg_part_two))
    print(msg_part_one+msg_part_two)

    uart.write(msg_part_one + msg_part_two)

def MapVal(val,minIn,maxIn,minOut,maxOut):
    return ((val-minIn)/(maxIn-minIn)) * (maxOut-minOut) + minOut

def MQTTRecv():
    print(uart.read()) #clear buffer
    while True:
        data =  uart.read(1)
        if data is not None and data[0] == 0x30:
            remain_len = uart.read(1)[0]
            data = uart.read(remain_len)
            topic_len = data[0]*256 + data[1]
            payload_start = 2+topic_len

            topic = ''.join([chr(b) for b in data[2:payload_start]])
            print(topic)

            payload = int(data[payload_start:remain_len])
            print(payload)
            if(payload <= 80 and payload >=65):
                highms = MapVal(payload,65,80,maxCCW_ms,maxCW_ms)
                print(highms)
                pwm.duty_cycle = int(pwmMaxDuty * highms / pwmPeriod_ms)

def EspPOST(val):
    post = "POST /api/v2/username/feeds/feed_name/data HTTP/1.1\r\n"
    host = "Host: io.adafruit.com\r\n"
    key = "X-AIO-Key: put_key_here\r\n"
    body = "value="+str(val)
    contentLen = "Content-Length: "+str(len(bytearray(body)))+"\r\n"
    contentType = "Content-Type: application/x-www-form-urlencoded\r\n"
    postArray = bytearray(post+host+key+contentLen+contentType+"\r\n"+body)

    uart.write(postArray)

def EspClose():
    uart.write(bytearray("+++"))
    time.sleep(1)
    uart.write(bytearray("AT+CIPCLOSE\r\n"))
    time.sleep(.2)
    uart.write(bytearray("AT+CIPMODE=0\r\n"))

if __name__ == '__main__':
    main()
    MQTTDisconnect()
    EspClose()
 

