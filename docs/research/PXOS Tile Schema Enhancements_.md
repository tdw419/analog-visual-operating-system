

# **A Technical Report on the Implementation of the PXOS 6-Pane Workbench Phase II**

## **1\. Executive Summary: Architectural Vision for PXOS Workbench Phase II**

This report presents a comprehensive architectural plan for the next phase of the PXOS 6-Pane Workbench, focusing on the critical components of visual tile rendering, live data replay, and seamless hardware integration. The proposed design is built on the principle of decoupling software layers to achieve a system that is not only functional but also highly maintainable, scalable, and testable. The architecture is centered around a robust Hardware Abstraction Layer (HAL) that separates the core application logic from low-level device communication. This is complemented by an Event-Driven Architecture (EDA) that utilizes a single, authoritative source of truth for real-time data synchronization across the entire user interface.

The core technology stack relies on standard, well-supported Python libraries. The foundation for hardware communication is pySerial and its asynchronous counterpart, pyserial-asyncio.1 For data integrity, the

struct module is used for binary data encoding, augmented with a custom implementation of Hamming code for error correction.3 The visual front-end combines

Pillow for generating static tile elements with a chosen visualization library for dynamic plots. A detailed analysis recommends fastplotlib for high-performance, real-time data streams due to its GPU-accelerated rendering, while Matplotlib.FuncAnimation is a suitable alternative for less demanding plotting tasks.5 The entire system is orchestrated using the

asyncio framework, a single-threaded approach that is ideal for handling concurrent I/O-bound operations without the overhead and complexity of multithreading.7

The strategic adoption of this architecture is anticipated to deliver significant benefits. The decoupled nature of the HAL, facilitated by the Bridge design pattern, allows for extensive off-target unit testing, which dramatically improves development speed and code reliability.9 The event-driven, single-source-of-truth model ensures a fluid and responsive user experience by separating data acquisition from UI rendering. Furthermore, a rigorous quality assurance plan, including automated visual regression testing with

Pillow and PixelMatch, will guarantee the aesthetic and functional consistency of the user interface across all releases.11 This architectural vision provides a solid foundation for the PXOS Workbench to meet current demands and easily adapt to future hardware and software developments.

## **2\. Foundational Architecture: The Hardware Abstraction Layer (HAL) as a Bridge**

The design of the PXOS Workbench Phase II begins with a foundational architectural decision: the implementation of a robust Hardware Abstraction Layer (HAL). This layer is crucial for isolating the application logic from the underlying hardware, which is a key principle for building modular, maintainable, and extensible systems.13 A well-structured HAL allows the software to interact with diverse hardware components through a uniform interface, regardless of the low-level communication specifics. This approach is instrumental in promoting platform independence and facilitating seamless updates or replacements of hardware without impacting the higher-level application code.14

### **2.1. Decoupling Abstraction and Implementation with the Bridge Pattern**

The core design of the HAL for the PXOS Workbench will be based on the Bridge design pattern. This structural pattern is specifically engineered to decouple an abstraction from its implementation, enabling both to evolve independently.15 In this context, the "Abstraction" is the high-level, human-readable command interface that the application uses, while the "Implementation" comprises the hardware-specific protocols and communication routines.

The PXOS\_API will serve as the primary abstraction. It will define a set of high-level commands, such as set\_voltage(channel, value) or read\_all\_sensors(), which represent the desired actions without detailing how those actions are carried out.9 The

Hardware\_Interface\_Base will be an abstract base class that defines the common methods required for any hardware interaction, such as send\_command(data) and read\_response(). Concrete implementations, such as Serial\_Hardware\_Interface and Mock\_Hardware\_Interface, will inherit from this base class, each providing its own specific logic for the underlying communication channel.15 For instance,

Serial\_Hardware\_Interface would contain the actual pySerial code to send and receive bytes, while Mock\_Hardware\_Interface would contain logic to return canned responses or simulate delays, all without touching physical hardware.

