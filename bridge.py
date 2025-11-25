import argparse
import subprocess
import threading
import sys
import time
import os
import signal

def forward(src, dst, name, verbose=False, stop_event=None):
    """
    exchange src => dst.
    if verbose=True, show data in console.
    stop_event used to thread ending.
    """
    try:
        while not (stop_event and stop_event.is_set()):
            data = src.readline()
            if not data:
                break
            if verbose:
                print(f"[{name}] {data.decode(errors='replace').rstrip()}")
            try:
                dst.write(data)
                dst.flush()
            except Exception:
                break
    except Exception:
        pass
    finally:
        try:
            dst.flush()
        except Exception:
            pass

def stop_process(p):
    """Stop process with pipes closing"""
    if p is None:
        return

    if p.poll() is not None:
        return  # déjà terminé

    # fermer stdin
    try:
        if p.stdin:
            p.stdin.close()
    except Exception:
        pass

    # envoyer signal propre
    try:
        os.kill(p.pid, signal.CTRL_BREAK_EVENT)
    except Exception:
        try:
            p.terminate()
        except Exception:
            pass

    # attendre fin
    try:
        p.wait(timeout=2)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass

    # fermer stdout et stderr
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

def main():
    parser = argparse.ArgumentParser(description="Bridge server <-> tester")
    parser.add_argument("filepath", help="Project Path")
    parser.add_argument("--UUID", help="Project UUID")
    parser.add_argument("--debug", action="store_true", help="Only for tester")
    parser.add_argument("--extra", nargs=argparse.REMAINDER, help="others sent to both")
    parser.add_argument("-V", "--verbose", action="store_true", help="Show all stdin stdout exchanges")

    args = parser.parse_args()

    server_cmd = ["server/obj/server.exe", args.filepath]
    tester_cmd = ["tester/obj/tester.exe", args.filepath]

    if args.UUID:
        server_cmd += ["--UUID", args.UUID]
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

        # Threads forward avec stop_event pour terminer proprement
        threads = [
            threading.Thread(target=forward, args=(server.stdout, tester.stdin, "Srv->Tst", args.verbose, stop_event), daemon=True),
            threading.Thread(target=forward, args=(tester.stdout, server.stdin, "Tst->Srv", args.verbose, stop_event), daemon=True),
            threading.Thread(target=forward, args=(server.stderr, sys.stdout.buffer, "Srv->ERR", args.verbose, stop_event), daemon=True),
            threading.Thread(target=forward, args=(tester.stderr, sys.stdout.buffer, "Tst->ERR", args.verbose, stop_event), daemon=True)
        ]
        for t in threads:
            t.start()

        # Boucle non bloquante pour Ctrl+C
        while True:
            if server.poll() is not None and tester.poll() is not None:
                break
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[CTRL+C] Stop Requested by user")
    finally:
        stop_event.set()  # signaler aux threads de s'arrêter
        print("Processes Cleanup...")
        stop_process(server)
        stop_process(tester)
        print("Ended.")

if __name__ == "__main__":
    main()
