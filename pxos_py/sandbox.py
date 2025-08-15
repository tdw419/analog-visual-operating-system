class ExecutionSandbox:
    def __init__(self, pixelos):
        self.px = pixelos
        self.env = {
            'px': self.px,
            'print': self.safe_print,
            'range': range,
            'len': len,
            '__builtins__': self.get_safe_builtins()
        }

    def get_safe_builtins(self):
        safe = {}
        for name in ['int', 'float', 'str', 'list', 'dict']:
            safe[name] = __builtins__[name]
        return safe

    def safe_print(self, *args):
        msg = " ".join(str(arg) for arg in args)
        self.px.log(msg)

    def execute(self, code, lang):
        try:
            if lang == "pixelpy":
                exec(code, self.env)
            elif lang == "pxasm":
                self.run_pxasm(code)
            return True, "Execution completed"
        except Exception as e:
            return False, str(e)

    def run_pxasm(self, code):
        from pxos_py.vm import PXASMVirtualMachine
        vm = PXASMVirtualMachine(self.px)
        vm.load_program(code)
        vm.execute()