A significant advantage of this architecture is the ability to develop and test the entire application independently of the physical hardware. A developer can write and verify all of the PXOS\_API's logic using the Mock\_Hardware\_Interface, simulating a perfect hardware environment or intentionally creating error conditions for testing. This separation means that hardware and software development can proceed in parallel, dramatically accelerating the project timeline and allowing for more comprehensive testing of corner cases that are difficult or impossible to reproduce with physical devices.10 This approach ensures that the core logic of the application is sound and stable before the final hardware integration phase, ultimately reducing the risk of project delays and critical bugs.

### **2.2. Robust Hardware Communication Protocol**

Building a robust communication stack is paramount for reliable hardware integration. The design must address the fundamental challenges of serial communication, including physical connection issues, data encoding, and error handling.

The foundation of the communication layer will be the pySerial library. This widely-used Python module provides a consistent, cross-platform interface for accessing serial ports on systems running Windows, macOS, and Linux.1 The library's

serial.Serial class offers a rich set of parameters for configuring the communication link, including the port name, baud rate, number of data bits (bytesize), parity checks, and stop bits.2 A standard configuration, such as 9600 baud and 8N1 (8 data bits, no parity, 1 stop bit), will be adopted to ensure broad compatibility.18

A critical component of this protocol is the handshake procedure. When a serial connection is established, especially with microcontrollers like Arduino, it's common to receive garbled or nonsensical data as the device reboots or synchronizes.19 To address this, a structured handshake protocol will be implemented. The recommended process involves: 1\) closing and reopening the serial port to clear buffers; 2\) pausing for a brief period to allow the device to settle; 3\) sending a predefined handshake character or byte (e.g.,

b'H'); and 4\) waiting for a specific acknowledgment from the device.19 This procedure ensures that data transmission only begins after a stable, synchronized connection has been verified.

For efficient data exchange, all high-level data types (e.g., integers, floats) from the Python application must be converted into a compact binary format. The struct module is the ideal tool for this task, as it provides functions to pack Python values into a byte string according to a specified format string.4 The format string precisely defines the data types and byte order (endianness), preventing ambiguity across different architectures. For instance, the format string

'\>Ih' would pack an unsigned integer (I) and a signed short integer (h) into a big-endian byte sequence, ensuring a consistent data representation for the hardware.21

To further enhance data reliability, the communication layer will incorporate error-correcting codes. Hamming code, a set of error-correction codes, is a simple and effective technique for detecting and correcting single-bit errors that may occur during transmission over a noisy channel.3 The implementation of this algorithm, based on bitwise XOR operations, will calculate redundant parity bits and insert them into the data block at positions corresponding to powers of two.23 This process adds a layer of data integrity, allowing the receiving end to identify and fix single-bit errors. The process of converting high-level commands into a low-level, error-corrected binary stream is a complex but essential part of the data pipeline, ensuring the final output is robust and reliable.

## **3\. The Control and Data Plane: An Asynchronous Event-Driven Pipeline**

A high-performance workbench requires a responsive user interface that remains fluid even when communicating with slow I/O devices. The traditional approach of blocking the main thread while waiting for a response would lead to a frozen UI, a significant usability flaw. This section outlines an architectural model that resolves this challenge by separating data flow from UI rendering.

### **3.1. Event-Driven Architecture and the Single Source of Truth (SSOT)**

The proposed solution for the PXOS Workbench is an Event-Driven Architecture (EDA) where the various components of the system communicate through events rather than direct, blocking function calls. In this model, the hardware communication layer, operating in the background, emits an event (e.g., DATA\_RECEIVED) whenever new data arrives from the hardware.24 The UI panes, interested in this data, simply listen for these events and update their display accordingly. This model ensures that the slowest part of the system—the I/O—does not impede the fastest part—the user interface.

Central to this architecture is the concept of a Single Source of Truth (SSOT).25 The SSOT is a single, authoritative data structure in memory that holds the current state of all relevant hardware and processing results. In the PXOS context, this would be a Python dictionary or a custom object containing the latest sensor readings, output values, and system status. All application components, including the six UI panes, access this single data source for their information. When the background I/O task receives new data, it updates the SSOT, which then triggers a UI refresh.

