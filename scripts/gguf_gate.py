"""Read a remote GGUF header and report the type of each router tensor, without downloading the file."""
import struct, sys, urllib.request

# ggml_type IDs from ggml.h
TYPES = {0: 'F32', 1: 'F16', 2: 'Q4_0', 3: 'Q4_1', 6: 'Q5_0', 7: 'Q5_1', 8: 'Q8_0', 9: 'Q8_1', 10: 'Q2_K', 11: 'Q3_K', 12: 'Q4_K',
         13: 'Q5_K', 14: 'Q6_K', 15: 'Q8_K', 16: 'IQ2_XXS', 17: 'IQ2_XS', 18: 'IQ3_XXS', 19: 'IQ1_S', 20: 'IQ4_NL', 21: 'IQ3_S',
         22: 'IQ2_S', 23: 'IQ4_XS', 29: 'IQ1_M', 30: 'BF16'}


class Remote:
    def __init__(self, url):
        self.url, self.pos, self.buf, self.start = url, 0, b'', 0

    def need(self, n):
        end = self.pos + n
        if not (self.start <= self.pos and end <= self.start + len(self.buf)):
            if n > 64 * 1024 * 1024:  # no header field is this big; the file is probably not a GGUF
                sys.exit(f'header field of {n} bytes at offset {self.pos}, stopping')
            size = max(n, 32 * 1024 * 1024)
            req = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-{self.pos + size - 1}', 'User-Agent': 'x'})
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status != 206:  # the server ignored Range and would send the whole file
                    sys.exit(f'server answered {resp.status} instead of 206 Partial Content, stopping')
                got = resp.headers.get('Content-Range', '')
                if not got.startswith(f'bytes {self.pos}-'):  # the server sent a different slice
                    sys.exit(f'asked for bytes from {self.pos}, server sent {got!r}, stopping')
                self.buf = resp.read(size)
            if len(self.buf) < n:
                sys.exit(f'needed {n} bytes at offset {self.pos}, got {len(self.buf)}: file ends early')
            self.start = self.pos

    def read(self, n):
        self.need(n)
        o = self.pos - self.start
        self.pos += n
        return self.buf[o:o + n]

    def u32(self): return struct.unpack('<I', self.read(4))[0]
    def u64(self): return struct.unpack('<Q', self.read(8))[0]
    def s(self): return self.read(self.u64())


SIZES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}


def skip(r, t):
    if t == 8:
        r.s()
    elif t == 9:
        et, n = r.u32(), r.u64()
        if et == 8:
            for _ in range(n):
                r.s()
        else:
            r.pos += SIZES[et] * n
    else:
        r.pos += SIZES[t]


def main(url):
    r = Remote(url)
    assert r.read(4) == b'GGUF'
    r.u32()
    nt, nkv = r.u64(), r.u64()
    nextn = None
    for _ in range(nkv):
        k, t = r.s(), r.u32()
        if k.endswith(b'nextn_predict_layers') and t == 4:
            nextn = r.u32()
        else:
            skip(r, t)
    gates, block = {}, 0
    for _ in range(nt):
        name = r.s().decode()
        nd = r.u32()
        for _ in range(nd):
            r.u64()
        ty = r.u32()
        r.u64()
        if name.startswith('blk.'):
            block = max(block, int(name.split('.')[1]))
        if name.endswith('.ffn_gate_inp.weight'):
            gates[int(name.split('.')[1])] = TYPES.get(ty, str(ty))
    print(f'blocks {block + 1}, nextn_predict_layers {nextn}, gate types {sorted(set(gates.values()))}, last gate {gates.get(block)}')


main(sys.argv[1])
