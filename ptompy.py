"""
ptompy - Python translation of ptom.c: convert MATLAB .p (p-code) files to .m source.
Compatible with main.py API: init, parse.

Decoding process (minimal flowchart):

    .p file
        |
        v
    +------------------+
    | _read_pfile      |  read 32-byte header, payload
    +--------+---------+
             |
             v
    +------------------+
    | _descramble     |  XOR payload with table
    +--------+---------+
             |
             v
    +------------------+
    | uncompress       |  raw -> decompressed bytes (stdlib zlib)
    +--------+---------+
             |
             v
    +------------------+
    | _decode_bytecode_to_source | 7 token counts + name table + bytecode
    |                  |  -> decode bytecode to .m source text
    +--------+---------+
             |
             v
    .m file (written)
"""

import os
import struct
import sys
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
import zlib

from matlab_formatter import Formatter as MatlabFormatter

__version__ = "1.0"

# Scramble table  (c_scramble_table[256])
S_SCRAMBLE_TBL = [
    0x050F0687, 0xC3F63AB0, 0x2E022A9C, 0x036DAA8C, 0x32ED8AE2, 0xF5571876, 0xC66FE7F3, 0x6CF0D7C0,
    0xBE08BA59, 0x0CBB32BE, 0x2E1E76F9, 0x5B095029, 0xD7B83753, 0xB949C2EA, 0x002B7101, 0x10BF6F59,
    0x5A565564, 0xCF31F672, 0x49B64869, 0x30B5AE91, 0x33D84C72, 0xE4B5B87D, 0x97EF0BD8, 0x58A53999,
    0xA2D54211, 0x040D16F3, 0x8ED0F2AB, 0xA1123692, 0x7CAD41FD, 0x47FD2EE5, 0xD5B56675, 0x01BC4884,
    0x8BF36995, 0x83B79111, 0x8529F311, 0x3EE0F477, 0x790EA987, 0x4B99DB04, 0x2BD1CC37, 0x371763E1,
    0x58550DC3, 0xD9F04330, 0x1220B40A, 0xB00D4516, 0x133A061B, 0x924C250C, 0x40CCB470, 0x6D905B7F,
    0x617E1B7E, 0x0A82FCD9, 0x1E460A11, 0x155667F0, 0x6F38B557, 0x363515E9, 0x6DFBA189, 0x920DF768,
    0x3A422CDD, 0x7CCC9435, 0xB3202DFB, 0x36EF6EDA, 0x44C9C31A, 0x08D59470, 0xB8ABB75E, 0x50BD2CAF,
    0x8C8D2582, 0x3DD5AA6F, 0x0F9E2126, 0x059BCF09, 0x096F8574, 0x3B6FED5D, 0x3CB332EA, 0x61C49337,
    0x9560308D, 0x4ED3E6F5, 0x91D1D84D, 0xA89A36A8, 0xE1200C01, 0xD29E8CBD, 0x162A9228, 0x429E277F,
    0x5D218997, 0x34709C39, 0x57F48F70, 0x4C5A3EEE, 0x6AA5B222, 0xC5F030F9, 0xDE683656, 0xA4E7DEFF,
    0xC2BCC52E, 0x11886451, 0xDBD74DD9, 0x87868848, 0x1A5DF8C2, 0x14830538, 0xD843B4F7, 0x26EB1E44,
    0x5258AFA7, 0xE7E1D61D, 0x2C86ED4D, 0x5BC8351B, 0x2351C37A, 0x693A2038, 0x3D8CC852, 0xB8B1F408,
    0x380E072D, 0x4F5EA0A0, 0xE14C2AB0, 0x192E132E, 0xA1FD2D5D, 0xF776BCD8, 0x5BCC3AAD, 0xFF1EB6F4,
    0xABE75911, 0x33C0CA1D, 0xCB78F5E2, 0x168D0B34, 0xF9B0FB17, 0xA9E12C39, 0xBB74EA33, 0x3C6DC045,
    0xBB69908A, 0x174C380D, 0x43F4488E, 0x55C7894C, 0xABCF3D45, 0x9C37FD85, 0x7CB2A790, 0xFE27ECEC,
    0x8419D3A3, 0x293994DE, 0x59F02208, 0xA76B971D, 0x1273B516, 0x177CEA5A, 0x601D8B25, 0x4A81BC43,
    0x66DB8AFA, 0xC169B5D6, 0x63AFCF71, 0x08D8B858, 0x38E072AE, 0x3F7C0A1E, 0x87F76F4C, 0x64C7CBC0,
    0xF33CD43C, 0xD370652F, 0x7B54D6F4, 0x6CEDCF53, 0x7D519168, 0xB6C9C127, 0xA95B8F98, 0xB8BB21F2,
    0xCE15F934, 0xED4FD826, 0x8E82AB3F, 0x79E53679, 0x0987D5AC, 0x8B3552CF, 0x780D2366, 0x8DA1A94F,
    0xB46EE7AD, 0x51FD456E, 0x350D406C, 0xC6E29CC3, 0x697A2FC8, 0x952ACB92, 0x11645906, 0xD055BAC3,
    0x56948168, 0x75142877, 0xD92E731B, 0x8F74F416, 0xB4903296, 0x6125E267, 0xF43CBFD6, 0x27CD06D2,
    0xB4964796, 0xEF9196CA, 0x14BAD625, 0xB1E7D8FE, 0x265B57F2, 0xBE1665BD, 0xEAA2FAF1, 0xF4715126,
    0x2B663DE4, 0x7925A630, 0x6E5687A0, 0xB4EE1390, 0x045AF8FF, 0x6663AB06, 0x428FBCDF, 0xB8C9E0AD,
    0x3860F074, 0xF79CFD4B, 0xFFAC7D70, 0x21DB203C, 0x0CC7C8DD, 0x9110D677, 0xF230DAFF, 0x635C4A45,
    0x8624FEEE, 0x4B5F4E1A, 0xF2D13E5C, 0x3AB53184, 0xAC853082, 0x670DFE32, 0x62823856, 0x611B7818,
    0xD69F94FD, 0xF73D0E7B, 0x13035117, 0xFCFAECEF, 0x35537439, 0xFDA64C08, 0xF16C3E15, 0xE0B9B21D,
    0xF6CBF238, 0xDFC2C5B5, 0x15A7C5AD, 0xFB26EB37, 0xC62670BB, 0x5837828C, 0xB3F0CBE4, 0xFE87612F,
    0xCFD47FD7, 0x339D4955, 0xA062816C, 0xDC9C48B5, 0xC4AE1FCC, 0x92935C6B, 0x3FF892FA, 0x4AD31EBA,
    0xDDF2AA86, 0xB2C9D156, 0x8588503F, 0x0A77DB08, 0x19D7CF89, 0xE80A8895, 0xEB935320, 0xF0776486,
    0x5F479711, 0xFE96A437, 0xED725175, 0x949B0B4A, 0x7C3CF03F, 0x5EDE8F8A, 0x7554BD67, 0xF308E277,
    0xBEA15540, 0x0AFC8314, 0xEE2FCDAF, 0x04C7C5FB, 0x633405A0, 0x22209993, 0x834F272B, 0x33088577,
]