This architectural pattern offers a fundamental advantage over traditional synchronous designs, especially when considering live data visualization. Traditional libraries like Matplotlib, when used for real-time plotting with FuncAnimation, rely on an animate function that frequently clears and redraws the entire plot.26 This approach is resource-intensive and can lead to a choppy user experience, as the UI is busy with computationally expensive rendering tasks. By implementing an EDA with an SSOT, the entire system becomes more efficient. The background process performs the slow work of data acquisition and updating the central state. The UI components, decoupled from this process, simply read from the updated state and render the changes, avoiding the overhead of recomputing data or clearing the entire display. This creates a performant and responsive user experience, even with high-frequency data streams.

### **3.2. Concurrency with Python's asyncio Library**

To enable this non-blocking, event-driven architecture, Python's asyncio library is the ideal choice. asyncio is a single-threaded framework for asynchronous I/O operations that uses cooperative multitasking.7 It allows a program to run multiple tasks seemingly "at the same time" without the complexities and potential race conditions associated with traditional multithreading.28 This is particularly well-suited for I/O-bound tasks where the program spends a significant amount of time waiting for external resources, such as a serial port.

The integration with pySerial is handled by the pyserial-asyncio library, which provides an asynchronous wrapper for the standard pySerial functions.29 This library offers high-level

asyncio.StreamReader and StreamWriter objects, allowing developers to use Python's modern async and await keywords to perform serial reads and writes in a non-blocking manner.30 For example, instead of a blocking

ser.read\_until(), a developer can simply await reader.read\_until(), allowing the asyncio event loop to switch to other tasks (like updating the UI) while the serial port is waiting for new data. This architecture ensures the main application loop remains free to process UI events, preventing the workbench from freezing and guaranteeing a smooth, responsive user experience.

## **4\. Visual Representation: Rendering Tiles and Live Plots**

The user experience of the PXOS Workbench hinges on its visual representation. The ability to render both static, informative tiles and dynamic, real-time data plots with high fidelity is a core requirement. This section details the technical approach for implementing these visual elements.

### **4.1. Visual Tile Rendering with Pillow and Tkinter**

For the static, pre-defined elements of the workbench's interface, such as informational tiles or grid lines, the Pillow library is the chosen tool. As an actively maintained fork of the Python Imaging Library (PIL), Pillow provides robust capabilities for image processing and the programmatic creation of graphics.32 The

ImageDraw module within Pillow offers a simple yet powerful 2D drawing interface.

To create the visual tiles, the process involves first creating an Image object with a specific mode and size, such as 'RGB' mode for a color image.33 A

Draw object is then instantiated for this image, providing the necessary drawing context. Using methods of the Draw object, developers can render various geometric shapes and text. For instance, the draw.rectangle() method is used to draw a rectangle by specifying the coordinates of its bounding box ((x0, y0, x1, y1)) and the fill and outline colors, which can be defined using RGB tuples.34 This approach allows for the dynamic generation of UI elements, a flexible alternative to hard-coded graphical assets.

These Pillow images are then integrated into the graphical user interface using Tkinter, Python's standard GUI library. The bridge between the Pillow Image object and a Tkinter widget is the ImageTk.PhotoImage class. This class converts a Pillow image into a format that Tkinter can display within widgets like a Label or a Canvas. A critical implementation detail is the necessity of maintaining a reference to the ImageTk.PhotoImage object. If the object is a local variable and goes out of scope, Python's garbage collection will reclaim the memory, and the image will disappear from the UI. This is prevented by storing a reference to the image on the widget itself, ensuring it persists for the lifetime of the application.

### **4.2. Live Replay and High-Performance Visualization**

For the dynamic elements of the workbench, such as live plots of sensor data, the choice of visualization library is critical for performance.

**Comparative Analysis of Visualization Libraries**

