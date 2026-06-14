"""Windows taskbar integration helpers."""
from __future__ import annotations

import ctypes
import sys
import uuid
from pathlib import Path

from aica.app_commands import COMMAND_ARG, COMMAND_CAPTURE
from aica.paths import icon_file, project_root
from aica.runtime import PLATFORM_WINDOWS, current_platform


def _resolve_taskbar_executable() -> str:
    executable = Path(sys.executable or "").resolve()
    return str(executable)


def _resolve_taskbar_prefix(executable: str | None = None) -> tuple[str, str]:
    executable = executable or _resolve_taskbar_executable()
    if getattr(sys, "frozen", False):
        return executable, ""
    launcher = project_root() / "run_aica.py"
    return executable, f'"{launcher}" '


def build_taskbar_tasks(executable: str | None = None) -> list[dict[str, str]]:
    executable, argument_prefix = _resolve_taskbar_prefix(executable)
    icon_path = str(icon_file(PLATFORM_WINDOWS))
    return [
        {
            "title": "开始截图",
            "path": executable,
            "arguments": f"{argument_prefix}{COMMAND_ARG} {COMMAND_CAPTURE}",
            "icon": icon_path,
        },
    ]


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    def __init__(self, value: str):
        parsed = uuid.UUID(value)
        super().__init__(
            parsed.time_low,
            parsed.time_mid,
            parsed.time_hi_version,
            (ctypes.c_ubyte * 8)(*parsed.bytes[8:]),
        )


class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [
        ("fmtid", _GUID),
        ("pid", ctypes.c_ulong),
    ]


class _PROPVARIANT_UNION(ctypes.Union):
    _fields_ = [
        ("pwszVal", ctypes.c_wchar_p),
    ]


class _PROPVARIANT(ctypes.Structure):
    _anonymous_ = ("value",)
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("wReserved1", ctypes.c_ushort),
        ("wReserved2", ctypes.c_ushort),
        ("wReserved3", ctypes.c_ushort),
        ("value", _PROPVARIANT_UNION),
    ]


def _succeeded(result: int) -> bool:
    return result >= 0


def _com_method(obj, index: int, restype, *argtypes):
    prototype = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    vtable = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return prototype(vtable[index])


def _release(obj) -> None:
    if obj:
        _com_method(obj, 2, ctypes.c_ulong)(obj)


def _check(result: int, message: str) -> None:
    if not _succeeded(result):
        raise OSError(result, message)


def _set_shell_link_title(shell_link, title: str) -> None:
    property_store = ctypes.c_void_p()
    _check(
        _com_method(
            shell_link,
            0,
            ctypes.c_long,
            ctypes.POINTER(_GUID),
            ctypes.POINTER(ctypes.c_void_p),
        )(
            shell_link,
            ctypes.byref(_GUID("{00000138-0000-0000-C000-000000000046}")),
            ctypes.byref(property_store),
        ),
        "IShellLinkW.QueryInterface(IPropertyStore) failed",
    )
    try:
        title_key = _PROPERTYKEY(
            _GUID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"),
            2,
        )
        title_value = _PROPVARIANT()
        title_value.vt = 31  # VT_LPWSTR
        title_value.pwszVal = title
        _check(
            _com_method(
                property_store,
                5,
                ctypes.c_long,
                ctypes.POINTER(_PROPERTYKEY),
                ctypes.POINTER(_PROPVARIANT),
            )(
                property_store,
                ctypes.byref(title_key),
                ctypes.byref(title_value),
            ),
            "IPropertyStore.SetValue(System.Title) failed",
        )
        _check(
            _com_method(property_store, 6, ctypes.c_long)(property_store),
            "IPropertyStore.Commit failed",
        )
    finally:
        _release(property_store)


def _co_create_instance(clsid: str, iid: str):
    ole32 = ctypes.windll.ole32
    obj = ctypes.c_void_p()
    result = ole32.CoCreateInstance(
        ctypes.byref(_GUID(clsid)),
        None,
        1,  # CLSCTX_INPROC_SERVER
        ctypes.byref(_GUID(iid)),
        ctypes.byref(obj),
    )
    _check(result, "CoCreateInstance failed")
    return obj


