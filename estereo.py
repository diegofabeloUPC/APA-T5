"""
APA-T5
"""
import struct

def leer_cabecera(f):
    """Desempaqueta la cabecera de un fichero WAVE PCM de 16/32 bits."""
    cabecera_raw = f.read(44)
    if len(cabecera_raw) < 44:
        raise ValueError("El fichero no tiene una cabecera WAVE válida.")
    
    datos = struct.unpack('<4sI4s4sIHHIIHH4sI', cabecera_raw)
    
    if datos != b'RIFF' or datos[3] != b'WAVE':
        raise ValueError("El fichero no es un formato RIFF/WAVE válido.")
    
    return {
        'ChunkSize': datos[1],
        'NumChannels': datos[4],
        'SampleRate': datos[5],
        'ByteRate': datos[6],
        'BlockAlign': datos[7],
        'BitsPerSample': datos[8],
        'Subchunk2Size': datos[9]
    }

def crear_cabecera(num_channels, sample_rate, bits_per_sample, num_samples):
    """Empaqueta una cabecera WAVE PCM basada en los parámetros de la señal."""
    subchunk2_size = num_samples * num_channels * (bits_per_sample // 8)
    chunk_size = 36 + subchunk2_size
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    
    return struct.pack('<4sI4s4sIHHIIHH4sI', 
        b'RIFF', chunk_size, b'WAVE', b'fmt ', 
        16, 1, num_channels, sample_rate, 
        byte_rate, block_align, bits_per_sample, b'data', subchunk2_size)

def estereo2mono(ficEste, ficMono, canal=2):
    """Convierte un fichero estéreo a mono según el canal indicado."""
    with open(ficEste, 'rb') as f_in, open(ficMono, 'wb') as f_out:
        info = leer_cabecera(f_in)
        if info['NumChannels'] != 2 or info['BitsPerSample'] != 16:
            raise ValueError("Se requiere un fichero WAVE estéreo de 16 bits.")
        
        n_muestras_total = info['Subchunk2Size'] // 2
        muestras = struct.unpack(f'<{n_muestras_total}h', f_in.read())
        
        izq = muestras[0::2]
        der = muestras[1::2]
        
        if canal == 0:   
            resultado = izq
        elif canal == 1: 
            resultado = der
        elif canal == 2: 
            resultado = [(l + r) // 2 for l, r in zip(izq, der)]
        elif canal == 3:
            resultado = [(l - r) // 2 for l, r in zip(izq, der)]
        else:
            raise ValueError("Canal no válido. Use 0, 1, 2 o 3.")
        
        f_out.write(crear_cabecera(1, info['SampleRate'], 16, len(resultado)))
        f_out.write(struct.pack(f'<{len(resultado)}h', *resultado))

def mono2estereo(ficIzq, ficDer, ficEste):
    """Combina dos ficheros mono en uno estéreo."""
    with open(ficIzq, 'rb') as f_izq, open(ficDer, 'rb') as f_der, open(ficEste, 'wb') as f_out:
        info_izq = leer_cabecera(f_izq)
        info_der = leer_cabecera(f_der)
        
        if info_izq['SampleRate'] != info_der['SampleRate']:
            raise ValueError("Los ficheros mono deben tener la misma frecuencia de muestreo.")
        
        m_izq = struct.unpack(f"<{info_izq['Subchunk2Size'] // 2}h", f_izq.read())
        m_der = struct.unpack(f"<{info_der['Subchunk2Size'] // 2}h", f_der.read())
        
        muestras_estereo = [samp for par in zip(m_izq, m_der) for samp in par]
        
        f_out.write(crear_cabecera(2, info_izq['SampleRate'], 16, len(m_izq)))
        f_out.write(struct.pack(f'<{len(muestras_estereo)}h', *muestras_estereo))

def codEstereo(ficEste, ficCod):
    """Codifica señal estéreo de 16 bits en una de 32 bits."""
    with open(ficEste, 'rb') as f_in, open(ficCod, 'wb') as f_out:
        info = leer_cabecera(f_in)
        if info['NumChannels'] != 2 or info['BitsPerSample'] != 16:
            raise ValueError("Se requiere señal estéreo de 16 bits.")
            
        muestras = struct.unpack(f"<{info['Subchunk2Size'] // 2}h", f_in.read())
        izq = muestras[0::2]
        der = muestras[1::2]
        
        s = [(l + r) // 2 for l, r in zip(izq, der)]
        d = [(l - r) // 2 for l, r in zip(izq, der)]
        
        muestras_32 = [(si << 16) | (di & 0xFFFF) for si, di in zip(s, d)]
        
        f_out.write(crear_cabecera(1, info['SampleRate'], 32, len(muestras_32)))
        f_out.write(struct.pack(f'<{len(muestras_32)}i', *muestras_32))

def decEstereo(ficCod, ficEste):
    """Decodifica señal de 32 bits a estéreo de 16 bits."""
    with open(ficCod, 'rb') as f_in, open(ficEste, 'wb') as f_out:
        info = leer_cabecera(f_in)
        if info['BitsPerSample'] != 32:
            raise ValueError("El fichero de entrada debe ser de 32 bits.")
            
        muestras_32 = struct.unpack(f"<{info['Subchunk2Size'] // 4}i", f_in.read())
        
        s = [m >> 16 for m in muestras_32]
        d_raw = [m & 0xFFFF for m in muestras_32]
        d = [struct.unpack('<h', struct.pack('<H', di)) for di in d_raw]
        
        izq = [si + di for si, di in zip(s, d)]
        der = [si - di for si, di in zip(s, d)]
        
        muestras_16 = [samp for par in zip(izq, der) for samp in par]
        
        f_out.write(crear_cabecera(2, info['SampleRate'], 16, len(s)))
        f_out.write(struct.pack(f'<{len(muestras_16)}h', *muestras_16))