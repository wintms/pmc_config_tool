#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Union
import os
import sys


class PMCDeviceConfig:
    def __init__(self, pmc_file: str):
        """
        Initialize PMC device configuration parser

        Args:
            pmc_file: Path to the PMC file
        """
        self.pmc_file = pmc_file
        self.tree = None
        self.root = None
        self.load_file()

    def load_file(self):
        """Load and parse the PMC XML file"""
        try:
            self.tree = ET.parse(self.pmc_file)
            self.root = self.tree.getroot()
        except FileNotFoundError:
            print(f"Error: File '{self.pmc_file}' not found")
            sys.exit(1)
        except ET.ParseError as e:
            print(f"Error: Failed to parse XML file: {e}")
            sys.exit(1)

    def get_device_by_name(self, name: str) -> Optional[ET.Element]:
        """
        Find device by name (using <name> tag)

        Args:
            name: Device name to search for

        Returns:
            Device Element if found, None otherwise
        """
        for device in self.root.findall('.//device'):
            name_elem = device.find('name')
            if name_elem is not None and name_elem.text == name:
                return device
        return None

    def get_device_config(self, dev_name: str) -> Dict[str, str]:
        """
        Get all configuration variables for a device (including SDR configs)

        Args:
            dev_name: Device name

        Returns:
            Dictionary mapping variable names to values
        """
        device = self.get_device_by_name(dev_name)
        if device is None:
            return {}

        config = {}

        # Get device-level configs
        for config_elem in device.findall('config'):
            variable = config_elem.find('variable')
            value = config_elem.find('value')
            if variable is not None and value is not None:
                config[variable.text] = value.text

        # Get SDR configs
        sdr = device.find('sdr')
        if sdr is not None:
            for config_elem in sdr.findall('config'):
                variable = config_elem.find('variable')
                value = config_elem.find('value')
                if variable is not None and value is not None:
                    config[f"SDR_{variable.text}"] = value.text

        return config

    def convert_raw_to_real(self, dev_name: str, raw_value: Union[str, int, float], print_calculation: bool = False) -> Optional[float]:
        """
        Convert raw value to real value using M_VAL and R_EXP from any config

        Formula: real_value = (M_VAL * raw_value) * 10^(R_EXP)

        Args:
            dev_name: Device name
            raw_value: Raw value to convert
            print_calculation: Whether to print the calculation steps

        Returns:
            Real value if conversion successful, None otherwise
        """
        device = self.get_device_by_name(dev_name)
        if device is None:
            return None

        # Get M_VAL and R_EXP from any config (device or SDR)
        m_val_str, r_exp_str = self.get_mval_rexp_from_anywhere(dev_name)

        if m_val_str is None or r_exp_str is None:
            print(f"Error: Config conversion requires M_VAL and R_EXP but they are not found in device or SDR config for device '{dev_name}'")
            return None

        try:
            # Convert hex strings if needed
            m_val = int(m_val_str, 16) if m_val_str.startswith(('0x', '0X')) else int(m_val_str)
            # Parse R_EXP with base 10 to support negative values like -3
            r_exp = int(r_exp_str, 16) if r_exp_str.startswith(('0x', '0X')) else int(r_exp_str, 10)
            raw_val_str = raw_value.decode() if isinstance(raw_value, bytes) else str(raw_value)
            raw_val = float(int(raw_val_str, 16) if raw_val_str.startswith(('0x', '0X')) else float(raw_val_str))

            # Formula: real_value = (M_VAL * raw_value) * 10^(R_EXP)
            real_value = (m_val * raw_val) * (10 ** r_exp)

            if print_calculation:
                print(f"Calculation: ({m_val} * {raw_val}) * 10^({r_exp}) = {real_value}")

            return real_value
        except (ValueError, TypeError, OverflowError) as e:
            print(f"Error: Failed to convert raw value - {e}")
            return None

    def convert_real_to_raw(self, dev_name: str, real_value: Union[str, int, float], print_calculation: bool = False) -> Optional[int]:
        """
        Convert real value to raw value using M_VAL and R_EXP from any config

        Formula: raw_value = real_value / (M_VAL * 10^(R_EXP))

        Args:
            dev_name: Device name
            real_value: Real value to convert
            print_calculation: Whether to print the calculation steps

        Returns:
            Raw value (rounded to nearest integer) if conversion successful, None otherwise
        """
        device = self.get_device_by_name(dev_name)
        if device is None:
            return None

        # Get M_VAL and R_EXP from any config (device or SDR)
        m_val_str, r_exp_str = self.get_mval_rexp_from_anywhere(dev_name)

        if m_val_str is None or r_exp_str is None:
            print(f"Error: Config conversion requires M_VAL and R_EXP but they are not found in device or SDR config for device '{dev_name}'")
            return None

        try:
            # Convert hex strings if needed
            m_val = int(m_val_str, 16) if m_val_str.startswith(('0x', '0X')) else int(m_val_str)
            # Parse R_EXP with base 10 to support negative values like -3
            r_exp = int(r_exp_str, 16) if r_exp_str.startswith(('0x', '0X')) else int(r_exp_str, 10)
            real_val_str = real_value.decode() if isinstance(real_value, bytes) else str(real_value)
            real_val = float(real_val_str)

            # Formula: raw_value = real_value / (M_VAL * 10^(R_EXP))
            denominator = m_val * (10 ** r_exp)
            if denominator == 0:
                print("Error: Cannot divide by zero (M_VAL is 0)")
                return None

            raw_value = real_val / denominator
            raw_int = round(raw_value)

            if print_calculation:
                print(f"Calculation: {real_val} / ({m_val} * 10^({r_exp})) = {raw_value} ≈ {raw_int}")

            return raw_int
        except (ValueError, TypeError, OverflowError) as e:
            print(f"Error: Failed to convert real value - {e}")
            return None

    def get_mval_rexp_from_anywhere(self, dev_name: str):
        """
        Get M_VAL and R_EXP from device config or SDR config

        Args:
            dev_name: Device name

        Returns:
            Tuple of (M_VAL, R_EXP) or (None, None) if not found
        """
        device = self.get_device_by_name(dev_name)
        if device is None:
            return None, None

        # First try device config
        m_val_device = None
        r_exp_device = None

        for config_elem in device.findall('config'):
            var_elem = config_elem.find('variable')
            val_elem = config_elem.find('value')
            if var_elem is not None and val_elem is not None:
                if var_elem.text == 'M_VAL':
                    m_val_device = val_elem.text
                elif var_elem.text == 'R_EXP':
                    r_exp_device = val_elem.text

        if m_val_device is not None and r_exp_device is not None:
            return m_val_device, r_exp_device

        # If not found in device config, try SDR config
        return self.get_sdr_config_value(dev_name, 'M_VAL'), self.get_sdr_config_value(dev_name, 'R_EXP')

    def get_config_value(self, dev_name: str, variable: str) -> Optional[str]:
        """
        Get specific configuration value for a device

        Args:
            dev_name: Device name
            variable: Configuration variable name (use SDR_ prefix for SDR configs, or search both)

        Returns:
            Value if found, None otherwise
        """
        device = self.get_device_by_name(dev_name)
        if device is None:
            return None

        # Check if it's an SDR config (starts with SDR_)
        if variable.startswith('SDR_'):
            sdr_var = variable[4:]  # Remove SDR_ prefix
            sdr = device.find('sdr')
            if sdr is not None:
                for config_elem in sdr.findall('config'):
                    var_elem = config_elem.find('variable')
                    val_elem = config_elem.find('value')
                    if var_elem is not None and var_elem.text == sdr_var:
                        # Return value as-is without formatting to preserve original format
                        return val_elem.text if val_elem is not None else None
        else:
            # Regular device config - search device config first
            for config_elem in device.findall('config'):
                var_elem = config_elem.find('variable')
                val_elem = config_elem.find('value')
                if var_elem is not None and var_elem.text == variable:
                    # Return value as-is without formatting to preserve original format
                    return val_elem.text if val_elem is not None else None

            # If not found in device config, search SDR config
            sdr = device.find('sdr')
            if sdr is not None:
                for config_elem in sdr.findall('config'):
                    var_elem = config_elem.find('variable')
                    val_elem = config_elem.find('value')
                    if var_elem is not None and var_elem.text == variable:
                        # Return value as-is without formatting to preserve original format
                        return val_elem.text if val_elem is not None else None

        return None

    def get_sdr_config_value(self, dev_name: str, variable: str) -> Optional[str]:
        """
        Get specific SDR configuration value for a device

        Args:
            dev_name: Device name
            variable: SDR variable name

        Returns:
            Value if found, None otherwise
        """
        device = self.get_device_by_name(dev_name)
        if device is None:
            return None

        sdr = device.find('sdr')
        if sdr is None:
            return None

        for config_elem in sdr.findall('config'):
            var_elem = config_elem.find('variable')
            val_elem = config_elem.find('value')
            if var_elem is not None and var_elem.text == variable:
                return val_elem.text if val_elem is not None else None

        return None

    def set_config_value(self, dev_name: str, variable: str, new_value: str) -> bool:
        """
        Set a configuration value for a device

        Args:
            dev_name: Device name
            variable: Configuration variable name (use SDR_ prefix for SDR configs, or search both)
            new_value: New value to set

        Returns:
            True if successful, False otherwise
        """
        device = self.get_device_by_name(dev_name)
        if device is None:
            print(f"Error: Device '{dev_name}' not found")
            return False

        # Check if it's an SDR config (starts with SDR_)
        if variable.startswith('SDR_'):
            sdr_var = variable[4:]  # Remove SDR_ prefix
            sdr = device.find('sdr')
            if sdr is None:
                print(f"Error: Device '{dev_name}' has no SDR section")
                return False

            # Find existing SDR config
            for config_elem in sdr.findall('config'):
                var_elem = config_elem.find('variable')
                val_elem = config_elem.find('value')
                if var_elem is not None and var_elem.text == sdr_var:
                    if val_elem is not None:
                        val_elem.text = new_value
                        print(f"Updated SDR config {sdr_var} to {new_value}")
                        return True

            print(f"Error: SDR config '{sdr_var}' not found in device '{dev_name}'")
            return False

        else:
            # Regular device config - search device config first
            for config_elem in device.findall('config'):
                var_elem = config_elem.find('variable')
                val_elem = config_elem.find('value')
                if var_elem is not None and var_elem.text == variable:
                    if val_elem is not None:
                        val_elem.text = new_value
                        print(f"Updated {variable} to {new_value}")
                        return True

            # If not found in device config, search SDR config
            sdr = device.find('sdr')
            if sdr is not None:
                for config_elem in sdr.findall('config'):
                    var_elem = config_elem.find('variable')
                    val_elem = config_elem.find('value')
                    if var_elem is not None and var_elem.text == variable:
                        if val_elem is not None:
                            val_elem.text = new_value
                            print(f"Updated SDR config {var_elem.text} to {new_value}")
                            return True

            # If config doesn't exist, create new one in device config
            config = ET.SubElement(device, 'config')
            var_elem = ET.SubElement(config, 'variable')
            var_elem.text = variable
            val_elem = ET.SubElement(config, 'value')
            val_elem.text = new_value
            print(f"Added new config {variable} = {new_value}")
            return True

    def interactive_set_thresholds(self, dev_name: str, threshold_params: set) -> Dict[str, str]:
        """
        Interactive mode to set all threshold parameters

        Args:
            dev_name: Device name
            threshold_params: Set of threshold parameter names

        Returns:
            Dictionary of changes made (variable -> value)
        """
        print(f"\n{'='*60}")
        print(f"Interactive Threshold Configuration for: {dev_name}")
        print(f"{'='*60}")
        print("Press Enter to keep current value, or enter a new value.")
        print("For threshold parameters, enter the REAL value (e.g., 12.5 for voltage)")
        print("-" * 60)

        changes = {}

        # Get current device info to display
        device = self.get_device_by_name(dev_name)
        if device is None:
            print(f"Error: Device '{dev_name}' not found")
            return changes

        sdr = device.find('sdr')
        if sdr is None:
            print(f"Error: Device '{dev_name}' has no SDR section")
            return changes

        # First, display current values with real values aligned
        print("\nCurrent threshold values:")
        print("-" * 40)

        current_values = {}
        for config_elem in sdr.findall('config'):
            variable = config_elem.find('variable')
            value = config_elem.find('value')
            if variable is not None and value is not None:
                var_name = variable.text
                val_str = value.text

                if var_name in threshold_params:
                    current_values[var_name] = val_str
                    # Display current value with real value if possible
                    base_str = f"  {var_name}: {val_str}"
                    real_val = None
                    if self.get_mval_rexp_from_anywhere(dev_name)[0] is not None:
                        real_val = self.convert_raw_to_real(dev_name, val_str, print_calculation=False)

                    if real_val is not None:
                        padding = max(1, 32 - len(base_str))
                        print(f"{base_str}{' '*padding}({real_val})")
                    else:
                        print(base_str)

        print("\n" + "-" * 60)
        print("Enter new values (or press Enter to skip):")
        print("-" * 60)

        # Process each threshold parameter in specific order
        # Order: lower thresholds first, then upper thresholds, then nominal
        ordered_params = [
            'LOWER_NON_RECOVERABLE',
            'LOWER_CRITICAL',
            'LOWER_NON_CRITICAL',
            'UPPER_NON_CRITICAL',
            'UPPER_CRITICAL',
            'UPPER_NON_RECOVERABLE',
            'SEN_MIN',
            'SEN_MAX',
            'NOMINAL_MIN',
            'NOMINAL_MAX'
        ]

        for param in ordered_params:
            if param not in current_values:
                continue

            current_val = current_values[param]
            current_real = None
            if self.get_mval_rexp_from_anywhere(dev_name)[0] is not None:
                current_real = self.convert_raw_to_real(dev_name, current_val, print_calculation=False)

            # Prompt user
            if current_real is not None:
                prompt = f"{param} [current: {current_real}]: "
            else:
                prompt = f"{param} [current: {current_val}]: "

            user_input = input(prompt).strip()

            # Skip if user pressed Enter
            if user_input == "":
                continue

            # Convert and set the new value
            try:
                if current_real is not None:
                    # Convert from real value to raw
                    raw_val = self.convert_real_to_raw(dev_name, user_input, print_calculation=False)
                    if raw_val is not None:
                        new_value = f"0x{raw_val:x}"
                        print(f"  -> Converting {user_input} to {new_value}")
                        changes[param] = new_value
                    else:
                        print(f"  -> Error: Failed to convert {user_input}. Skipping.")
                else:
                    # No conversion available, use as-is
                    changes[param] = user_input
            except Exception as e:
                print(f"  -> Error: {e}. Skipping.")

        # After all thresholds, prompt for mask values
        print("\n" + "-" * 60)
        print("Now configuring mask values (or press Enter to skip):")
        print("-" * 60)

        mask_params = ['LWR_T_MASK', 'UPR_T_MASK', 'S_R_T_MASK']
        for mask_param in mask_params:
            current_mask = self.get_sdr_config_value(dev_name, mask_param)
            if current_mask is None:
                current_mask = "Not set"

            mask_prompt = f"{mask_param} (Lower Threshold Reading Mask) [current: {current_mask}]: "
            if mask_param == 'UPR_T_MASK':
                mask_prompt = f"{mask_param} (Upper Threshold Reading Mask) [current: {current_mask}]: "
            elif mask_param == 'S_R_T_MASK':
                mask_prompt = f"{mask_param} (Settable/Readable Threshold Mask) [current: {current_mask}]: "

            mask_input = input(mask_prompt).strip()

            if mask_input != "":
                changes[mask_param] = mask_input

        return changes

    def save_file(self, backup: bool = True):
        """
        Save changes back to the PMC file

        Args:
            backup: Create a backup of the original file
        """
        if backup:
            backup_file = f"{self.pmc_file}.backup"
            os.replace(self.pmc_file, backup_file)
            print(f"Backup created: {backup_file}")

        try:
            self.tree.write(self.pmc_file, encoding='utf-8', xml_declaration=True)
            print(f"Changes saved to: {self.pmc_file}")
        except Exception as e:
            print(f"Error saving file: {e}")
            return False
        return True

    def list_all_devices(self) -> List[Dict[str, str]]:
        """
        List all devices in the PMC file

        Returns:
            List of dictionaries containing device information
        """
        devices = []
        for device in self.root.findall('.//device'):
            dev_name_elem = device.find('dev_name')
            dev_class_elem = device.find('dev_class')
            name_elem = device.find('name')

            dev_info = {
                'name': name_elem.text if name_elem is not None else 'N/A',
                'dev_class': dev_class_elem.text if dev_class_elem is not None else 'N/A',
                'dev_name': dev_name_elem.text if dev_name_elem is not None else 'N/A'
            }
            devices.append(dev_info)

        return devices

    def print_device_info(self, dev_name: str):
        """Print all information about a device"""
        device = self.get_device_by_name(dev_name)
        if device is None:
            print(f"Device '{dev_name}' not found")
            return

        print(f"\nDevice: {dev_name}")
        print("=" * 50)

        # Basic info
        dev_class = device.find('dev_class')
        name = device.find('name')
        dev_name_elem = device.find('dev_name')
        if dev_class is not None:
            print(f"Class: {dev_class.text}")
        if name is not None:
            print(f"Name: {name.text}")
        if dev_name_elem is not None:
            print(f"Dev Name: {dev_name_elem.text}")

        # SDR info
        sdr = device.find('sdr')
        if sdr is not None:
            sdr_name = sdr.find('name')
            if sdr_name is not None:
                print(f"SDR Name: {sdr_name.text}")

        # Device Glyph info
        device_glyph = device.find('device_glyph')
        if device_glyph is not None:
            topleft_x = device_glyph.find('topleft_x')
            topleft_y = device_glyph.find('topleft_y')
            width = device_glyph.find('width')
            height = device_glyph.find('height')
            print(f"Device Glyph:")
            if topleft_x is not None:
                print(f"  Top Left X: {topleft_x.text}")
            if topleft_y is not None:
                print(f"  Top Left Y: {topleft_y.text}")
            if width is not None:
                print(f"  Width: {width.text}")
            if height is not None:
                print(f"  Height: {height.text}")

        print("\n")

        # Device Configurations
        print("Configurations:")
        print("-" * 30)
        for config_elem in device.findall('config'):
            variable = config_elem.find('variable')
            value = config_elem.find('value')
            if variable is not None and value is not None:
                print(f"  {variable.text}: {value.text}")

        # SDR Configurations
        if sdr is not None:
            print("\nSDR:")
            print("-" * 30)

            # Threshold parameters that need Real value conversion
            threshold_vars = {
                'NOMINAL_READING', 'NOMINAL_MAX', 'NOMINAL_MIN',
                'SEN_MAX', 'SEN_MIN',
                'UPPER_NON_RECOVERABLE', 'UPPER_CRITICAL', 'UPPER_NON_CRITICAL',
                'LOWER_NON_RECOVERABLE', 'LOWER_CRITICAL', 'LOWER_NON_CRITICAL'
            }

            # First pass: collect all configs and calculate max length for alignment
            configs = []
            max_val_len = 0

            for config_elem in sdr.findall('config'):
                variable = config_elem.find('variable')
                value = config_elem.find('value')
                if variable is not None and value is not None:
                    var_name = variable.text
                    val_str = value.text
                    # Calculate max length for value alignment
                    max_val_len = max(max_val_len, len(val_str))
                    configs.append((var_name, val_str))

            # Second pass: print with aligned real values
            m_val_str, r_exp_str = self.get_mval_rexp_from_anywhere(dev_name)
            has_conversion = (m_val_str is not None and r_exp_str is not None)

            for var_name, val_str in configs:
                # Check if this is a threshold parameter that needs Real value
                if var_name in threshold_vars and has_conversion:
                    # Convert to real value
                    real_val = self.convert_raw_to_real(dev_name, val_str, print_calculation=False)
                    if real_val is not None:
                        # Build base string (variable name and value)
                        base_str = f"  {var_name}: {val_str}"
                        # Calculate padding to align real values at position 32 (0-indexed)
                        padding = max(1, 32 - len(base_str))
                        print(f"{base_str}{' ' * padding}({real_val})")
                    else:
                        print(f"  {var_name}: {val_str}")
                else:
                    # Non-threshold config, display without Real value
                    print(f"  {var_name}: {val_str}")


