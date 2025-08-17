"""
PXOS Shell: Interactive command interface
"""
import threading
import time
from ..ai_bridge import AIBridge

class ShellProcess:
    """Interactive shell for PXOS"""

    def __init__(self, dispatcher, pixel_buffer, chat_tile):
        self.dispatcher = dispatcher
        self.pixel_buffer = pixel_buffer
        self.chat_tile = chat_tile
        self.ai_bridge = AIBridge(backend="mock")
        self.running = True

    def run(self):
        """Run the main shell loop"""
        print("\n🔥 PXOS Shell - Type 'help' for commands")

        # Start input thread
        input_thread = threading.Thread(target=self._input_loop)
        input_thread.daemon = True
        input_thread.start()

        # Main render loop
        while self.running:
            self.chat_tile.render()
            time.sleep(0.016)  # ~60 FPS

    def _input_loop(self):
        """Handle user input"""
        while self.running:
            try:
                cmd = input("\npxos> ").strip()
                if not cmd:
                    continue

                if cmd == "exit":
                    self.running = False
                    break
                elif cmd == "help":
                    self._show_help()
                elif cmd.startswith("llm "):
                    self._handle_llm(cmd[4:])
                elif cmd.startswith("plan "):
                    self._handle_plan(cmd[5:])
                elif cmd == "clear":
                    self.pixel_buffer.clear()
                else:
                    # Pass other commands to chat tile
                    self.chat_tile.handle_input(cmd)

            except EOFError:
                self.running = False
                break
            except KeyboardInterrupt:
                print("\n⚠️  Use 'exit' to quit")

    def _show_help(self):
        """Show help information"""
        print("""
🔥 PXOS Shell Commands:
  help              - Show this help
  exit              - Exit PXOS
  clear             - Clear screen
  llm <prompt>      - Send prompt to LLM
  plan <goal>       - Generate and execute plan
  Any other text will be handled by the Chat Tile.
        """)

    def _handle_llm(self, prompt):
        """Handle LLM prompt"""
        print(f"🤖 LLM Processing: {prompt}")
        response = self.dispatcher.handle("llm", {"text": prompt})
        print(f"📝 LLM Response: {response}")

    def _handle_plan(self, goal):
        """Handle AI plan generation and execution"""
        print(f"🎯 Planning: {goal}")

        # Generate plan
        plan = self.ai_bridge.generate_plan(goal, {
            "screen": {"w": self.pixel_buffer.width, "h": self.pixel_buffer.height}
        })

        print(f"📋 Generated Plan: {plan}")

        # Execute plan
        result = self.dispatcher.handle("plan", {"plan": plan})
        print(f"✅ Plan Result: {result}")
