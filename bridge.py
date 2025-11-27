import argparse
import subprocess
import threading
import sys
import time
import os
import signal
import ctypes
import msvcrt

# Importer les chemins des binaires depuis le fichier séparé
from bridge_paths import SERVER_BINARY, TESTER_BINARY

# ------------------------------
# Fonctions Windows spécifiques
# ------------------------------
kernel32 = ctypes.windll.kernel32

def peek_pipe(pipe):
    """Retourne le nombre d'octets disponibles à lire dans le pipe."""
    handle = msvcrt.get_osfhandle(pipe.fileno())
    avail = ctypes.c_ulong(0)
    res = kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None)
    if res == 0:
        return 0
    return avail.value

def read_available(pipe):
    """Lit tout ce qui est disponible dans le pipe."""
    n = peek_pipe(pipe)
    if n > 0:
        return os.read(pipe.fileno(), n)
    return b""

# ------------------------------
# Forward
# ------------------------------
def forward(src, dst, name, verbose=False, stop_event=None):
    """
    Forward tout ce qui est disponible de src vers dst.
    """
    try:
        while not (stop_event and stop_event.is_set()):
            data = read_available(src)
            if not data:
                time.sleep(0.01)
                continue
            if verbose:
                print(f"[{name}] {data.decode(errors='replace').rstrip()}")
            try:
                dst.write(data)
                dst.flush()
            except Exception:
                break
    except Exception:
        pass

# ------------------------------
# Stop process
# ------------------------------
def stop_process(p):
    """Stop process with pipes closing"""
    if p is None:
        return

    if p.poll() is not None:
        return

    try:
        if p.stdin:
            p.stdin.close()
    except Exception:
        pass

    try:
        os.kill(p.pid, signal.CTRL_BREAK_EVENT)
    except Exception:
        try:
            p.terminate()
        except Exception:
            pass

    try:
        p.wait(timeout=2)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass

    try:
        if p.stdout:
            p.stdout.close()
    except Exception:
        pass
    try:
        if p.stderr:
            p.stderr.close()
    except Exception:
        pass

# ------------------------------
# Main
# ------------------------------
def main():
    parser = argparse.ArgumentParser(description="Bridge server <-> tester")
    parser.add_argument("filepath", help="Project Path")
    parser.add_argument("--application-id", help="Application ID sent only to server")
    parser.add_argument("--debug", action="store_true", help="Only for tester")
    parser.add_argument("--extra", nargs=argparse.REMAINDER, help="others sent to both")
    parser.add_argument("-V", "--verbose", action="store_true", help="Show all stdin stdout exchanges")

    args = parser.parse_args()

    server_cmd = [SERVER_BINARY, args.filepath]
    tester_cmd = [TESTER_BINARY, args.filepath]

    if args.application_id:
        server_cmd += ["--application-id", args.application_id]
    if args.debug:
        tester_cmd.append("--debug")
    if args.extra:
        server_cmd += args.extra
        tester_cmd += args.extra

    print("SERVER CMD :", server_cmd)
    print("TESTER CMD :", tester_cmd)

    server = None
    tester = None
    stop_event = threading.Event()

    try:
        server = subprocess.Popen(
            server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        tester = subprocess.Popen(
            tester_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )

        # Threads forward
        threads = [
            threading.Thread(target=forward, args=(server.stdout, tester.stdin, "Srv->Tst", args.verbose, stop_event), daemon=True),
            threading.Thread(target=forward, args=(tester.stdout, server.stdin, "Tst->Srv", args.verbose, stop_event), daemon=True),
            threading.Thread(target=forward, args=(server.stderr, sys.stdout.buffer, "Srv->ERR", args.verbose, stop_event), daemon=True),
            threading.Thread(target=forward, args=(tester.stderr, sys.stdout.buffer, "Tst->ERR", args.verbose, stop_event), daemon=True)
        ]
        for t in threads:
            t.start()

        # Boucle principale non bloquante
        while True:
            if server.poll() is not None and tester.poll() is not None:
                break
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[CTRL+C] Stop Requested by user")
    finally:
        stop_event.set()
        print("Processes Cleanup...")
        stop_process(server)
        stop_process(tester)
        print("Ended.")

if __name__ == "__main__":
    main()