| Feature | Matplotlib (FuncAnimation) | fastplotlib |
| :---- | :---- | :---- |
| **Primary Use Case** | General-purpose plotting, static and animated figures. | High-performance, interactive scientific visualization. |
| **Core Rendering Engine** | CPU-based rendering with optional optimizations. | GPU-accelerated via pygfx on modern APIs (Vulkan, Metal, DX12). |
| **Real-time Performance** | Can be slow for high-frequency data streams; relies on redrawing artists (blit=True).26 | Designed for rapid, real-time rendering of large datasets with millions of points.5 |
| **Usability for Large Data** | Can struggle with large datasets, leading to performance bottlenecks.5 | API is optimized for interacting with data as simple arrays, making it well-suited for large-scale data exploration.5 |
| **Architecture** | Distinct from fastplotlib's architecture. | Built on an entirely different architecture, optimized for hardware acceleration.35 |

While Matplotlib is a well-known and versatile library with a dedicated animation module, its performance characteristics are inherently limited by its CPU-based rendering model. The FuncAnimation class allows for live plots by repeatedly calling a user-defined function (animate), which updates the plot data.26 The

blit=True parameter significantly improves performance by only redrawing the parts of the figure that have changed, rather than the entire canvas.6 Despite this, continuously clearing and redrawing plots, even with

blit enabled, is a relatively heavy operation that can become a bottleneck when dealing with high data rates.

For the PXOS Workbench, which requires responsive "live replay" functionality, a more performant solution is warranted. The analysis suggests that fastplotlib is a superior choice for these demanding visualization tasks. It is a modern, GPU-accelerated library that leverages new graphics APIs like Vulkan and Metal via the pygfx rendering engine.5 This fundamental architectural difference allows

fastplotlib to render complex visualizations of large datasets (e.g., millions of data points) at high frame rates, which would be challenging or impossible for many other Python libraries.

The implementation for live plots requires transforming incoming data into a format suitable for visualization. Data from the hardware, likely structured as key-value pairs (e.g., {'time': 1, 'value': 2}), must be converted into a list of tuples \[(x, y)\] for plotting. Python offers several efficient and readable methods for this transformation, such as using the dict.items() method in combination with list() or a list comprehension.36

### **4.3. The PXOS High-Level-to-Low-Level Translation Pipeline**

The translation of high-level graphical commands from the user interface into low-level, hardware-specific operations can be modeled as a compiler-like process.38 For instance, a user's action of drawing a virtual rectangle on a pane is a high-level command. This command must be translated into a series of low-level instructions to control the physical hardware.

The first step in this process is to generate an Intermediate Representation (IR) from the high-level commands. This IR serves as a simplified, abstract data structure that is easier to manipulate and optimize than the raw source code. Python's built-in ast module can be used to parse high-level code or commands and represent them as an Abstract Syntax Tree (AST).39 This tree structure captures the syntactic relationships between the components of the command. This AST can then be transformed into a more linear, tuple-based IR, where each tuple represents a single instruction for the hardware.40 This intermediate format is both machine-independent and conducive to further processing and optimization.

Finally, this IR is used to generate the low-level binary code that is sent to the hardware. As discussed in Section 2, the struct module is used to convert the IR's values into a compact byte format. This low-level code generation phase is also where error-correcting parity bits are added, as specified by the Hamming code algorithm, completing the transformation from a high-level user command to a reliable hardware instruction set.

## **5\. Quality Assurance: A Rigorous Testing Strategy**

A robust system demands a comprehensive testing strategy that validates not only the code's functionality but also its reliability and visual consistency. This is especially true for systems that interact with external hardware, which introduces complexities related to determinism and safety. The proposed plan outlines two key testing methodologies to ensure the integrity of the PXOS Workbench: hardware interface mocking and automated visual regression testing.

### **5.1. Hardware Interface Unit Testing with Mocking**

Testing code that communicates with physical hardware is challenging because it relies on an external, unpredictable dependency. The solution is to use mocking to isolate the system's logic from the hardware. The unittest.mock library is a powerful tool for creating substitute objects that simulate the behavior of real objects in a controlled testing environment.43

