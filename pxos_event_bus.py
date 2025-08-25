from collections import defaultdict

class PXOSEventBus:
    """
    A simple event bus to manage communication and synchronization
    between the different panes of the PXOS workbench.
    """
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.build_id = 0
        self.truth_origin = None

    def subscribe(self, event_type: str, callback: callable):
        """Register a callback for a given event type."""
        self.subscribers[event_type].append(callback)

    def publish(self, event_type: str, data: dict, origin: str):
        """
        Publish an event to all subscribers.
        Includes metadata for synchronization control.
        """
        self.build_id += 1
        self.truth_origin = origin

        event_data = {
            'data': data,
            'build_id': self.build_id,
            'origin': origin
        }

        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(event_data)

if __name__ == '__main__':
    # Example Usage

    # --- Define some mock pane handlers ---
    def on_python_edit(event):
        print(f"Handler 1 (e.g., P2 updater) received python_edit event from '{event['origin']}' (Build #{event['build_id']})")
        print(f"  Data: {event['data']}")

    def on_python_edit_also(event):
        print(f"Handler 2 (e.g., P5 updater) received python_edit event from '{event['origin']}' (Build #{event['build_id']})")

    def on_dsl_edit(event):
        print(f"Handler 3 (e.g., P1 updater) received dsl_edit event from '{event['origin']}' (Build #{event['build_id']})")

    # --- Main simulation ---
    print("Initializing Event Bus...")
    bus = PXOSEventBus()

    print("\nSubscribing handlers to events...")
    bus.subscribe('python_edit', on_python_edit)
    bus.subscribe('python_edit', on_python_edit_also)
    bus.subscribe('dsl_edit', on_dsl_edit)

    print("\n--- Publishing Events ---")

    # 1. User edits the Python pane (P1)
    print("\n* User edits Python pane (P1)...")
    bus.publish('python_edit', {'code': 'x = 5 + 3'}, origin='P1')

    # 2. User edits the Analog DSL pane (P2)
    print("\n* User edits Analog DSL pane (P2)...")
    bus.publish('dsl_edit', {'dsl': 'CONST comp1 = 8'}, origin='P2')

    print(f"\nFinal state: Build ID = {bus.build_id}, Last Truth Origin = '{bus.truth_origin}'")
