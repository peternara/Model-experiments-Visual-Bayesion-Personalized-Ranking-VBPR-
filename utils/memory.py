import os

import GPUtil
import psutil
import torch
from humanize import naturalsize


def memory_report():
    # CPU RAM
    current_process = psutil.Process(os.getpid())
    print(f"Main process PID: {current_process.pid}")
    print(
        f"CPU RAM free: {naturalsize(psutil.virtual_memory().available)} | "
        f"Proc. size: {naturalsize(current_process.memory_info().rss)}"
    )
    for child in current_process.children(recursive=True):
        print(f">> Child {child.pid}: {naturalsize(child.memory_info().rss)}")
    # GPU RAM
    GPUs = GPUtil.getGPUs()
    if GPUs:
        for gpu in GPUs:
            print(f"GPU {gpu.id} ({gpu.name})")
            print(
                f"GPU RAM free: {gpu.memoryFree:.0f} MB | "
                f"Used: {gpu.memoryUsed:.0f} MB | "
                f"Util.: {gpu.memoryUtil*100:.0f}% | "
                f"Total: {gpu.memoryTotal:.0f} MB"
            )
    else:
        print("No GPU available")


def max_memory_stats(device=None):
    if not torch.cuda.is_available():
        print("No GPU available (unable to retrieve stats)")
        return
    if device is None:
        device = torch.device(torch.cuda.current_device())
    if isinstance(device, torch.device):
        print(f"Device: '{device}' (type: '{device.type}')")
        if device.type == "cpu":
            print("No GPU device (unable to retrieve stats)")
        else:
            print(f"Max memory allocated: {naturalsize(torch.cuda.max_memory_allocated(device))}")
            print(f"Max memory reserved:  {naturalsize(torch.cuda.max_memory_reserved(device))}")
    else:
        for d in device:
            max_memory_stats(device=d)
            print()


def reset_peak_memory_stats(device=None):
    if not torch.cuda.is_available():
        print("No GPU available (unable to reset stats)")
        return
    if device is None:
        device = torch.device(torch.cuda.current_device())
    if device.type == "cpu":
        print("No GPU device (unable to reset stats)")
        return
    if isinstance(device, torch.device):
        torch.cuda.reset_peak_memory_stats()
    else:
        for d in device:
            reset_peak_memory_stats(device=d)


if __name__ == '__main__':
    memory_report()
    print()
    max_memory_stats()
    print()
    reset_peak_memory_stats()