For the PXOS Workbench, the unittest.mock.patch decorator is the ideal mechanism for replacing the pySerial.Serial class during unit tests. This decorator temporarily replaces the real pySerial class with a mock object for the duration of a test and automatically restores the original class when the test concludes.

The behavior of this mock object can be precisely controlled to simulate a wide range of hardware scenarios. The return\_value attribute can be set to return a specific, predictable value from a mocked method, such as simulating a sensor reading.45 Alternatively, the

side\_effect attribute can be configured with an iterable of return values to simulate a stream of data over multiple calls, or it can be set to an exception to test how the system handles hardware failures.46

A significant architectural advantage of the Bridge pattern is revealed here. By patching the Implementation class (e.g., Serial\_Hardware\_Interface) with a mock, a test can verify that the high-level PXOS\_API correctly constructs and calls methods on its dependency, without ever having to engage with the actual hardware.45 The

assert\_called\_once\_with() method of the mock object allows for a precise assertion that a function was called exactly once with the expected parameters, validating the correctness of the abstraction layer's logic. This approach makes the entire system, from the high-level application down to the hardware interface, fully unit-testable, leading to a much more stable and reliable product.

### **5.2. Automated Visual Regression Testing for UI Consistency**

As a highly visual application, the PXOS Workbench is susceptible to subtle layout shifts or rendering bugs that may not be caught by traditional functional tests. Automated visual regression testing is the best practice to address this concern. This methodology involves comparing a freshly rendered screenshot of the UI against a previously approved "baseline" image.47

The testing process begins with capturing a screenshot of the workbench. This image is then loaded and processed using the Pillow library, and a comparison is performed against the baseline image.48 The

PixelMatch library is particularly well-suited for this task. It performs a fast, pixel-by-pixel comparison of two images and identifies discrepancies, even those caused by anti-aliasing.12

The output of such a test is a "diff image" that visually highlights the areas of change in the UI. For a developer, this provides an immediate, intuitive understanding of any unintended visual regressions, eliminating the need to manually sift through code to find the source of the problem.11 This testing ensures that every code change, whether a minor CSS adjustment or a major feature addition, maintains the visual integrity of the user experience.

## **6\. Conclusion and Future Roadmap**

### **6.1. Project Summary**

This report has presented a detailed architectural plan for the next phase of the PXOS 6-Pane Workbench, founded on the principles of modularity, performance, and testability. The proposed architecture separates the high-level application logic from the low-level hardware interface using a Bridge-pattern-based Hardware Abstraction Layer. This decoupling is a cornerstone of the design, enabling parallel development and deterministic testing.

The system's real-time capabilities are addressed through an asynchronous, event-driven data pipeline powered by Python's asyncio framework and the pyserial-asyncio library. This model ensures a highly responsive UI that remains unhindered by slow I/O operations. Visual rendering is handled by a combination of Pillow for static UI elements and fastplotlib for high-performance, GPU-accelerated data visualization. A comprehensive testing strategy, including mocking the hardware interface and performing visual regression tests, has been outlined to guarantee the system's stability and consistency.

### **6.2. Strategic Future Directions**

The architecture laid out in this report not only fulfills the current requirements but also establishes a robust foundation for future expansion. A logical next step is to explore more advanced Intermediate Representations (IRs) beyond simple tuples. Multi-Level Intermediate Representation (MLIR) is a framework designed to handle code generation for diverse, heterogeneous hardware targets and could be an ideal candidate for future versions of the PXOS Workbench that must interface with increasingly complex devices like FPGAs or custom ASICs.38 This would allow for the development of even more sophisticated, high-level user commands that are compiled into optimized, low-level binary data blocks for a wide range of hardware platforms.

#### **Works cited**

