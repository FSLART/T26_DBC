import os
import re
import cantools

# Path to your DBC file
dbc_path = '/home/andre-lopes/Desktop/ros2_ws/src/can_bridge/include/T26_DBC/autonomous_t26.dbc'

# Get directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Output folder = ./msg relative to this script
output_dir = os.path.join(script_dir, "msg")
os.makedirs(output_dir, exist_ok=True)

# Load DBC
db = cantools.database.load_file(dbc_path)

def to_camel_case(name):
    """Convert string with spaces or hyphens to CamelCase."""
    parts = re.split(r'[-_\s]+', name)
    return ''.join(word.capitalize() for word in parts if word)

def sanitize_constant_name(name):
    """Sanitize the choice string to be a valid ROS 2 constant name (uppercase with underscores)."""
    # Replace non-alphanumeric characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9]', '_', name)
    # Remove duplicate underscores and strip
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized.upper()

def dbc_to_rosmsg(message):
    lines = ["std_msgs/Header header\n"]  # Always include header
    constants = []

    for signal in message.signals:
        # Determine ROS data type
        if signal.scale != 1 or signal.offset != 0:
            dtype = "float32"
        elif signal.length <= 8:
            dtype = "int8"
        elif signal.length <= 16:
            dtype = "int16"
        elif signal.length <= 32:
            dtype = "int32"
        else:
            dtype = "int64"

        # Clean up signal name for ROS compatibility (lowercase)
        name = signal.name.replace(" ", "_").replace("-", "_").lower()
        lines.append(f"{dtype} {name}")

        # If the signal has defined choices/enums, create ROS 2 constants
        if signal.choices:
            for value, choice_name in signal.choices.items():
                clean_choice = sanitize_constant_name(str(choice_name))
                # Prefix with signal name to avoid duplicate names in the same message
                constant_name = f"{name.upper()}_{clean_choice}"
                
                # ROS 2 constants cannot be floating points, so cast to int
                # Float signals typically don't have value tables anyway
                if "int" in dtype:
                    constants.append(f"{dtype} {constant_name} = {value}")

    # Append constants to the end of the message file if any exist
    if constants:
        lines.append("\n# Signal Value Constants")
        lines.extend(constants)

    return "\n".join(lines) + "\n"

# Generate one .msg per CAN message
for message in db.messages:
    # Use CamelCase for filename
    file_name = f"{to_camel_case(message.name)}.msg"
    file_path = os.path.join(output_dir, file_name)

    with open(file_path, "w") as f:
        f.write(dbc_to_rosmsg(message))
    
    print(f"✅ Generated {file_path}")

print(f"\nAll .msg files are in: {output_dir}")
