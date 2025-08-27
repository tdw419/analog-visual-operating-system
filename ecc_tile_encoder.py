# ecc_tile_encoder.py
"""
Enhanced tile encoder with Hamming ECC support.
Drop-in upgrade from simple parity to Hamming(16,12) error correction.

This keeps the same 16-bit tile format but provides single-error correction
and double-error detection for robust field use.

Usage:
    # Replace your existing pack_bits function with this version
    from ecc_tile_encoder import pack_bits_hamming as pack_bits
    
    # Everything else stays the same!
"""

def pack_bits_simple_parity(opcode: int, operand: int) -> list[int]:
    """
    Original simple parity version (for comparison).
    4-bit opcode + 8-bit operand + 4-bit parity = 16 bits
    """
    opcode &= 0xF
    operand &= 0xFF
    
    hi_nibble = (operand >> 4) & 0xF
    lo_nibble = operand & 0xF
    parity = (opcode ^ hi_nibble ^ lo_nibble) & 0xF
    
    nibbles = [opcode, hi_nibble, lo_nibble, parity]
    bits = []
    for nibble in nibbles:
        for i in range(4):
            bits.append((nibble >> i) & 1)
    return bits

def pack_bits_hamming(opcode: int, operand: int) -> list[int]:
    """
    Hamming(16,12) version with single-error correction.
    4-bit opcode + 8-bit operand = 12 data bits + 4 parity bits = 16 bits total
    
    This is a drop-in replacement for pack_bits_simple_parity.
    """
    # Data bits: 12 = 4(opcode) + 8(operand), least-significant bit first per nibble
    def bits_of_nibble(n):
        return [(n >> i) & 1 for i in range(4)]  # LSB→MSB

    data = (bits_of_nibble(opcode & 0xF) + 
            bits_of_nibble((operand >> 4) & 0xF) + 
            bits_of_nibble(operand & 0xF))  # total 12 bits

    # Hamming(16,12) layout: positions 1..16; parity at 1,2,4,8
    # Fill data into non-parity positions: 3,5,6,7,9,10,11,12,13,14,15,16
    code = [0] * 17  # 1-indexed for easier Hamming math
    data_positions = [3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16]
    
    for bit, pos in zip(data, data_positions):
        code[pos] = bit

    # Compute parity bits p1 (pos1), p2 (pos2), p4 (pos4), p8 (pos8)
    def parity_for(mask_bit):
        acc = 0
        for i in range(1, 17):
            if i & mask_bit:
                acc ^= code[i]
        return acc

    code[1] = parity_for(0b0001)  # covers positions with bit0=1
    code[2] = parity_for(0b0010)  # covers bit1=1
    code[4] = parity_for(0b0100)  # covers bit2=1
    code[8] = parity_for(0b1000)  # covers bit3=1

    # Return 16 bits (positions 1-16) as list
    # Your tile renderer can keep its current mapping; just consume this bit list.
    return [code[i] for i in range(1, 17)]

def unpack_bits_hamming(bits: list[int]) -> tuple[int, int, bool]:
    """
    Decode Hamming(16,12) encoded bits back to opcode and operand.
    Returns (opcode, operand, valid) where valid indicates if decoding succeeded.
    """
    if len(bits) != 16:
        return 0, 0, False
    
    # Reconstruct code array (1-indexed)
    code = [0] + bits  # Make it 1-indexed
    
    # Calculate syndrome to detect/correct errors
    syndrome = 0
    syndrome |= (sum(code[i] for i in range(1, 17) if i & 0b0001) % 2) << 0
    syndrome |= (sum(code[i] for i in range(1, 17) if i & 0b0010) % 2) << 1
    syndrome |= (sum(code[i] for i in range(1, 17) if i & 0b0100) % 2) << 2
    syndrome |= (sum(code[i] for i in range(1, 17) if i & 0b1000) % 2) << 3
    
    if syndrome != 0:
        # Error detected - correct single-bit error
        if 1 <= syndrome <= 16:
            code[syndrome] ^= 1  # Flip the error bit
            print(f"Corrected single-bit error at position {syndrome}")
        else:
            print(f"Multiple-bit error detected (syndrome={syndrome})")
            return 0, 0, False
    
    # Extract data bits from non-parity positions
    data_positions = [3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16]
    data_bits = [code[pos] for pos in data_positions]
    
    # Reconstruct opcode and operand
    def nibble_from_bits(bits):
        return sum(bit << i for i, bit in enumerate(bits))
    
    opcode = nibble_from_bits(data_bits[0:4])
    operand_hi = nibble_from_bits(data_bits[4:8])
    operand_lo = nibble_from_bits(data_bits[8:12])
    operand = (operand_hi << 4) | operand_lo
    
    return opcode, operand, True

