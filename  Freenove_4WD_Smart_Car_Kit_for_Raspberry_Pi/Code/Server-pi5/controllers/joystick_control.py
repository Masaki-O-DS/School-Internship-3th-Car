
# controllers/joystick_control.py

import time
import sys
import pygame
from Motor import Motor
from servo import Servo
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def joystick_control():
    """
    Controls the car and Servo0 (neck) using a joystick.
    L1 Trigger (Button 4): Move Servo0 downward
    R1 Trigger (Button 5): Move Servo0 upward
    Right Stick X-axis (Axis 3): Rotate the car
    """
    try:
        # Initialize hardware components
        motor = Motor()
        servo = Servo()

        # Initialize Pygame
        pygame.init()

        # Initialize joystick
        pygame.joystick.init()

        # Get the number of connected joysticks
        joystick_count = pygame.joystick.get_count()
        logging.info(f"Number of joysticks connected: {joystick_count}")

        if joystick_count > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            logging.info(f"Joystick name: {joystick.get_name()}")
            logging.info(f"Number of axes: {joystick.get_numaxes()}")
            logging.info(f"Number of buttons: {joystick.get_numbuttons()}")
            logging.info(f"Number of hats: {joystick.get_numhats()}")
        else:
            logging.error("No joysticks connected. Exiting program.")
            pygame.quit()
            return

        # Define dead zones
        DEAD_ZONE_MOVEMENT = 0.2
        DEAD_ZONE_TURN = 0.2

        # Maximum PWM value
        MAX_PWM = 4095

        # Define servo channel
        SERVO_NECK_CHANNEL = '1'  # Servo0: neck up/down

        # Define servo angles within 0° to 180°
        SERVO_NECK_UP = 160    # Move neck up
        SERVO_NECK_DOWN = 120  # Move neck down
        SERVO_NECK_NEUTRAL = 90  # Neutral position for neck servo

        # Set servo to neutral position at start
        servo.setServoPwm(SERVO_NECK_CHANNEL, SERVO_NECK_NEUTRAL)
        logging.info("Servo0 set to neutral position.")

        # Initialize clock for FPS calculation
        clock = pygame.time.Clock()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return  # Exit loop

                elif event.type == pygame.JOYBUTTONDOWN:
                    button = event.button
                    logging.info(f"Button {button} pressed.")

                    # Xbox Controller Button Mapping
                    if button == 6:  # L2 Trigger
                        servo.setServoPwm(SERVO_NECK_CHANNEL, SERVO_NECK_DOWN)
                        logging.info(f"Servo0 moved down to {SERVO_NECK_DOWN} degrees.")
                    elif button == 7:  # R2 Trigger
                        servo.setServoPwm(SERVO_NECK_CHANNEL, SERVO_NECK_UP)
                        logging.info(f"Servo0 moved up to {SERVO_NECK_UP} degrees.")

                elif event.type == pygame.JOYBUTTONUP:
                    button = event.button
                    # Reset Servo0 to neutral when buttons are released
                    if button in [6, 7]:  # Servo0 buttons
                        servo.setServoPwm(SERVO_NECK_CHANNEL, SERVO_NECK_NEUTRAL)
                        logging.info("Servo0 reset to neutral position.")

                elif event.type == pygame.JOYHATMOTION:
                    hat = event.hat
                    value = event.value
                    logging.info(f"Hat {hat} moved. Value: {value}")

            # Get joystick axes
            left_vertical = joystick.get_axis(1)      # 左スティックY軸（前後）
            left_horizontal = joystick.get_axis(0)    # 左スティックX軸（左右）
            right_horizontal = joystick.get_axis(3)   # 右スティックX軸（旋回）

            # Display raw axis values
            raw_axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
            logging.debug(f"Raw axes: {raw_axes}")

            # Apply dead zone
            if abs(left_vertical) < DEAD_ZONE_MOVEMENT:
                left_vertical = 0
            if abs(left_horizontal) < DEAD_ZONE_MOVEMENT:
                left_horizontal = 0
            if abs(right_horizontal) < DEAD_ZONE_TURN:
                right_horizontal = 0

            # Calculate movement direction
            y = -left_vertical      # 前後の動き（反転）
            x = left_horizontal     # 左右の動き
            turn = right_horizontal # 旋回

            # Convert to PWM values (-4095 to 4095)
            duty_y = int(y * MAX_PWM)
            duty_x = int(x * MAX_PWM)
            duty_turn = int(turn * MAX_PWM * 0.5)  # 旋回の強度を調整（必要に応じて係数を変更）

            # Calculate PWM values for differential steering
            duty_front_left = duty_y + duty_x + duty_turn
            duty_front_right = duty_y - duty_x - duty_turn
            duty_back_left = duty_y + duty_x + duty_turn
            duty_back_right = duty_y - duty_x - duty_turn

            # PWM値を制限（-4095～4095）
            duty_front_left = max(min(duty_front_left, MAX_PWM), -MAX_PWM)
            duty_front_right = max(min(duty_front_right, MAX_PWM), -MAX_PWM)
            duty_back_left = max(min(duty_back_left, MAX_PWM), -MAX_PWM)
            duty_back_right = max(min(duty_back_right, MAX_PWM), -MAX_PWM)

            # Display PWM values
            logging.debug(f"PWM values - FL: {duty_front_left}, FR: {duty_front_right}, BL: {duty_back_left}, BR: {duty_back_right}")

            # Send PWM values to motors
            motor.setMotorModel(duty_front_left, duty_back_left, duty_front_right, duty_back_right)

            # Cap the frame rate to 60 FPS
            clock.tick(60)

    except KeyboardInterrupt:
        logging.info("\nExiting program.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        try:
            # Stop motors
            motor.setMotorModel(0, 0, 0, 0)
            # Reset servo to neutral position
            servo.setServoPwm(SERVO_NECK_CHANNEL, SERVO_NECK_NEUTRAL)
            logging.info("Motors stopped and Servo0 reset to neutral position.")
        except Exception as e:
            logging.error(f"Error while stopping motors or resetting servo: {e}")
        pygame.quit()