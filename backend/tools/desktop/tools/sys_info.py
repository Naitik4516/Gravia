import platform
import psutil
import socket
import cpuinfo
import wmi
import screeninfo
import json
import asyncio



def get_cpu_info():
    info = {}
    if cpuinfo:
        cpu = cpuinfo.get_cpu_info()
        info['cpu_name'] = cpu.get('brand_raw', 'Unknown')
        info['arch'] = cpu.get('arch', 'Unknown')
    else:
        info['cpu_name'] = platform.processor()
        info['arch'] = platform.machine()
    info['physical_cores'] = psutil.cpu_count(logical=False)
    info['total_cores'] = psutil.cpu_count(logical=True)
    info['cpu_frequency_mhz'] = round(psutil.cpu_freq().current, 2)
    info['cpu_usage_percent'] = psutil.cpu_percent(interval=1)

    # CPU cache size is platform dependent
    cache_size = 'Unknown'
    if wmi:
        c = wmi.WMI()
        for cpu in c.Win32_Processor():
            cache_size = cpu.L2CacheSize or cpu.L3CacheSize or 'Unknown'
            break
    info['cpu_cache_size_kb'] = cache_size


    return info

def get_ram_info():
    info = {}
    vm = psutil.virtual_memory()
    info['total_ram_gb'] = round(vm.total / (1024 ** 3), 2)
    info['available_ram_gb'] = round(vm.available / (1024 ** 3), 2)
    # RAM type is platform dependent
    ram_type = 'Unknown'
    if wmi:
        c = wmi.WMI()
        for mem in c.Win32_PhysicalMemory():
            ram_type = mem.MemoryType
            break
    info['ram_type'] = ram_type
    return info

def get_os_info():
    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'os_release': platform.release(),
        'hostname': socket.gethostname()
    }

def get_storage_info():
    drives = []
    partitions = psutil.disk_partitions()
    for p in partitions:
        try:
            usage = psutil.disk_usage(p.mountpoint)
            drives.append({
                'device': p.device,
                'mountpoint': p.mountpoint,
                'fstype': p.fstype,
                'total_gb': round(usage.total / (1024 ** 3), 2),
                'used_gb': round(usage.used / (1024 ** 3), 2),
                'free_gb': round(usage.free / (1024 ** 3), 2),
            })
        except PermissionError:
            continue
    return drives

def get_display_info():
    displays = []
    if screeninfo:
        for m in screeninfo.get_monitors():
            displays.append({
                'width': m.width,
                'height': m.height,
                'name': getattr(m, 'name', 'Unknown'),
            })
    else:
        # fallback for Windows using wmi
        if wmi:
            c = wmi.WMI(namespace='wmi')
            for monitor in c.WmiMonitorBasicDisplayParams():
                displays.append({
                    'width': getattr(monitor, 'MaxHorizontalImageSize', 'Unknown'),
                    'height': getattr(monitor, 'MaxVerticalImageSize', 'Unknown'),
                })
    # Refresh rate is platform dependent
    refresh_rate = 'Unknown'
    if wmi:
        c = wmi.WMI()
        for vc in c.Win32_VideoController():
            refresh_rate = getattr(vc, 'CurrentRefreshRate', 'Unknown')
            break
    return {'displays': displays, 'refresh_rate': refresh_rate}

def get_pc_type():
    # Only works on Windows with wmi
    if wmi:
        c = wmi.WMI()
        for system in c.Win32_SystemEnclosure():
            chassis_types = system.ChassisTypes
            if chassis_types:
                if 8 in chassis_types or 9 in chassis_types or 10 in chassis_types or 14 in chassis_types:
                    return 'Laptop'
                elif 3 in chassis_types or 4 in chassis_types or 5 in chassis_types or 6 in chassis_types or 7 in chassis_types or 15 in chassis_types:
                    return 'Desktop'
    # Fallback: check for battery
    if hasattr(psutil, "sensors_battery") and psutil.sensors_battery():
        return 'Laptop'
    return 'Desktop'

def get_gpu_info():
    gpus = []
    if wmi:
        c = wmi.WMI()
        for gpu in c.Win32_VideoController():
            gpu_type = 'Integrated' if 'intel' in gpu.Name.lower() else 'Discrete'
            gpus.append({
                'name': gpu.Name,
                'driver_version': getattr(gpu, 'DriverVersion', 'Unknown'),
                'video_memory_mb': int(getattr(gpu, 'AdapterRAM', 0)) // (1024 * 1024),
                'gpu_type': gpu_type,
                'status': getattr(gpu, 'Status', 'Unknown')
            })
    else:
        # Fallback: minimal info
        gpus.append({
            'name': 'Unknown',
            'driver_version': 'Unknown',
            'video_memory_mb': 'Unknown',
            'gpu_type': 'Unknown',
            'status': 'Unknown'
        })
    return gpus

async def get_pc_info():
    """Yields the output of each info function asynchronously."""
    loop = asyncio.get_event_loop()

    cpu = await loop.run_in_executor(None, get_cpu_info)
    yield {'cpu': cpu}

    ram = await loop.run_in_executor(None, get_ram_info)
    yield {'ram': ram}

    os_info = await loop.run_in_executor(None, get_os_info)
    yield {'os': os_info}

    storage = await loop.run_in_executor(None, get_storage_info)
    yield {'storage': storage}

    display = await loop.run_in_executor(None, get_display_info)
    yield {'display': display}

    gpu = await loop.run_in_executor(None, get_gpu_info)
    yield {'gpu': gpu}

    pc_type = await loop.run_in_executor(None, get_pc_type)
    yield {'pc_type': pc_type}

if __name__ == "__main__":
    info = get_pc_info()
    print(json.dumps(info, indent=4))