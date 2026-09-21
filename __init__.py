"""ComfyUI-Save_Audio_Numbered.

Saves audio as WAV with sequential 001/002 numbering, based on the CRT
"Save Audio With Path" node (plugcrypt / crt-nodes, MIT License).
"""

from .py.Save_Audio_With_Path_Numbered import (
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