def main():
    import argparse

    # Threshold parameters that need automatic Real/Raw conversion
    THRESHOLD_PARAMS = {
        'NOMINAL_READING', 'NOMINAL_MAX', 'NOMINAL_MIN',
        'SEN_MAX', 'SEN_MIN',
        'UPPER_NON_RECOVERABLE', 'UPPER_CRITICAL', 'UPPER_NON_CRITICAL',
        'LOWER_NON_RECOVERABLE', 'LOWER_CRITICAL', 'LOWER_NON_CRITICAL'
    }

    parser = argparse.ArgumentParser(description='Parse and modify PMC device configurations')
    parser.add_argument('pmc_file', help='Path to the PMC file')
    parser.add_argument('--dev', help='Device name to operate on (using <name> tag)')
    parser.add_argument('--list', action='store_true', help='List all devices')
    parser.add_argument('--get', help='Get value of a configuration variable')
    parser.add_argument('--set', nargs=2, metavar=('VARIABLE', 'VALUE'),
                        help='Set a configuration variable (VARIABLE VALUE)')
    parser.add_argument('--set-thres', action='store_true',
                        help='Interactive mode to set all threshold parameters')
    parser.add_argument('--no-backup', action='store_true', help='Do not create backup when saving')

    args = parser.parse_args()

    manager = PMCDeviceConfig(args.pmc_file)

    if args.list:
        devices = manager.list_all_devices()
        print(f"\nFound {len(devices)} devices in {args.pmc_file}")
        print("-" * 80)
        for i, device in enumerate(devices, 1):
            print(f"{i}. {device['name']}")
            print(f"   Class: {device['dev_class']}")
            print(f"   Dev Name: {device['dev_name']}")
        return

    if not args.dev:
        parser.error("--dev is required (unless using --list)")

    if args.get:
        variable = args.get
        value = manager.get_config_value(args.dev, variable)
        if value is not None:
            # Check if this is a threshold parameter that needs automatic conversion
            if variable in THRESHOLD_PARAMS:
                real_val = manager.convert_raw_to_real(args.dev, value, print_calculation=True)
                if real_val is not None:
                    # Format raw value as hex (0x) format
                    try:
                        raw_int = int(value, 16) if value.startswith(('0x', '0X')) else int(value)
                        raw_hex = f"0x{raw_int:x}"
                    except ValueError:
                        raw_hex = value

                    print(f"{variable}:")
                    print(f"  raw = {raw_hex}")
                    print(f"  real = {real_val}")
                else:
                    print(f"{variable} = {value}")
            else:
                # Non-threshold parameter, display as-is
                print(f"{variable} = {value}")
        else:
            print(f"Configuration '{variable}' not found for device '{args.dev}'")
    elif args.set:
        variable, value = args.set

        # For threshold parameters, convert real value to raw automatically
        converted_value = value
        converted_msg = ""
        if variable in THRESHOLD_PARAMS:
            raw_val = manager.convert_real_to_raw(args.dev, value, print_calculation=True)
            if raw_val is not None:
                # Format as hex (0x) format
                converted_value = f"0x{raw_val:x}"
                converted_msg = f" (converted from real value {value})"
            else:
                print(f"Error: Failed to convert real value. Aborting.")
                sys.exit(1)
        # else: no format conversion - use value as provided by user to preserve original format

        success = manager.set_config_value(args.dev, variable, converted_value)
        if success:
            print(f"Config saved successfully{converted_msg}")
            manager.save_file(backup=not args.no_backup)
    elif args.set_thres:
        # Interactive threshold configuration
        changes = manager.interactive_set_thresholds(args.dev, THRESHOLD_PARAMS)

        if changes:
            print(f"\n{'='*60}")
            print("Summary of changes to be applied:")
            print(f"{'='*60}")
            for var, val in changes.items():
                print(f"  {var}: {val}")

            confirm = input("\nApply these changes? (y/N): ").strip().lower()
            if confirm == 'y':
                # Apply all changes
                success_count = 0
                for var, val in changes.items():
                    if manager.set_config_value(args.dev, var, val):
                        success_count += 1

                if success_count == len(changes):
                    manager.save_file(backup=not args.no_backup)
                    print(f"\nSuccessfully applied {success_count} changes!")
                else:
                    print(f"\nWarning: Only {success_count}/{len(changes)} changes were applied.")
                    print("Check errors above.")
            else:
                print("\nChanges cancelled.")
        else:
            print("\nNo changes to apply.")
    else:
        manager.print_device_info(args.dev)


if __name__ == '__main__':
    main()
