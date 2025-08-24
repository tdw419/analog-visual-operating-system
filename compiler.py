import csv

def compile_calculator_to_ais(source_code):
    ais_instructions = []
    frame = 0

    for line in source_code.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        parts = line.split(' ', 1)
        command = parts[0].upper()
        args_str = parts[1] if len(parts) > 1 else ''
        args = [arg.strip() for arg in args_str.split(',')]

        if command == 'SET':
            var_name, value = args
            if value.isalpha():
                ais_instructions.append([frame, 'LOAD_V', value])
                frame += 1
            else:
                ais_instructions.append([frame, 'LOAD_C', value])
                frame += 1
            ais_instructions.append([frame, 'STORE', var_name])
            frame += 1
        elif command in ['ADD', 'SUB', 'MUL', 'DIV']:
            var_name, value = args
            ais_instructions.append([frame, 'LOAD_V', var_name])
            frame += 1
            if value.isalpha():
                ais_instructions.append([frame, 'LOAD_V', value])
                frame += 1
            else:
                ais_instructions.append([frame, 'LOAD_C', value])
                frame += 1
            ais_instructions.append([frame, command, ''])
            frame += 1
            ais_instructions.append([frame, 'STORE', var_name])
            frame += 1
        elif command == 'PRINT':
            var_name = args[0]
            ais_instructions.append([frame, 'LOAD_V', var_name])
            frame += 1
            ais_instructions.append([frame, 'PRINT', ''])
            frame += 1

    return ais_instructions

def main():
    import sys
    if len(sys.argv) != 3:
        print("Usage: python compiler.py <input_file> <output_csv>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_csv = sys.argv[2]

    with open(input_file, 'r') as f:
        source_code = f.read()

    ais_instructions = compile_calculator_to_ais(source_code)

    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['frame', 'op', 'arg1'])
        writer.writerows(ais_instructions)

    print(f"Compiled {input_file} to {output_csv}")

if __name__ == '__main__':
    main()
