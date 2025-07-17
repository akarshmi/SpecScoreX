import subprocess
import json
import tempfile
import os

# Simple test script to debug PowerShell issues
def test_powershell_basic():
    """Test basic PowerShell functionality"""
    print("=== Testing Basic PowerShell ===")
    
    try:
        result = subprocess.run([
            "powershell", "-Command", "Write-Output 'Hello World'"
        ], capture_output=True, text=True, timeout=10)
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            print("✓ Basic PowerShell works")
            return True
        else:
            print("✗ Basic PowerShell failed")
            return False
            
    except Exception as e:
        print(f"✗ PowerShell test failed: {e}")
        return False

def test_powershell_json():
    """Test PowerShell JSON conversion"""
    print("\n=== Testing PowerShell JSON Conversion ===")
    
    simple_script = '''
    $data = @{
        test = "success"
        number = 42
        array = @(1, 2, 3)
    }
    $data | ConvertTo-Json -Compress
    '''
    
    try:
        result = subprocess.run([
            "powershell", "-Command", simple_script
        ], capture_output=True, text=True, timeout=10)
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            try:
                json_data = json.loads(result.stdout.strip())
                print(f"✓ JSON conversion works: {json_data}")
                return True
            except json.JSONDecodeError as e:
                print(f"✗ JSON parsing failed: {e}")
                return False
        else:
            print("✗ PowerShell JSON test failed")
            return False
            
    except Exception as e:
        print(f"✗ PowerShell JSON test failed: {e}")
        return False

def test_powershell_wmi():
    """Test PowerShell WMI/CIM queries"""
    print("\n=== Testing PowerShell WMI/CIM Queries ===")
    
    wmi_script = '''
    try {
        $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop | Select-Object Caption, Version
        $result = @{
            success = $true
            os_info = $os
        }
        $result | ConvertTo-Json -Compress
    } catch {
        $error = @{
            success = $false
            error = $_.Exception.Message
        }
        $error | ConvertTo-Json -Compress
    }
    '''
    
    try:
        result = subprocess.run([
            "powershell", "-Command", wmi_script
        ], capture_output=True, text=True, timeout=15)
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            try:
                json_data = json.loads(result.stdout.strip())
                if json_data.get('success'):
                    print(f"✓ WMI/CIM queries work: {json_data}")
                    return True
                else:
                    print(f"✗ WMI/CIM query failed: {json_data.get('error')}")
                    return False
            except json.JSONDecodeError as e:
                print(f"✗ JSON parsing failed: {e}")
                return False
        else:
            print("✗ PowerShell WMI test failed")
            return False
            
    except Exception as e:
        print(f"✗ PowerShell WMI test failed: {e}")
        return False

def test_powershell_file_execution():
    """Test PowerShell file execution"""
    print("\n=== Testing PowerShell File Execution ===")
    
    script_content = '''
    $data = @{
        message = "File execution test"
        timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    }
    $data | ConvertTo-Json -Compress
    '''
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(script_content)
            temp_script_path = temp_file.name
        
        result = subprocess.run([
            "powershell", "-ExecutionPolicy", "Bypass", "-File", temp_script_path
        ], capture_output=True, text=True, timeout=10)
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        # Clean up
        os.unlink(temp_script_path)
        
        if result.returncode == 0:
            try:
                json_data = json.loads(result.stdout.strip())
                print(f"✓ File execution works: {json_data}")
                return True
            except json.JSONDecodeError as e:
                print(f"✗ JSON parsing failed: {e}")
                return False
        else:
            print("✗ PowerShell file execution failed")
            return False
            
    except Exception as e:
        print(f"✗ PowerShell file execution test failed: {e}")
        return False

def test_minimal_system_info():
    """Test minimal system info collection"""
    print("\n=== Testing Minimal System Info Collection ===")
    
    minimal_script = '''
    try {
        $ProgressPreference = "SilentlyContinue"
        
        $info = @{
            timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
            hostname = $env:COMPUTERNAME
            os = (Get-CimInstance Win32_OperatingSystem -ErrorAction Stop).Caption
            processor = (Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object -First 1).Name
        }
        
        $info | ConvertTo-Json -Compress
    } catch {
        $error = @{
            error = "System info collection failed: $($_.Exception.Message)"
        }
        $error | ConvertTo-Json -Compress
    }
    '''
    
    try:
        result = subprocess.run([
            "powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", minimal_script
        ], capture_output=True, text=True, timeout=15)
        
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0:
            try:
                json_data = json.loads(result.stdout.strip())
                if 'error' not in json_data:
                    print(f"✓ Minimal system info works: {json_data}")
                    return True
                else:
                    print(f"✗ System info collection failed: {json_data.get('error')}")
                    return False
            except json.JSONDecodeError as e:
                print(f"✗ JSON parsing failed: {e}")
                return False
        else:
            print("✗ Minimal system info test failed")
            return False
            
    except Exception as e:
        print(f"✗ Minimal system info test failed: {e}")
        return False

if __name__ == "__main__":
    print("PowerShell Diagnostic Test Suite")
    print("=" * 50)
    
    tests = [
        test_powershell_basic,
        test_powershell_json,
        test_powershell_wmi,
        test_powershell_file_execution,
        test_minimal_system_info
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print(f"Basic PowerShell: {'✓' if results[0] else '✗'}")
    print(f"JSON Conversion: {'✓' if results[1] else '✗'}")
    print(f"WMI/CIM Queries: {'✓' if results[2] else '✗'}")
    print(f"File Execution: {'✓' if results[3] else '✗'}")
    print(f"System Info: {'✓' if results[4] else '✗'}")
    
    if all(results):
        print("\n✓ All tests passed! PowerShell should work correctly.")
    else:
        print("\n✗ Some tests failed. Check the output above for details.")
        print("\nTroubleshooting suggestions:")
        print("1. Run PowerShell as administrator")
        print("2. Check execution policy: Get-ExecutionPolicy")
        print("3. Set execution policy: Set-ExecutionPolicy RemoteSigned")
        print("4. Ensure Windows PowerShell (not PowerShell Core) is available")