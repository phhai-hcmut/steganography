import numpy as np
from scipy.io import wavfile


CHIP_RATE = 2000


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
    pn_seq = rng.choice([-1, 1], size=CHIP_RATE)
    return pn_seq


def embed_file(msg, infile, outfile=None):
    """Hide a message in a stereo audio file"""
    sample_rate, data = wavfile.read(infile)
    stego = embed(data.T, msg)
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
    if len(msg) * CHIP_RATE > nsamples:
        raise ValueError("Audio too short to embed the message")

    pn_seq = gen_pn_seq(CHIP_RATE)
    max_volume = np.max(np.abs(cover_signal))
    # str_fact = 0.05
    str_fact = max_volume / 100
    modulated = (np.atleast_2d(M).T @ np.atleast_2d(pn_seq)).ravel() * str_fact
    # Pad modulated signal with 0 so it have the same shape as the cover signal
    modulated = np.concatenate((modulated, np.zeros(nsamples - len(modulated))))
    stego = cover_signal + modulated
    error_msg = "Unsuccessfully embed message to audio. Try increasing strength factor or chip rate."
    try:
        extracted_msg = extract(stego[0])
    except UnicodeDecodeError:
        raise ValueError(error_msg)
    else:
        if extracted_msg != msg[:-1]:
            raise ValueError(error_msg)
        return stego


def extract_file(filename):
    _, data = wavfile.read(filename)
    return extract(data.T[0])


def extract(signal):
    pn_seq = gen_pn_seq(CHIP_RATE)
    nbits = len(signal) // CHIP_RATE
    # Reshape signal for matrix multiplication
    stego = signal[: (CHIP_RATE * nbits)].reshape(nbits, CHIP_RATE)
    Z = (stego @ np.atleast_2d(pn_seq).T).ravel()
    binary_msg = (Z > 0).astype(np.uint8)
    return binary2text(binary_msg)


if __name__ == '__main__':
    embed_audio('audio.wav')
