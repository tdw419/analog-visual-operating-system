# pxos_dsl.py - Simple DSL module for PXOS
from pxos_dsl_parser import T_analog_to_hlir, T_hlir_to_analog

# Re-export the functions for compatibility
__all__ = ['T_analog_to_hlir', 'T_hlir_to_analog']