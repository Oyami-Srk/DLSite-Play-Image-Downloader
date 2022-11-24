# DLSite Play Image rebuild PoC
import math
from ctypes import c_int, c_uint

from PIL import Image

# name = "80c7d564314c4c1671b8f40e359e21ba"
name = "91a94cf7e51953e8637313254a1e236d"


def name_to_seed(name: str) -> int:
    return int(name[5:12], 16)


# 梅森旋转算法
class Randomizer:
    N = 624
    M = 397
    MATRIX_A = 2567483615
    UPPER_MASK = 2147483648
    LOWER_MASK = 2147483647

    def __init__(self, seed: int):
        assert seed != 0  # otherwise e = (new Date).getTime(); in javascript
        # mt = array with N elements
        # mti = N + 1
        self.mt = []
        self.init_seed(seed)
        self.mti = self.N

    def init_seed(self, e: int):
        mt = [e >> 0]
        for i in range(1, self.N):
            v = mt[i - 1] ^ mt[i - 1] >> 30
            magic = (1812433253 *
                     (c_int(((4294901760 & v) >> 16) & 0x7FFFFFFF).value << 16)
                     + 1812433253 * (65535 & v) + i)
            mt.append(c_uint(magic & 0xFFFFFFFF).value)
        self.mt = mt

    def random(self):
        return self.random_int() * (1 / 4294967296)

    def random_int(self) -> int:
        t = [0, self.MATRIX_A]
        if self.mti >= self.N:
            if self.mti == self.N + 1:
                self.init_seed(5489)
            n = 0
            while n < self.N - self.M:
                e = self.mt[n] & self.UPPER_MASK | self.mt[n + 1] & self.LOWER_MASK
                self.mt[n] = self.mt[n + self.M] ^ e >> 1 ^ t[1 & e]
                n += 1
            while n < self.N - 1:
                e = self.mt[n] & self.UPPER_MASK | self.mt[n + 1] & self.LOWER_MASK
                self.mt[n] = self.mt[n + (self.M - self.N)] ^ e >> 1 ^ t[1 & e]
                n += 1
            e = self.mt[self.N - 1] & self.UPPER_MASK | self.mt[0] & self.LOWER_MASK
            self.mt[self.N - 1] = self.mt[self.M - 1] ^ e >> 1 ^ t[1 & e]
            self.mti = 0
        n = self.mt[self.mti]
        self.mti += 1
        n = n ^ n >> 11
        n = n ^ n << 7 & 2636928640
        n = n ^ n << 15 & 4022730752
        n = n ^ n >> 18
        return c_uint(n & 0xFFFFFFFF).value


def shuffle(seed: int) -> list[int]:
    randomizer = Randomizer(seed)
    result = list(range(0, 80))
    for i in range(79, 0, -1):
        r = randomizer.random()
        # print(r)
        j = math.floor(r * (i + 1))
        a = [result[j], result[i]]
        result[i] = a[0]
        result[j] = a[1]
    return result


def get_blocks(filename: str) -> list[Image]:
    img = Image.open(filename)
    assert img.width == 1024
    assert img.height == 1280
    block_width = 1024 // 8
    block_height = 1280 // 10
    result = []
    for x in range(0, 8):
        for y in range(0, 10):
            left = x * block_width
            right = left + block_width
            upper = y * block_height
            lower = upper + block_height
            result.append(img.crop((left, upper, right, lower)))
    return result


def test_poc():
    filename = "ebd13bafced4d0d0385d19b3a86cccfb.jpg"
    assert name_to_seed(filename) == 196071124
    wanted = [
        10, 67, 1, 65, 76, 26, 48, 32, 53, 21, 70, 58, 39, 7, 43, 42, 13, 17, 62, 46, 63, 72, 57, 23, 8, 60, 54, 22, 44,
        49, 11, 38, 37, 50, 14, 79, 9, 0, 45, 29, 71, 25, 31, 12, 66, 77, 51, 28, 68, 74, 15, 33, 3, 5, 75, 20, 56, 2,
        34, 35, 59, 64, 30, 73, 55, 47, 16, 69, 78, 41, 40, 36, 4, 18, 52, 27, 19, 61, 6, 24
    ]
    assert wanted == shuffle(name_to_seed(filename))


def build_image(filename: str, cropped: Image, width: int, height: int) -> Image:
    index = 0
    target = Image.new("RGB", (width, height))
    for i in shuffle(name_to_seed(filename)):
        target_x = 128 * (i % 8 if i >= 8 else i)
        target_y = 128 * (i // 8)
        left = 128 * (index % 8 if index >= 8 else index)
        upper = 128 * (index // 8)
        right = left + 128
        lower = upper + 128
        b = cropped.crop((left, upper, right, lower))
        target.paste(b, (target_x, target_y))
        index += 1
    return target


if __name__ == '__main__':
    test_poc()
    print("Test pass")
    # file = "ebd13bafced4d0d0385d19b3a86cccfb.jpg"
    # file = "91a94cf7e51953e8637313254a1e236d.jpg"
    # target = build_image(file, Image.open(file), 907, 1280)
    # target.show()
