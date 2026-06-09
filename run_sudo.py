#!/usr/bin/env python3
import sys, os, pty, select, termios, tty

def run_with_sudo(cmd, password):
    master, slave = pty.openpty()
    old = termios.tcgetattr(slave)
    old[3] |= termios.ECHO  # enable echo
    termios.tcsetattr(slave, termios.TCSANOW, old)
    pid = os.fork()
    if pid == 0:
        os.close(master)
        os.dup2(slave, 0); os.dup2(slave, 1); os.dup2(slave, 2)
        os.execvp('sudo', ['sudo', '-S', 'sh', '-c', cmd])
    else:
        os.close(slave)
        out = b''; sent = False
        try:
            while True:
                r, _, _ = select.select([master], [], [], 20)
                if not r: break
                data = os.read(master, 4096)
                out += data
                if not data: break
                sys.stderr.buffer.write(data)
                if not sent and b'[sudo] password' in data.lower():
                    os.write(master, (password + '\n').encode())
                    sent = True
        except OSError: pass
        os.close(master)
        pid2, st = os.waitpid(pid, 0)
        return out.decode('utf-8', errors='replace'), os.WEXITSTATUS(st)

if __name__ == '__main__':
    pwd = os.environ.get('SUDO_PASS', '')
    out, rc = run_with_sudo(sys.argv[1] if len(sys.argv)>1 else 'whoami', pwd)
    print(out)
    sys.exit(rc)
