"""
FEC (前向纠错) 工具模块
基于 GF(256) 有限域上的 Reed-Solomon 编码
用于在二维码传输中恢复丢失的帧
"""

import functools

# GF(256) 不可约多项式: x^8 + x^4 + x^3 + x^2 + 1
GF_POLY = 0x11D
GF_SIZE = 256


def _build_gf_tables():
    """构建 GF(256) 指数表和对数表"""
    exp_table = [0] * (GF_SIZE * 2)
    log_table = [0] * GF_SIZE

    value = 1
    for index in range(GF_SIZE - 1):
        exp_table[index] = value
        log_table[value] = index
        value <<= 1
        if value & GF_SIZE:
            value ^= GF_POLY

    for index in range(GF_SIZE - 1, GF_SIZE * 2):
        exp_table[index] = exp_table[index - (GF_SIZE - 1)]

    return exp_table, log_table


GF_EXP, GF_LOG = _build_gf_tables()


def gf_add(a, b):
    return a ^ b


def gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return GF_EXP[GF_LOG[a] + GF_LOG[b]]


def gf_inv(value):
    if value == 0:
        raise ZeroDivisionError("Cannot invert zero in GF(256)")
    return GF_EXP[255 - GF_LOG[value]]


def gf_pow(value, power):
    if power == 0:
        return 1
    if value == 0:
        return 0
    return GF_EXP[(GF_LOG[value] * power) % 255]


def _mat_mul(left, right):
    """GF(256) 上的矩阵乘法"""
    rows = len(left)
    cols = len(right[0])
    inner = len(right)
    result = [[0] * cols for _ in range(rows)]

    for row in range(rows):
        for col in range(cols):
            value = 0
            for idx in range(inner):
                value ^= gf_mul(left[row][idx], right[idx][col])
            result[row][col] = value

    return result


def _mat_identity(size):
    return [[1 if row == col else 0 for col in range(size)] for row in range(size)]


def _mat_invert(matrix):
    """GF(256) 上的矩阵求逆（高斯消元法）"""
    size = len(matrix)
    augmented = [row[:] + identity_row[:] for row, identity_row in zip(matrix, _mat_identity(size))]

    for col in range(size):
        pivot_row = None
        for row in range(col, size):
            if augmented[row][col] != 0:
                pivot_row = row
                break

        if pivot_row is None:
            raise ValueError("Matrix is singular in GF(256)")

        if pivot_row != col:
            augmented[col], augmented[pivot_row] = augmented[pivot_row], augmented[col]

        pivot_inv = gf_inv(augmented[col][col])
        for idx in range(col, size * 2):
            augmented[col][idx] = gf_mul(augmented[col][idx], pivot_inv)

        for row in range(size):
            if row == col or augmented[row][col] == 0:
                continue
            factor = augmented[row][col]
            for idx in range(col, size * 2):
                augmented[row][idx] ^= gf_mul(factor, augmented[col][idx])

    return [row[size:] for row in augmented]


@functools.lru_cache(maxsize=64)
def build_generator_matrix(data_shards, parity_shards):
    """构建 FEC 生成矩阵（Vandermonde 矩阵变体）"""
    if data_shards <= 0:
        raise ValueError("data_shards must be positive")
    if parity_shards < 0:
        raise ValueError("parity_shards cannot be negative")

    total_shards = data_shards + parity_shards
    vandermonde = []

    for row in range(total_shards):
        base = row + 1
        vandermonde.append([gf_pow(base, col) for col in range(data_shards)])

    top_inverse = _mat_invert(vandermonde[:data_shards])
    return _mat_mul(vandermonde, top_inverse)


def encode_parity_shards(data_shard_bytes, parity_shards):
    """
    对一组等长的数据分片生成冗余分片
    
    参数:
        data_shard_bytes: list[bytes] - 数据分片列表，每片长度相同
        parity_shards: int - 要生成的冗余分片数
    
    返回:
        list[bytes] - 冗余分片列表
    """
    if not data_shard_bytes:
        raise ValueError("No data shards to encode")
    if parity_shards <= 0:
        return []

    data_shards = len(data_shard_bytes)
    shard_size = len(data_shard_bytes[0])
    if any(len(shard) != shard_size for shard in data_shard_bytes):
        raise ValueError("All data shards must have the same size")

    generator = build_generator_matrix(data_shards, parity_shards)
    parity_rows = generator[data_shards:]
    parity_outputs = [bytearray(shard_size) for _ in range(parity_shards)]

    for parity_idx, coefficients in enumerate(parity_rows):
        output = parity_outputs[parity_idx]
        for data_idx, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            shard = data_shard_bytes[data_idx]
            for byte_idx in range(shard_size):
                output[byte_idx] ^= gf_mul(coefficient, shard[byte_idx])

    return [bytes(shard) for shard in parity_outputs]


def recover_data_shards(received_shards, data_shards, parity_shards, shard_size):
    """
    从任意足够数量的分片（数据+冗余混合）恢复原始数据分片
    
    参数:
        received_shards: dict[int, bytes] - {分片索引: 分片数据}
            索引 0..data_shards-1 为数据分片，data_shards..total-1 为冗余分片
        data_shards: int - 原始数据分片数
        parity_shards: int - 冗余分片数
        shard_size: int - 每个分片的字节长度
    
    返回:
        list[bytes] - 恢复后的 data_shards 个数据分片
    
    异常:
        ValueError - 收到的分片数量不足以恢复
    """
    if len(received_shards) < data_shards:
        raise ValueError(
            f"Not enough shards to recover: got {len(received_shards)}, need {data_shards}"
        )

    generator = build_generator_matrix(data_shards, parity_shards)
    selected_indices = sorted(received_shards.keys())[:data_shards]
    decode_matrix = [generator[index] for index in selected_indices]
    decode_inverse = _mat_invert(decode_matrix)
    selected_shards = [received_shards[index] for index in selected_indices]

    if any(len(shard) != shard_size for shard in selected_shards):
        raise ValueError("Received shard size mismatch")

    recovered = [bytearray(shard_size) for _ in range(data_shards)]
    for out_idx in range(data_shards):
        for in_idx, shard in enumerate(selected_shards):
            coefficient = decode_inverse[out_idx][in_idx]
            if coefficient == 0:
                continue
            for byte_idx in range(shard_size):
                recovered[out_idx][byte_idx] ^= gf_mul(coefficient, shard[byte_idx])

    return [bytes(shard) for shard in recovered]