# Token strings from ptom.c (c_token_table[134]); bytecode uses indices 0..NUM_1BYTE_TOKENS-1 for 1-byte tokens
S_TOKEN = [
    "", "function ", "function ", "if ", "switch", "try", "while", "for ", "end", "else ", "elseif ",
    "break", "return ", "parfor", "",
    "global ", "persistent ", "", "", "", "catch ", "continue ",  "case ", "otherwise", "", "classdef ", 
    "", "", "properties ", "", "methods ", "events ",
    "enumeration ", "spmd ", "parsection ", "section ", "", "", "", "", "id ", "end", "int ",
    "float ", "string ", "dual ", "bang ", "?", "", "", "; ", ",", "(", ")", "[", "]", "{", "}",
    "feend ", "", "' ", ".'", "~", "@", "$", "`", '"', "", "", "", "+", "-", "*", "/", "\\",  # 61: p-code dottrans → MATLAB .'
    "^", ":", "", "", "", ".", ".*", "./", ".\\", ".^", "&", "|", "&&", "||", "<", ">", "<=", ">=",
    "==", "~=", "=", "cne ", "arrow ",
    "", "", "\n", "\n ", "\n ", "...\n    ", "", "comment ",
    "blkstart ", "blkcom ", "blkend ", "cpad ", "pragma ", "...", "..", "deep_nest ", "deep_stmt ",
    "", "white ", "", "negerr ", "semerr ", "eolerr ", "unterm ", "badchar ", "deep_paren ",
    "fp_err ", "res_err ", "deep_com ", "begin_type ", "end_type ", "string_literal ",
    "unterm_string_literal ", "arguments_block ", "last_token ", "",
]
NUM_1BYTE_TOKENS = len(S_TOKEN)  # 134; bytecode: if byte < NUM_1BYTE_TOKENS then 1-byte token else 2-byte

