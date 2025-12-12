import os
import sys
import fcntl
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class PIDLock:
    def __init__(self, lock_file: str = "server.lock"):
        self.lock_file = Path(lock_file).absolute()
        self.lock_fd = None

    def acquire(self) -> bool:
        """
        Acquire the lock. Returns True if successful, False if another instance is running.
        """
        try:
            self.lock_fd = open(self.lock_file, 'a+')
            # Try to acquire an exclusive lock (non-blocking)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write current PID
            self.lock_fd.seek(0)
            self.lock_fd.truncate()
            self.lock_fd.write(str(os.getpid()) + '\n')
            self.lock_fd.flush()
            
            # Keep the file open to maintain the lock
            return True
        except BlockingIOError:
            # Lock is held by another process
            return False
        except Exception as e:
            logger.error(f"Failed to acquire PID lock: {e}")
            return False

    def release(self):
        """
        Release the lock.
        """
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
                if self.lock_file.exists():
                    os.remove(self.lock_file)
            except Exception as e:
                logger.error(f"Failed to release PID lock: {e}")
            finally:
                self.lock_fd = None

def enforce_single_instance(lock_file: str = "server.lock"):
    """
    Enforce single instance execution. Exits if another instance is running.
    """
    lock = PIDLock(lock_file)
    if not lock.acquire():
        print(f"❌ Error: Another instance is already running (Lock: {lock_file})")
        print("   Please stop the existing process before starting a new one.")
        sys.exit(1)
    return lock
