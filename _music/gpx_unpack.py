"""Unpack Guitar Pro 6 .gpx files: BCFZ decompression + GPX virtual filesystem extraction.

Ported from the alphaTab TypeScript reference (CoderLine/alphaTab, GpxFileSystem.cs / BitReader.cs).

Public API:
    extract_score_gpif(path) -> bytes   # returns the Content/score.gpif XML
"""
import struct


class BitReader:
    """MSB-first bit reader over a byte buffer."""
    def __init__(self, data):
        self.data = data
        self.pos = 0          # byte position
        self.cur = 0          # current byte buffer
        self.left = 0         # bits remaining in cur
        self._eof = False

    def _read_bit(self):
        if self.left == 0:
            if self.pos >= len(self.data):
                self._eof = True
                return 0
            self.cur = self.data[self.pos]
            self.pos += 1
            self.left = 8
        bit = (self.cur >> (self.left - 1)) & 1
        self.left -= 1
        return bit

    def read_bits(self, n):
        """MSB-first: first bit read is the most significant."""
        v = 0
        for i in range(n - 1, -1, -1):
            v |= self._read_bit() << i
        return v

    def read_bits_reversed(self, n):
        """LSB-first: first bit read is the least significant."""
        v = 0
        for i in range(n):
            v |= self._read_bit() << i
        return v

    def read_byte(self):
        return self.read_bits(8)

    def eof(self):
        return self._eof or (self.pos >= len(self.data) and self.left == 0)


def bcfz_decompress(data):
    """Decompress a BCFZ-compressed blob (header = b'BCFZ' + uint32_LE uncompressed length)."""
    assert data[:4] == b'BCFZ', f'not a BCFZ blob, got: {data[:4]!r}'
    expected_len = struct.unpack('<I', data[4:8])[0]
    reader = BitReader(data[8:])
    out = bytearray()

    while len(out) < expected_len and not reader.eof():
        flag = reader.read_bits(1)
        if reader.eof(): break
        if flag == 1:
            word_size = reader.read_bits(4)
            offset = reader.read_bits_reversed(word_size)
            size = reader.read_bits_reversed(word_size)
            if offset == 0 or size == 0: break   # malformed / end-of-stream
            source_pos = len(out) - offset
            to_read = min(offset, size)
            chunk = bytes(out[source_pos:source_pos + to_read])
            for i in range(size):
                out.append(chunk[i % to_read])
        else:
            size = reader.read_bits_reversed(2)
            for _ in range(size):
                if reader.eof(): break
                out.append(reader.read_byte())

    return bytes(out)


# === GPX virtual filesystem ===
# After BCFZ decompression, the payload is a sector-based file system.
#   Magic: 4 bytes 'BCFS'
#   Sector size: 0x1000 (4096 bytes); first sector is the FS header
#   File entries follow as 4096-byte blocks. Each file entry block starts with marker uint32=2,
#     then filename (127 bytes null-padded), file_size (uint32 LE), then list of sector indices.
SECTOR_SIZE = 0x1000


def _read_u32_le(buf, off):
    return struct.unpack('<I', buf[off:off+4])[0]


def gpx_fs_files(data):
    """Walk the GPX virtual filesystem. Yields (filename, content_bytes).

    Sector layout (4096 bytes each):
      Sector 0: FS header (just 'BCFS' magic at offset 0)
      Sector 1+: file or directory entries.
        File entry: marker(4) | type(4)=2 | name(127, null-padded, starts at +8) |
                    pad to +0x90 | file_size(4 LE) | pad(4) | sector indices(uint32 each, 0-terminated)
    """
    assert data[:4] == b'BCFS', f'not a BCFS blob, got: {data[:4]!r}'
    offset = SECTOR_SIZE
    while offset + 0x9C <= len(data):
        file_type = _read_u32_le(data, offset + 4)
        if file_type == 2:
            name_bytes = data[offset+8 : offset+8+127]
            null = name_bytes.find(b'\x00')
            name = name_bytes[:null if null >= 0 else 127].decode('utf-8', errors='replace')
            # Filter to plausible filenames (printable ASCII, non-empty)
            if name and all(0x20 <= b < 0x7f for b in name.encode('utf-8', errors='replace')):
                file_size = _read_u32_le(data, offset + 0x90)
                sector_indices = []
                list_off = offset + 0x98
                while list_off + 4 <= offset + SECTOR_SIZE:
                    idx = _read_u32_le(data, list_off)
                    if idx == 0: break
                    sector_indices.append(idx)
                    list_off += 4
                content = bytearray()
                for idx in sector_indices:
                    src = idx * SECTOR_SIZE
                    content.extend(data[src : src + SECTOR_SIZE])
                # First 4 bytes of the concatenated data are a sector-link prefix, not file content
                yield name, bytes(content[4 : 4 + file_size])
        offset += SECTOR_SIZE


def extract_score_gpif(path):
    """Open a .gpx file, decompress BCFZ, walk the GPX FS, return score.gpif bytes."""
    with open(path, 'rb') as f:
        raw = f.read()
    fs_data = bcfz_decompress(raw)
    for name, content in gpx_fs_files(fs_data):
        # The score XML is at 'Content/score.gpif' (sometimes leading '/')
        if name.endswith('score.gpif'):
            return content
    raise RuntimeError('score.gpif not found in GPX filesystem')


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2: print('usage: gpx_unpack.py <file.gpx>'); sys.exit(1)
    xml = extract_score_gpif(sys.argv[1])
    print(f'extracted score.gpif: {len(xml)} bytes')
    print(xml[:500].decode('utf-8', errors='replace'))