S_MINOR_VERSION = b"v00.00"

# Keyword token indices (1-byte): add space after identifier when next token is identifier or one of these.
_NEED_SPACE_AFTER_IDENT = frozenset[int]({
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,            # function if switch try while for end else elseif break return parfor
    15, 16, 20, 21, 22, 23, 24, 25,                       # global persistent catch continue case otherwise classdef
    28, 30, 31, 32, 33, 34, 35, 39, 40, 41, 42, 43, 44,   # properties methods events enumeration spmd parsection section id end int float string dual bang
    57, 103, 104,                                         # feend cne arrow
})




def init() -> bool:
    """Initialize the converter. Returns True (zlib is checked at import)."""
    return True


@dataclass
class PFileData:
    """Parsed .p file header and payload."""
    path: str
    minor: bytes
    scramble: int
    size_after_compass: int
    size_befor_compass: int
    pdata: bytes


@dataclass
class UncompressedData:
    """Decompressed .p file data (tokens and bytecode)."""
    tokens: list
    mdata: bytes


@dataclass
class MFileData:
    """Decoded MATLAB source code."""
    path: str
    source: str


def _descramble(pfile_data: PFileData) -> bytes:
    """Undo scramble: XOR pdata (u32 words) with table. Returns descrambled bytes."""
    scramble_number = (pfile_data.scramble >> 12) & 0xFF
    pdata = pfile_data.pdata
    n = len(pdata) // 4
    words = list(struct.unpack("<%dI" % n, pdata[: n * 4]))
    words = [w ^ S_SCRAMBLE_TBL[(i + scramble_number) & 0xFF] for i, w in enumerate(words)]
    out = struct.pack("<%dI" % n, *words)
    # Append trailing bytes (payload not always multiple of 4) so zlib gets full stream
    if len(pdata) > n * 4:
        out += pdata[n * 4 :]
    return out


def _read_pfile(ppath: str) -> Optional[PFileData]:
    """
    Read .p file (header + payload). No validation.
    Returns PFileData or None if file missing or < 32 bytes.

    P-file header format (32 bytes, then compressed payload):
      Offset   Size  Field
      ------   ----  -----
      0        6     major version (e.g. b"v01.00")
      6        6     minor version (e.g. b"v00.00"); must match S_MINOR_VERSION
      12       4     scramble key (u32 big-endian); used for XOR descramble
      16       4     crc (u32, unused) ???
      20       4     uk2 (u32, unused) ???
      24       4     size_after_compass (u32 big-endian); payload length in file
      28       4     size_befor_compass (u32 big-endian); expected size after zlib decompress
      ------   ----
      32       N     pdata (scrambled, zlib-compressed); N = size_after_compass
    """
    pp = Path(ppath)
    if not pp.exists():
        raise FileNotFoundError(f".p file not found: {ppath}")
    
    data = pp.read_bytes()
    if len(data) < 32:
        raise ValueError(f".p file has no header (<32 bytes): {ppath}")
    size_after_compass = int.from_bytes(data[24:28], "big")
    # Use full remainder as payload; some .p files have payload longer than header says
    pdata = data[32:]
    minor = data[6:12]
    scramble = int.from_bytes(data[12:16], "big")
    size_befor_compass = int.from_bytes(data[28:32], "big")

    return PFileData(
        path=ppath,
        minor=minor,
        scramble=scramble,
        size_after_compass=size_after_compass,
        size_befor_compass=size_befor_compass,
        pdata=pdata,
    )


def _extract_tokens_from_decompressed(data: bytes) -> list:
    """
    Extract 7 token counts from first 28 bytes of decompressed data.
    Each token count is a 4-byte big-endian integer.
    """
    return [int.from_bytes(data[i * 4 : i * 4 + 4], "big") for i in range(7)]


def _uncompress_pfile(pfile_data: PFileData) -> Optional[UncompressedData]:
    """
    Descramble and zlib-decompress pdata. Returns UncompressedData or None.
    """
    decrypted = _descramble(pfile_data)
    try:
        tmp = zlib.decompress(decrypted)
    except Exception:
        return None
    if len(tmp) < pfile_data.size_befor_compass:
        return None
    tokens = _extract_tokens_from_decompressed(tmp)
    mdata = tmp[28:]  # Token data is 7*4 = 28 bytes
    return UncompressedData(tokens=tokens, mdata=mdata)


