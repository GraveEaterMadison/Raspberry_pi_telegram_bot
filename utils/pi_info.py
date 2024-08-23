import subprocess

def get_system_info():
    return subprocess.check_output("uname -a", shell=True).decode()

def get_cpu_temperature():
    return subprocess.check_output("vcgencmd measure_temp", shell=True).decode().strip()

def get_ip_addresses():
    return subprocess.check_output("hostname -I", shell=True).decode().strip()

def get_ram_usage() -> str:
    try:
        result = subprocess.check_output("free -m", shell=True)
        lines = result.decode('utf-8').splitlines()
        memory_info = lines[1].split()
        total = int(memory_info[1])
        used = int(memory_info[2])
        free = int(memory_info[3])
        used_percent = (used / total) * 100
        free_percent = (free / total) * 100
        return (f"Total RAM: {total} MB\n"
                f"Used RAM: {used} MB ({used_percent:.2f}%)\n"
                f"Free RAM: {free} MB ({free_percent:.2f}%)")
    except subprocess.CalledProcessError as e:
        return f"Error retrieving RAM usage: {e.output.decode('utf-8')}"


def get_cpu_usage() -> str:
    try:
        result = subprocess.check_output("top -bn1 | grep 'Cpu(s)'", shell=True)
        cpu_info = result.decode('utf-8').split()
        user = float(cpu_info[1])
        system = float(cpu_info[3])
        idle = float(cpu_info[7])
        used = 100 - idle
        return (f"User CPU Usage: {user:.2f}%\n"
                f"System CPU Usage: {system:.2f}%\n"
                f"Idle CPU Usage: {idle:.2f}%\n"
                f"Total CPU Usage: {used:.2f}%")
    except subprocess.CalledProcessError as e:
        return f"Error retrieving CPU usage: {e.output.decode('utf-8')}"


def get_disk_usage() -> str:
    try:
        result = subprocess.check_output("df -h --total", shell=True)
        lines = result.decode('utf-8').splitlines()
        disk_info = lines[-1].split()
        total = disk_info[1]
        used = disk_info[2]
        available = disk_info[3]
        used_percent = disk_info[4]
        return (f"Total Disk Space: {total}\n"
                f"Used Disk Space: {used} ({used_percent})\n"
                f"Available Disk Space: {available}")
    except subprocess.CalledProcessError as e:
        return f"Error retrieving disk usage: {e.output.decode('utf-8')}"


def get_uptime():
    return subprocess.check_output("uptime -p", shell=True).decode()

def get_services() -> str:
    try:
        result = subprocess.check_output("systemctl list-units --type=service --state=running", shell=True)
        return result.decode('utf-8')
    except subprocess.CalledProcessError as e:
        return f"Error retrieving services: {e.output.decode('utf-8')}"

def manage_service(action: str, service: str) -> str:
    try:
        if action not in ["start", "stop", "status", "restart"]:
            return "Invalid action. Use one of the following: start, stop, status, restart."

        result = subprocess.check_output(f"sudo systemctl {action} {service}", shell=True, stderr=subprocess.STDOUT)
        return result.decode('utf-8')
    except subprocess.CalledProcessError as e:
        return f"Error performing {action} on {service}: {e.output.decode('utf-8')}"

def get_gpio_status():
    return subprocess.check_output("gpio readall", shell=True).decode()

def get_netinfo():
    return subprocess.check_output("ifconfig", shell=True).decode()

def ping_host(host):
    return subprocess.check_output(f"ping -c 4 {host}", shell=True).decode()



def get_running_services() -> str:
    try:
        result = subprocess.check_output("systemctl list-units --type=service --state=running", shell=True)
        lines = result.decode('utf-8').splitlines()
        if len(lines) < 2:
            return "No running services found or command failed."

        # Extract headers and rows
        headers = lines[0].split()
        rows = [line.split(None, len(headers)-1) for line in lines[1:] if len(line.split()) >= len(headers)]
        
        # Format header
        output = f"{'No.':<5} {'Unit':<30} {'Load':<10} {'Active':<15} {'Sub':<15} {'Description':<50}\n"
        output += '-' * 120 + '\n'
        
        
        for idx, row in enumerate(rows, 1):
            unit = row[0] if len(row) > 0 else "N/A"
            load = row[1] if len(row) > 1 else "N/A"
            active = row[2] if len(row) > 2 else "N/A"
            sub = row[3] if len(row) > 3 else "N/A"
            description = ' '.join(row[4:]) if len(row) > 4 else "N/A"
            output += f"{idx:<5} {unit:<30} {load:<10} {active:<15} {sub:<15} {description:<50}\n\n\n"
        
        return output
    except subprocess.CalledProcessError as e:
        return f"Error retrieving running services: {e.output.decode('utf-8')}"



def get_all_services() -> str:
    try:
        result = subprocess.check_output("systemctl list-unit-files --type=service", shell=True)
        services = result.decode('utf-8').splitlines()
        services = [service for service in services if service.strip() != ""]
        formatted_services = "\n\n".join([f"{i+1}. {services[i]}" for i in range(len(services))])
        return formatted_services
    except subprocess.CalledProcessError as e:
        return f"Error retrieving all services: {e.output.decode('utf-8')}"

