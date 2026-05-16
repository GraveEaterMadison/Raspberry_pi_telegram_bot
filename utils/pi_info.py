import re
import subprocess


def get_system_info():
    return subprocess.check_output(["uname", "-a"]).decode()


def get_cpu_temperature():
    return subprocess.check_output(["vcgencmd", "measure_temp"]).decode().strip()


def get_ip_addresses():
    return subprocess.check_output(["hostname", "-I"]).decode().strip()


def get_ram_usage() -> str:
    try:
        result = subprocess.check_output(["free", "-m"])
        lines = result.decode("utf-8").splitlines()
        memory_info = lines[1].split()
        total = int(memory_info[1])
        used  = int(memory_info[2])
        free  = int(memory_info[3])
        used_percent = (used / total) * 100
        free_percent = (free / total) * 100
        return (f"Total RAM: {total} MB\n"
                f"Used RAM: {used} MB ({used_percent:.2f}%)\n"
                f"Free RAM: {free} MB ({free_percent:.2f}%)")
    except subprocess.CalledProcessError as e:
        return f"Error retrieving RAM usage: {e.output.decode('utf-8')}"


def get_cpu_usage() -> str:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        per = psutil.cpu_times_percent(interval=0)
        return (f"User CPU Usage: {per.user:.2f}%\n"
                f"System CPU Usage: {per.system:.2f}%\n"
                f"Idle CPU Usage: {per.idle:.2f}%\n"
                f"Total CPU Usage: {cpu:.2f}%")
    except Exception as e:
        return f"Error retrieving CPU usage: {e}"


def get_disk_usage() -> str:
    try:
        result = subprocess.check_output(["df", "-h", "--total"])
        lines = result.decode("utf-8").splitlines()
        disk_info = lines[-1].split()
        total        = disk_info[1]
        used         = disk_info[2]
        available    = disk_info[3]
        used_percent = disk_info[4]
        return (f"Total Disk Space: {total}\n"
                f"Used Disk Space: {used} ({used_percent})\n"
                f"Available Disk Space: {available}")
    except subprocess.CalledProcessError as e:
        return f"Error retrieving disk usage: {e.output.decode('utf-8')}"


def get_uptime():
    return subprocess.check_output(["uptime", "-p"]).decode()


def get_services() -> str:
    try:
        result = subprocess.check_output(
            ["systemctl", "list-units", "--type=service", "--state=running"]
        )
        return result.decode("utf-8")
    except subprocess.CalledProcessError as e:
        return f"Error retrieving services: {e.output.decode('utf-8')}"


def manage_service(action: str, service: str) -> str:
    try:
        if action not in ["start", "stop", "status", "restart"]:
            return "Invalid action. Use one of the following: start, stop, status, restart."

     
        result = subprocess.check_output(
            ["sudo", "systemctl", action, service],
            stderr=subprocess.STDOUT
        )
        return result.decode("utf-8")
    except subprocess.CalledProcessError as e:
        return f"Error performing {action} on {service}: {e.output.decode('utf-8')}"


def get_gpio_status():
    return subprocess.check_output(["gpio", "readall"]).decode()


def get_netinfo():
    return subprocess.check_output(["ifconfig"]).decode()


def ping_host(host: str) -> str:
    if not re.match(r'^[a-zA-Z0-9.\-:]+$', host):
        return "❌ Invalid host name."
    try:
        result = subprocess.check_output(
            ["ping", "-c", "4", "-W", "3", host],
            stderr=subprocess.STDOUT,
            timeout=15,
        )
        return result.decode()
    except subprocess.CalledProcessError as e:
        return e.output.decode() or f"Host '{host}' is unreachable."
    except subprocess.TimeoutExpired:
        return f"❌ Ping to '{host}' timed out."


def get_running_services() -> str:
    try:
        result = subprocess.check_output(
            ["systemctl", "list-units", "--type=service", "--state=running"]
        )
        lines = result.decode("utf-8").splitlines()
        if len(lines) < 2:
            return "No running services found or command failed."

        headers = lines[0].split()
        rows = [line.split(None, len(headers) - 1) for line in lines[1:] if len(line.split()) >= len(headers)]

        output = f"{'No.':<5} {'Unit':<30} {'Load':<10} {'Active':<15} {'Sub':<15} {'Description':<50}\n"
        output += '-' * 120 + '\n'

        for idx, row in enumerate(rows, 1):
            unit        = row[0] if len(row) > 0 else "N/A"
            load        = row[1] if len(row) > 1 else "N/A"
            active      = row[2] if len(row) > 2 else "N/A"
            sub         = row[3] if len(row) > 3 else "N/A"
            description = ' '.join(row[4:]) if len(row) > 4 else "N/A"
            output += f"{idx:<5} {unit:<30} {load:<10} {active:<15} {sub:<15} {description:<50}\n\n\n"

        return output
    except subprocess.CalledProcessError as e:
        return f"Error retrieving running services: {e.output.decode('utf-8')}"


def get_all_services() -> str:
    try:
        result = subprocess.check_output(
            ["systemctl", "list-unit-files", "--type=service"]
        )
        services = result.decode("utf-8").splitlines()
        services = [s for s in services if s.strip()]
        return "\n\n".join(f"{i+1}. {services[i]}" for i in range(len(services)))
    except subprocess.CalledProcessError as e:
        return f"Error retrieving all services: {e.output.decode('utf-8')}"
