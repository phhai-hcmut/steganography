import argparse

import numpy as np
from scipy.io import wavfile

SPREADING_FACTOR = 6
STR_FACTOR_WEIGHT = 500
ERROR_FAIL_DECODE_MSG = "Unsuccessfully embed message to audio. Try increasing strength factor or spreading factor."
ERROR_TOO_SHORT = "Audio too short to embed the message, try lowering spreading factor!"


def text2binary(text):
    """Convert text to bit array"""
    text_bytes = text.encode()
    return np.unpackbits(np.frombuffer(text_bytes, dtype=np.uint8))


def binary2text(bit_array):
    """Conert bit array to text"""
    a = np.packbits(bit_array)
    # null-terminated string
    string_end = list(a).index(0)
    return bytes(a[:string_end]).decode()


def gen_pn_seq():
    rng = np.random.default_rng(seed)
    pn_seq = rng.choice([-1, 1], size=SPREADING_FACTOR)
    return pn_seq


def embed_file(msg, infile, outfile=None):
    """Hide a message in a stereo audio file"""
    sample_rate, data = wavfile.read(infile)
    stego = embed(data.T, msg)
    stego = stego.astype(np.float32)
    if outfile is not None:
        wavfile.write(outfile, sample_rate, stego.T)
    else:
        return stego[0]


def embed(cover_signal, msg):
    # Terminate the message string with null
    msg += '\0'
    # Encode message to binary format and change 0 bit to -1
    M = text2binary(msg).astype(np.int8) * 2 - 1
    nsamples = cover_signal.shape[-1]
    if len(M) * SPREADING_FACTOR > nsamples:
        raise ValueError(ERROR_TOO_SHORT)

    pn_seq = gen_pn_seq()

    # streng factor must be proportional to message's amplitude (or frequency idk)
    max_volume = np.max(np.abs(cover_signal))
    str_fact = max_volume / STR_FACTOR_WEIGHT
    if isinstance(cover_signal, np.integer):
        # Round strength factor if input signal is in integer format
        str_fact = round(str_fact)

    modulated = (np.atleast_2d(M).T @ np.atleast_2d(pn_seq)).ravel() * str_fact
    # Pad modulated signal with 0 so it have the same shape as the cover signal
    modulated = np.concatenate((modulated, np.zeros(nsamples - len(modulated))))
    stego = cover_signal + modulated
    try:
        extracted_msg = extract(stego)
    except UnicodeDecodeError:
        print('UNICODE PROBLEM!')
        raise ValueError(ERROR_FAIL_DECODE_MSG)
    else:
        if extracted_msg != msg[:-1]:
            print('Extracted Message: ', extracted_msg)
            raise ValueError(ERROR_FAIL_DECODE_MSG)
        return stego


def extract_file(filename):
    _, data = wavfile.read(filename)
    return extract(data.T)


def extract(signal):
    pn_seq = gen_pn_seq()
    nbits = len(signal) // SPREADING_FACTOR
    # Reshape signal for matrix multiplication
    stego = signal[: (SPREADING_FACTOR * nbits)].reshape(nbits, SPREADING_FACTOR)
    Z = (stego @ np.atleast_2d(pn_seq).T).ravel()
    binary_msg = (Z > 0).astype(np.uint8)
    return binary2text(binary_msg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--decrypt', '-d', action='store_true')
    parser.add_argument('in_file')
    parser.add_argument('out_file', nargs='?')
    parser.add_argument('message', nargs='?')
    parser.add_argument('--seed', nargs='?', type=int, default=0)
    args = parser.parse_args()

    seed = args.seed
    if args.decrypt:
        print(extract_file(args.in_file))
    else:
        embed_file(args.message, args.in_file, args.out_file)