1. pyserial/pyserial: Python serial port access library \- GitHub, accessed August 25, 2025, [https://github.com/pyserial/pyserial](https://github.com/pyserial/pyserial)  
2. pySerial API, accessed August 25, 2025, [https://pyserial.readthedocs.io/en/latest/pyserial\_api.html](https://pyserial.readthedocs.io/en/latest/pyserial_api.html)  
3. Hamming Code implementation in Python \- GeeksforGeeks, accessed August 25, 2025, [https://www.geeksforgeeks.org/python/hamming-code-implementation-in-python/](https://www.geeksforgeeks.org/python/hamming-code-implementation-in-python/)  
4. struct \--- Interpret bytes as packed binary data — Dokumentasi Python 3.7.17, accessed August 25, 2025, [https://docs.python.org/id/3.7/library/struct.html](https://docs.python.org/id/3.7/library/struct.html)  
5. fastplotlib: driving scientific discovery through data visualization | by ..., accessed August 25, 2025, [https://medium.com/@caitlin9165/fastplotlib-driving-scientific-discovery-through-data-visualization-418f8bff094c](https://medium.com/@caitlin9165/fastplotlib-driving-scientific-discovery-through-data-visualization-418f8bff094c)  
6. matplotlib.animation — Matplotlib 3.10.5 documentation, accessed August 25, 2025, [https://matplotlib.org/stable/api/animation\_api.html](https://matplotlib.org/stable/api/animation_api.html)  
7. Python's asyncio: A Hands-On Walkthrough, accessed August 24, 2025, [https://realpython.com/async-io-python/](https://realpython.com/async-io-python/)  
8. Python Tutorial: AsyncIO \- Complete Guide to Asynchronous Programming with Animations, accessed August 24, 2025, [https://www.youtube.com/watch?v=oAkLSJNr5zY](https://www.youtube.com/watch?v=oAkLSJNr5zY)  
9. How to Write Epic Hardware Abstraction Layers (HAL) in C | Beningo Embedded Group, accessed August 25, 2025, [https://www.beningo.com/how-to-write-epic-hardware-abstraction-layers-hal-in-c/](https://www.beningo.com/how-to-write-epic-hardware-abstraction-layers-hal-in-c/)  
10. Unit Testing for functions communicating with Hardware? Best practices? : r/cpp \- Reddit, accessed August 25, 2025, [https://www.reddit.com/r/cpp/comments/47g2gn/unit\_testing\_for\_functions\_communicating\_with/](https://www.reddit.com/r/cpp/comments/47g2gn/unit_testing_for_functions_communicating_with/)  
11. Python Visual Regression Testing: A Complete Tutorial \- LambdaTest, accessed August 25, 2025, [https://www.lambdatest.com/learning-hub/python-visual-regression-testing](https://www.lambdatest.com/learning-hub/python-visual-regression-testing)  
12. Visual Regression Testing with Playwright and Pixelmatch | by Testrig Technologies, accessed August 25, 2025, [https://medium.com/@testrig/visual-regression-testing-with-playwright-and-pixelmatch-002770005019](https://medium.com/@testrig/visual-regression-testing-with-playwright-and-pixelmatch-002770005019)  
13. What Are Abstraction Layers? \- Coursera, accessed August 25, 2025, [https://www.coursera.org/articles/abstraction-layers](https://www.coursera.org/articles/abstraction-layers)  
14. Abstraction layer \- Wikipedia, accessed August 25, 2025, [https://en.wikipedia.org/wiki/Abstraction\_layer](https://en.wikipedia.org/wiki/Abstraction_layer)  
15. Design Patterns in Python: Bridge | Medium, accessed August 25, 2025, [https://medium.com/@amirm.lavasani/design-patterns-in-python-bridge-c34f3fcdd2eb](https://medium.com/@amirm.lavasani/design-patterns-in-python-bridge-c34f3fcdd2eb)  
16. Bridge in Python / Design Patterns \- Refactoring.Guru, accessed August 25, 2025, [https://refactoring.guru/design-patterns/bridge/python/example](https://refactoring.guru/design-patterns/bridge/python/example)  
17. Python, Abstracting a class best practice \- serial port \- Stack Overflow, accessed August 25, 2025, [https://stackoverflow.com/questions/21821026/python-abstracting-a-class-best-practice](https://stackoverflow.com/questions/21821026/python-abstracting-a-class-best-practice)  
18. PySerial RS232 Serial Communication \- AB Electronics UK, accessed August 25, 2025, [https://www.abelectronics.co.uk/kb/article/1112/pyserial-rs232-serial-communication](https://www.abelectronics.co.uk/kb/article/1112/pyserial-rs232-serial-communication)  
19. 10\. Serial communication with Python — BE/EE/MedE 189 a ..., accessed August 25, 2025, [https://be189.github.io/lessons/10/control\_of\_arduino\_with\_python.html](https://be189.github.io/lessons/10/control_of_arduino_with_python.html)  
20. struct module in Python \- GeeksforGeeks, accessed August 25, 2025, [https://www.geeksforgeeks.org/python/struct-module-python/](https://www.geeksforgeeks.org/python/struct-module-python/)  
21. struct.pack() in Python \- GeeksforGeeks, accessed August 25, 2025, [https://www.geeksforgeeks.org/python/struct-pack-in-python/](https://www.geeksforgeeks.org/python/struct-pack-in-python/)  
22. \[IT430\] Class 3: Struct Packing, Type Conversion, accessed August 25, 2025, [https://www.usna.edu/Users/cs/choi/it430/lec/l03/lec.html](https://www.usna.edu/Users/cs/choi/it430/lec/l03/lec.html)  
23. Hamming Code in Python \- Naukri Code 360, accessed August 25, 2025, [https://www.naukri.com/code360/library/hamming-code-in-python](https://www.naukri.com/code360/library/hamming-code-in-python)  
24. What is a Single Source of Truth (SSOT) | MuleSoft, accessed August 24, 2025, [https://www.mulesoft.com/resources/esb/what-is-single-source-of-truth-ssot](https://www.mulesoft.com/resources/esb/what-is-single-source-of-truth-ssot)  
25. Single source of truth \- Wikipedia, accessed August 24, 2025, [https://en.wikipedia.org/wiki/Single\_source\_of\_truth](https://en.wikipedia.org/wiki/Single_source_of_truth)  
26. Graph Sensor Data with Python and Matplotlib \- SparkFun Learn, accessed August 25, 2025, [https://learn.sparkfun.com/tutorials/graph-sensor-data-with-python-and-matplotlib/update-a-graph-in-real-time](https://learn.sparkfun.com/tutorials/graph-sensor-data-with-python-and-matplotlib/update-a-graph-in-real-time)  
27. CustomProcessingUnit: Reverse Engineering and Customization of Intel Microcode \- Michael Schwarz, accessed August 25, 2025, [https://misc0110.net/files/cpu\_woot23.pdf](https://misc0110.net/files/cpu_woot23.pdf)  
28. I am trying to cause race condition for demonstration purposes but fail to fail \- Stack Overflow, accessed August 24, 2025, [https://stackoverflow.com/questions/79382803/i-am-trying-to-cause-race-condition-for-demonstration-purposes-but-fail-to-fail](https://stackoverflow.com/questions/79382803/i-am-trying-to-cause-race-condition-for-demonstration-purposes-but-fail-to-fail)  
29. Overview — pySerial-asyncio 0.6 documentation, accessed August 25, 2025, [https://pyserial-asyncio.readthedocs.io/en/latest/shortintro.html](https://pyserial-asyncio.readthedocs.io/en/latest/shortintro.html)  
30. using serial port in python3 asyncio \- Stack Overflow, accessed August 25, 2025, [https://stackoverflow.com/questions/21666106/using-serial-port-in-python3-asyncio](https://stackoverflow.com/questions/21666106/using-serial-port-in-python3-asyncio)  
31. pyserial-asyncio-fast \- PyPI, accessed August 25, 2025, [https://pypi.org/project/pyserial-asyncio-fast/](https://pypi.org/project/pyserial-asyncio-fast/)  
32. Image Processing With the Python Pillow Library, accessed August 25, 2025, [https://realpython.com/image-processing-with-the-python-pillow-library/](https://realpython.com/image-processing-with-the-python-pillow-library/)  
33. Draw circle, rectangle, line, etc. with Python, Pillow | note.nkmk.me, accessed August 25, 2025, [https://note.nkmk.me/en/python-pillow-imagedraw/](https://note.nkmk.me/en/python-pillow-imagedraw/)  
34. ImageDraw module \- Pillow (PIL Fork) 11.3.0 documentation, accessed August 25, 2025, [https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html)  
35. FAQ — v0.5.0+g124d79e.dirty \- fastplotlib's documentation\!, accessed August 25, 2025, [https://fastplotlib.org/user\_guide/faq.html](https://fastplotlib.org/user_guide/faq.html)  
36. Convert Dictionary to List of Tuples \- Python \- GeeksforGeeks, accessed August 25, 2025, [https://www.geeksforgeeks.org/python/python-convert-dictionary-to-list-of-tuples/](https://www.geeksforgeeks.org/python/python-convert-dictionary-to-list-of-tuples/)  
37. 5\. Data Structures — Python 3.13.7 documentation, accessed August 25, 2025, [https://docs.python.org/3/tutorial/datastructures.html](https://docs.python.org/3/tutorial/datastructures.html)  
38. Intermediate representation \- Wikipedia, accessed August 25, 2025, [https://en.wikipedia.org/wiki/Intermediate\_representation](https://en.wikipedia.org/wiki/Intermediate_representation)  
39. Abstract syntax tree \- Wikipedia, accessed August 25, 2025, [https://en.wikipedia.org/wiki/Abstract\_syntax\_tree](https://en.wikipedia.org/wiki/Abstract_syntax_tree)  
40. ast — Abstract Syntax Trees — Python 3.13.7 documentation, accessed August 25, 2025, [https://docs.python.org/3/library/ast.html](https://docs.python.org/3/library/ast.html)  
41. Abstract Syntax Trees In Python \- Pybites, accessed August 25, 2025, [https://pybit.es/articles/ast-intro/](https://pybit.es/articles/ast-intro/)  
42. How to transform Python dictionaries to tuples \- LabEx, accessed August 25, 2025, [https://labex.io/tutorials/python-how-to-transform-python-dictionaries-to-tuples-421903](https://labex.io/tutorials/python-how-to-transform-python-dictionaries-to-tuples-421903)  
43. The Art of Mocking in Python: A Comprehensive Guide | by ... \- Medium, accessed August 25, 2025, [https://medium.com/@moraneus/the-art-of-mocking-in-python-a-comprehensive-guide-8b619529458f](https://medium.com/@moraneus/the-art-of-mocking-in-python-a-comprehensive-guide-8b619529458f)  
44. Understanding the Python Mock Object Library \- Real Python, accessed August 25, 2025, [https://realpython.com/python-mock-library/](https://realpython.com/python-mock-library/)  
45. unittest.mock — getting started — Python 3.13.7 documentation, accessed August 25, 2025, [https://docs.python.org/3/library/unittest.mock-examples.html](https://docs.python.org/3/library/unittest.mock-examples.html)  
46. unittest.mock — mock object library — Python 3.13.7 documentation, accessed August 25, 2025, [https://docs.python.org/3/library/unittest.mock.html](https://docs.python.org/3/library/unittest.mock.html)  
47. Visual Regression Testing with Python \- TestingBot, accessed August 25, 2025, [https://testingbot.com/resources/articles/python-visual-testing](https://testingbot.com/resources/articles/python-visual-testing)  
48. Compare images Python PIL \- Stack Overflow, accessed August 25, 2025, [https://stackoverflow.com/questions/35176639/compare-images-python-pil](https://stackoverflow.com/questions/35176639/compare-images-python-pil)  
49. whtsky/pixelmatch-py: A fast pixel-level image comparison library, originally created to compare screenshots in tests. \- GitHub, accessed August 25, 2025, [https://github.com/whtsky/pixelmatch-py](https://github.com/whtsky/pixelmatch-py)  
50. Visual regression testing \- jounileino.com, accessed August 25, 2025, [https://jounileino.com/posts/2019-05-17-visual-regression-testing.html](https://jounileino.com/posts/2019-05-17-visual-regression-testing.html)