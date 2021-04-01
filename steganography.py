import numpy as np
from scipy.io import wavfile


CHIP_RATE = 6
STR_FACTOR_WEIGHT = 500
ERROR_FAIL_DECODE_MSG = "Unsuccessfully embed message to audio. Try increasing strength factor or chip rate."
ERROR_TOO_SHORT = "Audio too short to embed the message, try lowering chip rate!"

def text2binary(text):
    """Convert text to bit array"""
    text_bytes = text.encode()
    return np.unpackbits(np.frombuffer(text_bytes, dtype=np.uint8))


def binary2text(bit_array):
    """Conert bit array to text"""
    a = np.packbits(bit_array)
    # null-terminated string
    string_end = list(a).index(0)
    print(a[:string_end])
    return bytes(a[:string_end]).decode()


def gen_pn_seq(CHIP_RATE):
    seed = 0
    rng = np.random.default_rng(seed)
    pn_seq = rng.choice([-1, 1], size=CHIP_RATE) #NOTE: this PN is len cr
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
    if len(M) * CHIP_RATE > nsamples:
        raise ValueError(ERROR_TOO_SHORT)

    pn_seq = gen_pn_seq(CHIP_RATE)

    #streng factor must be proportional to message's amplitude (or frequency idk)
    max_volume = np.max(np.abs(cover_signal))
    str_fact = max_volume / STR_FACTOR_WEIGHT

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
    pn_seq = gen_pn_seq(CHIP_RATE)
    nbits = len(signal) // CHIP_RATE
    # Reshape signal for matrix multiplication
    stego = signal[: (CHIP_RATE * nbits)].reshape(nbits, CHIP_RATE)
    Z = (stego @ np.atleast_2d(pn_seq).T).ravel()
    binary_msg = (Z > 0).astype(np.uint8)
    return binary2text(binary_msg)


if __name__ == '__main__':
    embed_file("TRANHOANGLONGPHAMHOANGHAIVOQUANGTU", 'preamble.wav','stergo.wav')
    print(extract_file('stergo.wav'))
