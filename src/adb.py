import subprocess


def detect_adb():
    """Detect if adb is installed on the system."""
    try:
        subprocess.check_output(['adb', 'version'])
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True


def get_devices():
    """Get the list of connected devices."""
    try:
        devices = subprocess.check_output(['adb', 'devices']).decode('utf-8').split('\n')[1:-2]
    except subprocess.CalledProcessError:
        return []
    return [device.split('\t')[0] for device in devices]


def push_file(file_path, device_path):
    """Push a file to a device."""
    try:
        subprocess.check_output(['adb', 'push', file_path, device_path])
    except subprocess.CalledProcessError:
        return False
    return True