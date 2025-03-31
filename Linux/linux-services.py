import subprocess
# List all services and their statuses on a linux machine
def get_all_service_statuses():
    try:
        output = subprocess.check_output(
            ['systemctl', 'list-units', '--type=service', '--no-pager', '--no-legend'],
            stderr=subprocess.DEVNULL
        ).decode('utf-8')

        services = []
        for line in output.strip().split('\n'):
            if line:
                parts = line.split(None, 4)
                service_name = parts[0]
                load_state = parts[1]
                active_state = parts[2]
                sub_state = parts[3]
                description = parts[4] if len(parts) > 4 else ''
                services.append({
                    'name': service_name,
                    'load_state': load_state,
                    'active_state': active_state,
                    'sub_state': sub_state,
                    'description': description
                })

        return services

    except subprocess.CalledProcessError:
        return []

# append output to a file
services = get_all_service_statuses()
with open("services.txt", "a", encoding="utf-8") as f:  # 'a' to append
    for svc in services:
        f.write(f"name: {svc['name']}:  | active: {svc['active_state']} | sub: ({svc['sub_state']}) | description: {svc['description']}\n")