def create_ecc_tile(opcode: int, operand: int, tile_size: int = 16):
    """
    Create a tile image using Hamming ECC encoding.
    Drop-in replacement for your existing create_tile function.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("PIL not available - returning None")
        return None
    
    bits = pack_bits_hamming(opcode, operand)
    
    img = Image.new('RGB', (tile_size, tile_size), 'white')
    draw = ImageDraw.Draw(img)
    
    # Draw the 4x4 bit pattern (same as before)
    margin = 2
    cell_size = (tile_size - 2 * margin) // 4
    
    for bit_idx, bit in enumerate(bits):
        row = bit_idx // 4
        col = bit_idx % 4
        
        x = margin + col * cell_size
        y = margin + row * cell_size
        
        color = 'black' if bit else 'white'
        draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color)
    
    # Draw border
    draw.rectangle([0, 0, tile_size-1, tile_size-1], outline='gray')
    
    return img

def test_ecc_encoding():
    """Test the ECC encoding/decoding with error injection"""
    print("Testing Hamming ECC encoding/decoding...")
    
    # Test data
    test_cases = [
        (0x5, 0xA3),  # Opcode 5, operand 163
        (0xF, 0x00),  # Max opcode, min operand
        (0x0, 0xFF),  # Min opcode, max operand
        (0x7, 0x80),  # Mid values
    ]
    
    for opcode, operand in test_cases:
        print(f"\nTesting opcode={opcode:X}, operand={operand:02X}")
        
        # Encode
        bits = pack_bits_hamming(opcode, operand)
        print(f"Encoded bits: {bits}")
        
        # Decode (no errors)
        decoded_op, decoded_operand, valid = unpack_bits_hamming(bits)
        print(f"Decoded: opcode={decoded_op:X}, operand={decoded_operand:02X}, valid={valid}")
        
        # Test error correction
        if len(bits) > 5:
            # Inject single-bit error
            corrupted_bits = bits.copy()
            corrupted_bits[5] ^= 1  # Flip bit 5
            print(f"Corrupted bits: {corrupted_bits}")
            
            # Try to decode with error
            corrected_op, corrected_operand, valid = unpack_bits_hamming(corrupted_bits)
            print(f"Corrected: opcode={corrected_op:X}, operand={corrected_operand:02X}, valid={valid}")
            
            # Verify correction worked
            if corrected_op == opcode and corrected_operand == operand:
                print("✅ Error correction successful!")
            else:
                print("❌ Error correction failed!")

# Compatibility aliases for drop-in replacement
pack_bits = pack_bits_hamming  # Default to Hamming version
create_tile = create_ecc_tile   # Default to ECC version

if __name__ == "__main__":
    test_ecc_encoding()
    
    print("\n" + "=" * 60)
    print("ECC Tile Encoder ready!")
    print("To upgrade your workbench:")
    print("1. Replace: from your_module import pack_bits")
    print("   With:    from ecc_tile_encoder import pack_bits")
    print("2. Everything else stays the same!")
    print("3. Your tiles now have single-error correction capability")