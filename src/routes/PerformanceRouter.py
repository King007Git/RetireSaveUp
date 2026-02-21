from fastapi import APIRouter
import psutil
import os
import time
from datetime import timedelta

from config import settings
from comms import START_TIME

router = APIRouter(
    prefix=f"/blackrock/challenge/{settings.VERSION}",
    tags=['Performance Report']
)

@router.get(f"/blackrock/challenge/{settings.VERSION}/performance")
def get_performance():
    """
    Reports system execution metrics including uptime, memory usage, 
    and the number of active threads used by the process.
    """
    process = psutil.Process(os.getpid())
    
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / (1024 * 1024)
    formatted_memory = f"{memory_mb:.2f} MB"
    
    threads = process.num_threads()
    
    uptime_seconds = time.time() - START_TIME
    uptime_td = timedelta(seconds=uptime_seconds)
    
    hours, remainder = divmod(uptime_td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = uptime_td.microseconds // 1000
    
    formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
    return {
        "time": formatted_time,
        "memory": formatted_memory,
        "threads": threads
    }