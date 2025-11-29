# PMC Configuration Manager

A Python tool for parsing and modifying PMC (Platform Management Controller) device configurations in XML format.

## Overview

`pmc_config_tool.py` provides a command-line interface to:
- List all devices in a PMC file
- View device configurations with automatic real value conversion
- Modify individual configuration parameters
- Interactively batch-configure threshold parameters
- Automatically convert between raw and real values (temperature, voltage, etc.)

## Requirements

- Python 3.6+
- xml.etree.ElementTree (built-in)

## Installation

No installation required. The script can be run directly:

```bash
chmod +x pmc_config_tool.py
```

## Usage

### Basic Syntax

```bash
./pmc_config_tool.py <pmc_file> [options]
```

### Options

- `--dev DEVICE` - Specify device name to operate on (using `<name>` tag)
- `--list` - List all devices in the PMC file
- `--get VARIABLE` - Get value of a configuration variable
- `--set VARIABLE VALUE` - Set a configuration variable
- `--set-thres` - Interactive mode to batch configure threshold parameters
- `--no-backup` - Do not create backup when saving changes

### Examples

#### 1. List All Devices

```bash
./pmc_config_tool.py archercity.pmc --list
```

Output:
```
Found 45 devices in archercity.pmc
--------------------------------------------------------------------------------
1. RR_Brd Temp 1
   Class: Sensor
   Dev Name: Temp
2. P12V_AUX
   Class: Sensor
   Dev Name: Voltage
...
```

#### 2. View Device Information

```bash
./pmc_config_tool.py archercity.pmc --dev "RR_Brd Temp 1"
```

This displays complete device information including:
- Device metadata (class, name, dev_name)
- Device configurations
- SDR configurations with automatic real value conversion

Example output with aligned real values:
```
SDR:
------------------------------
  LOWER_NON_RECOVERABLE: 0x0    (0.0)
  LOWER_CRITICAL: 0x0           (0.0)
  LOWER_NON_CRITICAL: 0x5       (5.0)
  UPPER_NON_CRITICAL: 0x20      (32.0)
  UPPER_CRITICAL: 0x28          (40.0)
  UPPER_NON_RECOVERABLE: 0x46   (70.0)
  SEN_MIN: 0x0                  (0.0)
  SEN_MAX: 0xff                 (255.0)
  NOMINAL_MIN: 0x8b             (139.0)
  NOMINAL_MAX: 0xc5             (197.0)
```

Real values are aligned at the 32nd character position for readability.

#### 3. Get a Specific Configuration Value

```bash
./pmc_config_tool.py archercity.pmc --dev "RR_Brd Temp 1" --get UPPER_CRITICAL
```

For threshold parameters, automatically shows both raw and real values:
```
UPPER_CRITICAL:
  raw = 0x28
  real = 40.0
```

#### 4. Set a Configuration Value

Set using real value (for threshold parameters):
```bash
./pmc_config_tool.py archercity.pmc --dev "RR_Brd Temp 1" --set UPPER_CRITICAL 45.0
```

Set using raw value:
```bash
./pmc_config_tool.py archercity.pmc --dev "P12V_AUX" --set NOMINAL_VOLTAGE 0x78
```

Output:
```
Calculation: 12.0 / (100 * 10^(-3)) = 120.0 ≈ 120
Config saved successfully (converted from real value 12.0)
Backup created: archercity.pmc.backup
Changes saved to: archercity.pmc
```

#### 5. Interactive Threshold Configuration

```bash
./pmc_config_tool.py archercity.pmc --dev "RR_Brd Temp 1" --set-thres
```

This launches an interactive session to batch configure all threshold parameters:

