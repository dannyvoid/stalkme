import os
import ctypes
import time
import platform


def get_size_os_path(file_path):
    return os.path.getsize(file_path)


def get_size_os_stat(file_path):
    return os.stat(file_path).st_size


def get_size_ctypes(file_path):
    if platform.system() == "Windows":

        class LARGE_INTEGER(ctypes.Union):
            _fields_ = [
                ("LowPart", ctypes.c_uint),
                ("HighPart", ctypes.c_int),
                ("QuadPart", ctypes.c_longlong),
            ]

        class FILETIME(ctypes.Structure):
            _fields_ = [
                ("dwLowDateTime", ctypes.c_uint),
                ("dwHighDateTime", ctypes.c_uint),
            ]

        class WIN32_FILE_ATTRIBUTE_DATA(ctypes.Structure):
            _fields_ = [
                ("dwFileAttributes", ctypes.c_uint),
                ("ftCreationTime", FILETIME),
                ("ftLastAccessTime", FILETIME),
                ("ftLastWriteTime", FILETIME),
                ("nFileSizeHigh", ctypes.c_uint),
                ("nFileSizeLow", ctypes.c_uint),
            ]

        data = WIN32_FILE_ATTRIBUTE_DATA()
        GetFileAttributesEx = ctypes.windll.kernel32.GetFileAttributesExW
        GetFileAttributesEx.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_int,
            ctypes.POINTER(WIN32_FILE_ATTRIBUTE_DATA),
        ]
        GetFileAttributesEx.restype = ctypes.c_int

        if GetFileAttributesEx(file_path, 0, ctypes.byref(data)):
            return (data.nFileSizeHigh << 32) + data.nFileSizeLow
        else:
            raise ctypes.WinError()

    else:

        class Stat(ctypes.Structure):
            _fields_ = [
                ("st_dev", ctypes.c_ulong),
                ("st_ino", ctypes.c_ulong),
                ("st_nlink", ctypes.c_ulong),
                ("st_mode", ctypes.c_uint),
                ("st_uid", ctypes.c_uint),
                ("st_gid", ctypes.c_uint),
                ("st_rdev", ctypes.c_ulong),
                ("st_size", ctypes.c_long),
                ("st_blksize", ctypes.c_long),
                ("st_blocks", ctypes.c_long),
                ("st_atime", ctypes.c_long),
                ("st_atimensec", ctypes.c_long),
                ("st_mtime", ctypes.c_long),
                ("st_mtimensec", ctypes.c_long),
                ("st_ctime", ctypes.c_long),
                ("st_ctimensec", ctypes.c_long),
            ]

        stat = Stat()
        libc = ctypes.CDLL("libc.so.6")
        libc.stat(file_path.encode("utf-8"), ctypes.byref(stat))
        return stat.st_size


def time_function(func, file_path, iterations=1000):
    times = []
    result = None
    for _ in range(iterations):
        # Introduce a small delay to reduce the chance of caching influencing results
        time.sleep(0.001)

        # Ensure the file is accessed in a way that prevents caching optimizations
        with open(file_path, "rb") as f:
            f.read(1)

        start_time = time.time()
        result = func(file_path)
        end_time = time.time()
        times.append(end_time - start_time)
    average_time = sum(times) / iterations
    return result, average_time


def compare_methods(file_path, iterations=1000):
    results = {}

    result, avg_time = time_function(get_size_os_path, file_path, iterations)
    results["os.path.getsize"] = (result, avg_time)

    result, avg_time = time_function(get_size_os_stat, file_path, iterations)
    results["os.stat"] = (result, avg_time)

    result, avg_time = time_function(get_size_ctypes, file_path, iterations)
    results["ctypes"] = (result, avg_time)

    for method, (size, time_taken) in results.items():
        print(
            f"Method: {method}, Size: {size} bytes, Average Time taken: {time_taken:.10f} seconds"
        )

    # Find the fastest method
    fastest_method = min(results, key=lambda x: results[x][1])
    fastest_time = results[fastest_method][1]

    print(
        f"\nThe fastest method is {fastest_method} with an average time of {fastest_time:.10f} seconds."
    )

    return results


file_path = r"G:\.void.bz\persistent\log.csv"
compare_methods(file_path, iterations=10000)