def _create_shell_link(task: dict[str, str]):
    shell_link = _co_create_instance(
        "{00021401-0000-0000-C000-000000000046}",
        "{000214F9-0000-0000-C000-000000000046}",
    )
    try:
        _check(
            _com_method(shell_link, 20, ctypes.c_long, ctypes.c_wchar_p)(shell_link, task["path"]),
            "IShellLinkW.SetPath failed",
        )
        _check(
            _com_method(shell_link, 11, ctypes.c_long, ctypes.c_wchar_p)(shell_link, task["arguments"]),
            "IShellLinkW.SetArguments failed",
        )
        _check(
            _com_method(shell_link, 7, ctypes.c_long, ctypes.c_wchar_p)(shell_link, task["title"]),
            "IShellLinkW.SetDescription failed",
        )
        _set_shell_link_title(shell_link, task["title"])
        _check(
            _com_method(shell_link, 17, ctypes.c_long, ctypes.c_wchar_p, ctypes.c_int)(
                shell_link,
                task["icon"],
                0,
            ),
            "IShellLinkW.SetIconLocation failed",
        )
    except Exception:
        _release(shell_link)
        raise
    return shell_link


def _create_object_collection(tasks: list[dict[str, str]]):
    collection = _co_create_instance(
        "{2D3468C1-36A7-43B6-AC24-D3F02FD9607A}",
        "{5632B1A4-E38A-400A-928A-D4CD63230295}",
    )
    links = []
    try:
        add_object = _com_method(collection, 5, ctypes.c_long, ctypes.c_void_p)
        for task in tasks:
            link = _create_shell_link(task)
            links.append(link)
            _check(add_object(collection, link), "IObjectCollection.AddObject failed")
        return collection
    except Exception:
        _release(collection)
        raise
    finally:
        for link in links:
            _release(link)


def _install_jump_list(tasks: list[dict[str, str]]) -> None:
    ole32 = ctypes.windll.ole32
    coinit = ole32.CoInitialize(None)
    destination_list = None
    collection = None
    removed_destinations = ctypes.c_void_p()
    try:
        if coinit not in (0, 1, -2147417850):  # S_OK, S_FALSE, RPC_E_CHANGED_MODE
            _check(coinit, "CoInitialize failed")
        destination_list = _co_create_instance(
            "{77F10CF0-3DB5-4966-B520-B7C54FD35ED6}",
            "{6332DEBF-87B5-4670-90C0-5E57B408A49E}",
        )
        slots = ctypes.c_uint()
        _check(
            _com_method(
                destination_list,
                4,
                ctypes.c_long,
                ctypes.POINTER(ctypes.c_uint),
                ctypes.POINTER(_GUID),
                ctypes.POINTER(ctypes.c_void_p),
            )(
                destination_list,
                ctypes.byref(slots),
                ctypes.byref(_GUID("{92CA9DCD-5622-4BBA-A805-5E9F541BD8C9}")),
                ctypes.byref(removed_destinations),
            ),
            "ICustomDestinationList.BeginList failed",
        )
        collection = _create_object_collection(tasks)
        _check(
            _com_method(destination_list, 7, ctypes.c_long, ctypes.c_void_p)(destination_list, collection),
            "ICustomDestinationList.AddUserTasks failed",
        )
        _check(
            _com_method(destination_list, 8, ctypes.c_long)(destination_list),
            "ICustomDestinationList.CommitList failed",
        )
    finally:
        _release(removed_destinations)
        _release(collection)
        _release(destination_list)
        if coinit in (0, 1):
            ole32.CoUninitialize()


def install_windows_taskbar_tasks(
    *,
    platform_id: str | None = None,
    tasks: list[dict[str, str]] | None = None,
) -> bool:
    platform_id = platform_id or current_platform()
    if platform_id != PLATFORM_WINDOWS:
        return False
    if not hasattr(ctypes, "windll") or not hasattr(ctypes, "WINFUNCTYPE"):
        return False

    try:
        _install_jump_list(tasks or build_taskbar_tasks())
        return True
    except Exception:
        return False