def _parse_name_table(tokens: list, mdata: bytes) -> Optional[tuple]:
    """
    Extract and decode the name table from mdata.
    Returns (slot, code_start_pos) where slot is list of decoded names,
    or None if parsing fails.
    """
    slot = []
    pos = 0
    for i in range(7):
        for _ in range(tokens[i]):
            end = mdata.find(b"\x00", pos)
            if end == -1:
                return None
            slot.append(mdata[pos:end].decode("utf-8", errors="replace"))
            pos = end + 1
    return (slot, pos)


def _decode_bytecode_tokens(code: bytes, slot: list) -> Optional[list]:
    """
    Decode bytecode into token strings.
    Returns list of output parts or None on failure.
    """
    end_ptr = len(code)
    out_parts = []
    cur = 0
    while cur < end_ptr:
        if (code[cur] & 0x80) != 0:
            # 2-byte code (identifier / slot ref)
            res_id = 128 + 256 * ((code[cur] & 0x7F) - 1) + code[cur + 1]
            if res_id >= len(slot):
                return None
            name_ptr = slot[res_id]
            out_parts.append(name_ptr)
            next_cur = cur + 2
            # Space only when next is identifier (2-byte) or keyword (1-byte in _NEED_SPACE_AFTER_IDENT)
            if next_cur < end_ptr and ((code[next_cur] & 0x80) != 0 or code[next_cur] in _NEED_SPACE_AFTER_IDENT):
                out_parts.append(" ")
            cur = next_cur
            continue
        if code[cur] < NUM_1BYTE_TOKENS:
            # 1-byte code: index into S_TOKEN (no space added after; spacing only after slot ref above)
            name_ptr = S_TOKEN[code[cur]]
            if len(name_ptr) != 0:
                out_parts.append(name_ptr)
            cur += 1
            continue
        # Unknown code
        return None
    return out_parts


def _decode_bytecode_to_source(tokens: list, mdata: bytes, mpath: str = "") -> Optional[MFileData]:
    """
    Decode decompressed bytecode (name table + token stream) to MATLAB source.
    tokens: list of 7 counts of names per group.
    mpath: path for the output .m file (stored in MFileData.path).
    Returns MFileData or None on failure.
    """

    slot, code_start = _parse_name_table(tokens, mdata)
    code = mdata[code_start:]
    
    out_parts = _decode_bytecode_tokens(code, slot)
    
    return MFileData(path=mpath, source="".join(out_parts))


def _write_mfile(mfile_data: MFileData) -> bool:
    """Write decoded MATLAB source to file (formatted via matlab_formatter)."""
    path = Path(mfile_data.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    formatter = MatlabFormatter(
        indentwidth=4,
        separateBlocks=True,
        indentMode=1,  # all_functions
    )
    formatted = formatter.format_source(mfile_data.source)
    path.write_text(formatted, encoding="utf-8")
    return True


def _validate_pfile_data(pfile_data: PFileData) -> bool:
    """
    Validate parsed p-file data for integrity.
    Returns True if valid, False otherwise.
    """
    return (
        pfile_data.size_after_compass > 0
        and pfile_data.size_befor_compass > 0
        and pfile_data.minor == S_MINOR_VERSION # True ? always?
        and len(pfile_data.pdata) == pfile_data.size_after_compass
    )


def parse(pfile: str, mfile: str) -> Tuple[int, str]:
    """
    Convert a MATLAB .p file to .m source.
    :param pfile: Path to the .p (p-code) file
    :param mfile: Path to the output .m file
    :return: (code, msg) — code 0 = success, non-zero = error; msg is displayable in GUI/TUI.
    """
    try:
        # Read and validate .p file
        pfile_data = _read_pfile(pfile)
        if not pfile_data or not _validate_pfile_data(pfile_data):
            return (2, "Invalid p-file or decompression failed.")

        # Decompress and extract tokens
        uncompressed = _uncompress_pfile(pfile_data)

        # Decode bytecode to .m source
        mfile_data = _decode_bytecode_to_source(
            uncompressed.tokens, uncompressed.mdata, mpath=mfile
        )

        # Write output file
        if not _write_mfile(mfile_data):
            return (3, "Failed to write .m file.")

        return (0, f"Saved to {mfile}")
    except KeyboardInterrupt:
        return (1, "Cancelled by user (Ctrl+C)")
    except Exception as e:
        return (1, str(e))
