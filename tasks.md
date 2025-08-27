- task_id: 1
  title: "Implement visual boot sequence"
  description: "Automate experiments for booting the simulator from an image. This involves loading a PNG, extracting state, and initializing the simulator."
  type: "feature"
  priority: 1
  files_to_edit:
    - "screen_native_sim.py"
    - "program_host.py"
  status: "todo"

- task_id: 2
  title: "Fix off-by-one error in pixel buffer"
  description: "There is a reported off-by-one error in the pixel buffer rendering that causes a single-pixel artifact at the edge of the screen."
  type: "bug"
  priority: 1
  files_to_edit:
    - "screen_native_sim.py"
  status: "todo"

- task_id: 3
  title: "Add support for circular connections"
  description: "Allow connections between regions to be marked as 'cyclic' to create feedback loops in the audio graph."
  type: "feature"
  priority: 2
  files_to_edit:
    - "program_host.py"
  status: "todo"