```
============================================================
Interactive Threshold Configuration for: RR_Brd Temp 1
============================================================
Press Enter to keep current value, or enter a new value.
For threshold parameters, enter the REAL value (e.g., 12.5 for voltage)
------------------------------------------------------------

Current threshold values:
----------------------------------------
  LOWER_NON_RECOVERABLE: 0x0    (0.0)
  LOWER_CRITICAL: 0x0           (0.0)
  LOWER_NON_CRITICAL: 0x5       (5.0)
  UPPER_NON_CRITICAL: 0x20      (32.0)
  UPPER_CRITICAL: 0x28          (40.0)
  UPPER_NON_RECOVERABLE: 0x46   (70.0)
  SEN_MIN: 0x0                  (0.0)
  SEN_MAX: 0xff                 (255.0)
  NOMINAL_MIN: 0x8b             (139.0)
  NOMINAL_MAX: 0xc5             (197.0)

------------------------------------------------------------
Enter new values (or press Enter to skip):
------------------------------------------------------------
LOWER_NON_RECOVERABLE [current: 0.0]:
LOWER_CRITICAL [current: 0.0]:
LOWER_NON_CRITICAL [current: 5.0]:
UPPER_NON_CRITICAL [current: 32.0]: 30
  -> Converting 30 to 0x1e
UPPER_CRITICAL [current: 40.0]: 45
  -> Converting 45 to 0x2d
UPPER_NON_RECOVERABLE [current: 70.0]: 80
  -> Converting 80 to 0x50
SEN_MIN [current: 0.0]:
SEN_MAX [current: 255.0]:
NOMINAL_MIN [current: 139.0]: 135
  -> Converting 135 to 0x87
NOMINAL_MAX [current: 197.0]:

------------------------------------------------------------
Now configuring mask values (or press Enter to skip):
------------------------------------------------------------
LWR_T_MASK (Lower Threshold Reading Mask) [current: 0x3285]:
UPR_T_MASK (Upper Threshold Reading Mask) [current: 0x3285]:
S_R_T_MASK (Settable/Readable Threshold Mask) [current: 0x1b1b]:

============================================================
Summary of changes to be applied:
============================================================
  UPPER_NON_CRITICAL: 0x1e
  UPPER_CRITICAL: 0x2d
  UPPER_NON_RECOVERABLE: 0x50
  NOMINAL_MIN: 0x87

Apply these changes? (y/N): y
Backup created: archercity.pmc.backup
Successfully applied 4 changes!
```

## Threshold Parameters

The following parameters support automatic raw/real value conversion:

- **NOMINAL_READING** - Nominal reading value
- **NOMINAL_MAX** - Nominal maximum value
- **NOMINAL_MIN** - Nominal minimum value
- **SEN_MAX** - Sensor maximum value
- **SEN_MIN** - Sensor minimum value
- **UPPER_NON_RECOVERABLE** - Upper non-recoverable threshold
- **UPPER_CRITICAL** - Upper critical threshold
- **UPPER_NON_CRITICAL** - Upper non-critical threshold
- **LOWER_NON_RECOVERABLE** - Lower non-recoverable threshold
- **LOWER_CRITICAL** - Lower critical threshold
- **LOWER_NON_CRITICAL** - Lower non-critical threshold

## Value Conversion

The tool automatically converts between raw and real values using the formula:

```
real_value = (M_VAL * raw_value) * 10^(R_EXP)
```

Where:
- **M_VAL** and **R_EXP** are extracted from device or SDR configuration
- For temperature sensors: Real values are in Celsius
- For voltage sensors: Real values are in Volts

### Examples

Temperature sensor (M_VAL=1, R_EXP=0):
- Raw: 0x28 (40)
- Real: 40.0°C

Voltage sensor (M_VAL=0x64 (100), R_EXP=-3):
- Real: 12.0V
- Raw: 0x78 (120)
- Calculation: 12.0 / (100 * 10^(-3)) = 120

## Mask Parameters

When using `--set-thres`, you can also configure these mask values:

- **LWR_T_MASK** - Lower Threshold Reading Mask
- **UPR_T_MASK** - Upper Threshold Reading Mask
- **S_R_T_MASK** - Settable/Readable Threshold Mask

## Tips

1. **Backup Files**: By default, a backup is created before saving changes (`.backup` extension)
2. **Skip Changes**: Press Enter without entering a value to keep the current setting
3. **Order of Thresholds**: When using `--set-thres`, thresholds are presented in logical order:
   - Lower thresholds (non-recoverable → critical → non-critical)
   - Upper thresholds (non-critical → critical → non-recoverable)
   - Sensor range and nominal values
4. **Raw vs Real**: Always enter real physical values (e.g., 12.5 for 12.5V) for threshold parameters, the tool handles conversion automatically

## Error Handling

- File not found errors
- XML parsing errors
- Missing M_VAL or R_EXP for conversions
- Invalid value formats
- Device not found errors

## License

This tool is part of the BMC firmware development toolkit.
