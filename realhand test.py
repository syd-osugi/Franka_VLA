from RealHand.real_hand_api import RealHandApi
from RealHand.utils.load_write_yaml import LoadWriteYaml
# def main():
#     # Initialize API. hand_type: left or right. hand_joint: L7, L10, L20, or L25
#     real_hand = RealHandApi(hand_type="right", hand_joint="L6")
#     # Set finger speed
#     real_hand.set_speed(speed=[120,200,200,200,200])
#     # Set hand torque
#     real_hand.set_torque(torque=[200,200,200,200,200])
#     # Get current hand state
#     hand_state = real_hand.get_state()
#     # Print state values
#     print(hand_state)

configyaml = LoadWriteYaml() # Initialize configuration file
# Read configuration file
# This line gets all info from RealHand/config/setting.yaml
setting = configyaml.load_setting_yaml()

left_hand = False
right_hand = False
if setting['REAL_HAND']['LEFT_HAND']['EXISTS'] == True:
    left_hand = True
elif setting['REAL_HAND']['RIGHT_HAND']['EXISTS'] == True:
    right_hand = True
# GUI control only supports single hand, mutual exclusion for left/right hand here
if left_hand == True and right_hand == True:
    left_hand = True
    right_hand = False
if left_hand == True:
    hand_exists = True
    hand_joint = setting['REAL_HAND']['LEFT_HAND']['JOINT']
    hand_type = "left"
    is_touch = setting['REAL_HAND']['LEFT_HAND']['TOUCH']
    can = setting['REAL_HAND']['LEFT_HAND']['CAN']
    modbus = setting['REAL_HAND']['LEFT_HAND']['MODBUS']
if right_hand == True:
    hand_exists = True
    hand_joint = setting['REAL_HAND']['RIGHT_HAND']['JOINT']
    hand_type = "right"
    is_touch = setting['REAL_HAND']['RIGHT_HAND']['TOUCH']
    can = setting['REAL_HAND']['RIGHT_HAND']['CAN']
    modbus = setting['REAL_HAND']['RIGHT_HAND']['MODBUS']

# allows us to use https://github.com/realhand-dev/realhand-python-sdk/blob/main/doc/API-Reference.md
real_hand = RealHandApi(hand_joint=hand_joint, hand_type=hand_type, modbus=modbus, can=can)

# change speed of 
speed = [10, 10, 10, 10, 10, 10]
real_hand.set_speed(speed)
#get speed data
real_hand.get_speed()

# fingie torque limit
torque = [10, 10, 10, 10, 10, 10]
real_hand.set_torque(torque)
#get torque
torque_state = real_hand.get_torque()
print(f"torque state {torque_state}")

# NOT WORKING
#force = [] # [[Normal Pressure], [Tangential Pressure], [Tangential Direction], [Proximity Induction]]
force_state = real_hand.get_force()
print(f"force state {force_state}")

# send position via matrix for position
position = [250, 250, 250, 250, 250, 250]
positionone = [0, 18, 255, 0, 0, 0]
real_hand.finger_move(position)
#real_hand.finger_move(positionone)
#current state of hand postions
hand_state = real_hand.get_state()
print(f"hand state {hand_state}")

#get motor temperature of the current joints
temp_state = real_hand.get_temperature()
print(f"temp state {temp_state}")
#get motor fault codes
# 0 means normal; 1: Current Overload; 2: Over Temperature; 3: Encoding Error; 4: Over/Under Voltage.
fault_state = real_hand.get_fault()
print(f"fault state {fault_state}")




print('We made it')