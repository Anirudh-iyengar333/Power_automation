#!/usr/bin/env python3
"""
PWR-STD-04 Demo Script

Demonstrates how to use the PWR-STD-04 automation suite with different
configurations and customization options.

Author: Senior Test Automation Engineer
Version: 1.0.0 - Production Grade
Date: 2024-12-03
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from pwr_std_04_automation import PWRStd04SteadyStateTest, TestConfiguration
from pwr_std_04_config import get_lab_config, validate_configuration


def demo_basic_usage():
    """Demonstrate basic automation usage"""
    print("=" * 80)
    print("PWR-STD-04 DEMO: BASIC USAGE")
    print("=" * 80)
    
    # Update these addresses for your lab setup
    DMM_ADDRESS = "GPIB::22::INSTR"  # Your DMM address
    PSU_ADDRESS = "GPIB::5::INSTR"   # Your PSU address
    
    # Create basic configuration
    config = TestConfiguration(
        psu_voltage=5.0,
        psu_current_limit=3.0,
        stabilization_time=60,
        measurement_samples=10
    )
    
    print(f"Creating test suite with:")
    print(f"  DMM Address: {DMM_ADDRESS}")
    print(f"  PSU Address: {PSU_ADDRESS}")
    print(f"  Configuration: {config}")
    
    # Create test suite
    test_suite = PWRStd04SteadyStateTest(
        dmm_address=DMM_ADDRESS,
        psu_address=PSU_ADDRESS,
        config=config,
        output_directory="./demo_results"
    )
    
    print(f"\nTest suite created successfully!")
    print(f"   To run: test_suite.run_complete_test()")
    
    return test_suite


def demo_predefined_configurations():
    """Demonstrate predefined configuration usage"""
    print("=" * 80)
    print("PWR-STD-04 DEMO: PREDEFINED CONFIGURATIONS")
    print("=" * 80)
    
    configurations = ["default", "high_precision", "fast", "production", "debug"]
    
    for config_name in configurations:
        print(f"\n{config_name.upper()} CONFIGURATION:")
        print("-" * 50)
        
        try:
            config = get_lab_config(config_name)
            
            print(f"  Measurement Samples: {config.MEASUREMENT_SAMPLES}")
            print(f"  Measurement Interval: {config.MEASUREMENT_INTERVAL}s")
            print(f"  DMM NPLC: {config.DMM_NPLC}")
            print(f"  Stabilization Time: {config.STABILIZATION_TIME}s")
            print(f"  Statistics Enabled: {config.ENABLE_STATISTICS}")
            print(f"  Log Level: {config.LOG_LEVEL}")
            
            # Validate configuration
            is_valid = validate_configuration(config)
            status = "VALID" if is_valid else "INVALID"
            print(f"  Validation: {status}")
            
        except Exception as e:
            print(f"  ERROR: Error loading configuration: {e}")


def demo_custom_configuration():
    """Demonstrate custom configuration creation"""
    print("=" * 80)
    print("PWR-STD-04 DEMO: CUSTOM CONFIGURATION")
    print("=" * 80)
    
    # Start with a base configuration
    base_config = get_lab_config("production")
    
    # Customize for specific requirements
    print("Creating custom configuration...")
    
    # Example: High-accuracy testing for critical project
    custom_config = base_config
    custom_config.MEASUREMENT_SAMPLES = 25          # More samples
    custom_config.DMM_NPLC = 5.0                   # Higher accuracy
    custom_config.STABILIZATION_TIME = 120         # Longer stabilization
    custom_config.COMPANY_NAME = "Demo Electronics"
    custom_config.PROJECT_NAME = "Critical CPU Board Rev 2.1"
    custom_config.ENGINEER_NAME = "Senior Test Engineer"
    
    # Custom rail specifications
    custom_config.CUSTOM_RAIL_SPECS = {
        '3V3': {
            'min_voltage': 3.250,  # Tighter tolerance for critical rail
            'max_voltage': 3.350,
            'description': 'Critical 3.3V system rail - tight tolerance'
        }
    }
    
    print("Custom configuration created:")
    print(f"  Project: {custom_config.PROJECT_NAME}")
    print(f"  Company: {custom_config.COMPANY_NAME}")
    print(f"  Engineer: {custom_config.ENGINEER_NAME}")
    print(f"  Samples per rail: {custom_config.MEASUREMENT_SAMPLES}")
    print(f"  DMM accuracy: {custom_config.DMM_NPLC} NPLC")
    print(f"  Custom rail specs: {len(custom_config.CUSTOM_RAIL_SPECS)} rails")
    
    # Validate custom configuration
    if validate_configuration(custom_config):
        print("Custom configuration validated successfully!")
    
    return custom_config


def demo_test_simulation():
    """Simulate a test run (without actual instruments)"""
    print("=" * 80)
    print("PWR-STD-04 DEMO: TEST SIMULATION")
    print("=" * 80)
    
    print("This demo shows what a typical test sequence looks like:")
    print("   (Actual instruments not required)")
    
    # Simulate the test steps
    steps = [
        "Connecting to instruments...",
        "Configuring DMM for DC voltage measurements",
        "Configuring PSU: 5.000V, 3.000A limit",
        "Pre-test checks: board inspection, probe setup",
        "Power-on sequence: enabling PSU, monitoring current",
        "Stabilization period: 60 seconds",
        "Measuring 5V Input at PSU/TP: 5.0124V [PASS]",
        "Measuring 3V6 at TP2: 3.6089V [PASS]",
        "Measuring 3V3 at TP10: 3.3045V [PASS]",
        "Measuring 2V5 at TP9: 2.4987V [PASS]",
        "Measuring 1V8 at TP6: 1.8023V [PASS]",
        "Measuring 1V35 at TP7: 1.3498V [PASS]",
        "Generating test documentation...",
        "Professional Word report created",
        "Results saved: JSON, CSV, summary files",
        "Safe shutdown and cleanup",
        "Test completed: PASS"
    ]
    
    import time
    for i, step in enumerate(steps):
        print(f"[{i+1:2d}/{len(steps)}] {step}")
        time.sleep(0.5)  # Simulate processing time
    
    print("\nSimulation complete!")
    print("   Typical test duration: ~5 minutes")
    print("   Output files: Word report, JSON/CSV data, logs")


def demo_safety_features():
    """Demonstrate safety monitoring features"""
    print("=" * 80)
    print("PWR-STD-04 DEMO: SAFETY FEATURES")
    print("=" * 80)
    
    print("Safety monitoring capabilities:")
    print("")
    
    safety_features = [
        {
            "feature": "Current Monitoring",
            "description": "Real-time current monitoring with automatic shutdown",
            "threshold": "5.0A (configurable)",
            "action": "Immediate PSU disable + comprehensive logging"
        },
        {
            "feature": "Voltage Validation", 
            "description": "Out-of-specification voltage detection",
            "threshold": "Per-rail tolerance limits",
            "action": "Test failure logging + continue to next rail"
        },
        {
            "feature": "Communication Verification",
            "description": "Instrument connectivity validation before testing", 
            "threshold": "SCPI command response",
            "action": "Test abort if communication fails"
        },
        {
            "feature": "Emergency Stop",
            "description": "User-initiated emergency shutdown capability",
            "threshold": "Type 'abort' at any manual prompt",
            "action": "Immediate safe shutdown sequence"
        },
        {
            "feature": "Probe Connection Verification",
            "description": "Interactive probe connection validation",
            "threshold": "Manual operator verification",
            "action": "Prevent incorrect measurements"
        }
    ]
    
    for i, feature in enumerate(safety_features, 1):
        print(f"{i}. {feature['feature']}")
        print(f"   Description: {feature['description']}")
        print(f"   Threshold: {feature['threshold']}")
        print(f"   Action: {feature['action']}")
        print()
    
    print("Comprehensive safety monitoring ensures:")
    print("   • No damage to board under test")
    print("   • No damage to test instruments")  
    print("   • Clear operator guidance at all times")
    print("   • Complete audit trail of all actions")


def main():
    """Main demo runner"""
    print("PWR-STD-04 AUTOMATION SUITE DEMONSTRATION")
    print("Enterprise-Grade Test Automation v1.0.0")
    print("=" * 80)
    
    demos = [
        ("Basic Usage", demo_basic_usage),
        ("Predefined Configurations", demo_predefined_configurations),
        ("Custom Configuration", demo_custom_configuration),
        ("Test Simulation", demo_test_simulation),
        ("Safety Features", demo_safety_features)
    ]
    
    while True:
        print("\nAvailable Demonstrations:")
        for i, (name, _) in enumerate(demos, 1):
            print(f"   {i}. {name}")
        print(f"   {len(demos) + 1}. Run All Demos")
        print(f"   0. Exit")
        
        try:
            choice = input(f"\nSelect demo (0-{len(demos) + 1}): ").strip()
            
            if choice == "0":
                print("\nThank you for trying PWR-STD-04 automation!")
                print("   Update instrument addresses in config files to begin testing.")
                break
            elif choice == str(len(demos) + 1):
                # Run all demos
                for name, demo_func in demos:
                    print(f"\nRunning: {name}")
                    demo_func()
                    input("\nPress ENTER to continue...")
            elif choice.isdigit() and 1 <= int(choice) <= len(demos):
                demo_index = int(choice) - 1
                name, demo_func = demos[demo_index]
                print(f"\nRunning: {name}")
                demo_func()
            else:
                print("Invalid selection. Please try again.")
                
        except KeyboardInterrupt:
            print("\n\nDemo interrupted. Thank you!")
            break
        except Exception as e:
            print(f"\nDemo error: {e}")


if __name__ == "__main__":
    main()
