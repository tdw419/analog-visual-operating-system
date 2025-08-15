import pytest
from pxos_py.pxasm_compiler import pxasm_to_pixelbuffer
from pxos_py.vm import PXASMVirtualMachine

def test_pxasm_compiler():
    # This is a placeholder for a real test
    # In a real test, you would compile a PXASM program and verify the output
    code = "HALT"
    buffer = pxasm_to_pixelbuffer(code)
    assert buffer is not None

def test_pxasm_vm():
    # This is a placeholder for a real test
    # In a real test, you would load a program into the VM and verify its execution
    vm = PXASMVirtualMachine(None)
    program = b'\x00' * 32 # Placeholder for a real program
    vm.load_program(program)
    vm.execute()
    assert vm.pc == 1
