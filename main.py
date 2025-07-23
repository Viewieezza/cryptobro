import subprocess
import time

def run_script(script_name):
    try:
        result = subprocess.run(["python", script_name], capture_output=True, text=True)
        print(f"Output of {script_name}:\n{result.stdout}")
        if result.stderr:
            print(f"Log output of {script_name}:\n{result.stderr}")
    except Exception as e:
        print(f"Error running {script_name}: {e}")

def main():
    scripts = [
        "cc_wallet_6165.py",
        "cc_wallet_1945.py",
        "cc_wallet_289.py",
        "cc_wallet_16.py",
        "cc_wallet_789.py"
    ]

    for script in scripts:
        print(f"Running {script}...")
        run_script(script)
        print(f"Execution script {script} done...")
        time.sleep(60)

if __name__ == "__main__":
    main()
