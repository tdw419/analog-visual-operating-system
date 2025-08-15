from pxos_py.px_bitpack_v1 import encode_to_png

with open("examples/bouncy_bar.py", "rb") as f:
    src_bytes = f.read()

encode_to_png(src_bytes, lang_id="pixelpy", out_path="bouncy_bar.png")
