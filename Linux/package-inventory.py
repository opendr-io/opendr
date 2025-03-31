import subprocess
import shutil

def get_rpm_packages():
    try:
        output = subprocess.check_output(
            ['rpm', '-qa', '--qf', '%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\t%{SUMMARY}\n'],
            stderr=subprocess.DEVNULL
        ).decode('utf-8')

        packages = []
        for line in output.strip().split('\n'):
            parts = line.split('\t', 3)
            if len(parts) == 4:
                pkg = {
                    'name': parts[0],
                    'version': parts[1],
                    'architecture': parts[2],
                    'description': parts[3]
                }
                packages.append(pkg)
        return packages
    except subprocess.CalledProcessError:
        return []
        
def get_debian_packages():
    try:
        output = subprocess.check_output(
            ['dpkg-query', '-W', '-f=${Package}\t${Version}\t${Architecture}\t${Description}\n'],
            stderr=subprocess.DEVNULL
        ).decode('utf-8')

        packages = []
        for line in output.strip().split('\n'):
            parts = line.split('\t', 3)
            if len(parts) == 4:
                pkg = {
                    'name': parts[0],
                    'version': parts[1],
                    'architecture': parts[2],
                    'description': parts[3]
                }
                packages.append(pkg)
        return packages
    except subprocess.CalledProcessError:
        return []

# run one of the above functions after checking if we have deb or rpm packages
def get_installed_packages():
    try:
        if shutil.which("dpkg"):
            return get_debian_packages()
        elif shutil.which("rpm"):
            return get_rpm_packages()
        else:
            return [{
                "name": "Unknown",
                "version": "-",
                "architecture": "-",
                "description": "Unsupported package manager"
            }]
    except Exception as e:
        return [{
            "name": "Error",
            "version": "-",
            "architecture": "-",
            "description": f"Failed to retrieve packages: {str(e)}"
        }]
    
# write the inventory to a file
# todo: handle the different field names from rpm and dpkg
packages = get_installed_packages()
with open("installed_packages.txt", "a", encoding="utf-8") as f:  # 'a' = append mode
    for pkg in packages:
        f.write(f"name: {pkg['name']} | version: {pkg['version']} | architecture: {pkg['architecture']} | description: {pkg['description']}\n")

