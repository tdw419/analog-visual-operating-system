"""
Visual backends for VisualPython rendering

This module provides different rendering backends for displaying
Python execution as visual operations.
"""

import time
import threading
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

# Import visual element class
try:
    from .core import VisualElement
except ImportError:
    # Fallback for standalone testing
    from dataclasses import dataclass
    
    @dataclass
    class VisualElement:
        element_type: str
        content: str
        x: int
        y: int
        color: str = '#00ff88'


class VisualBackend(ABC):
    """Abstract base class for visual backends"""
    
    @abstractmethod
    def render_elements(self, elements: List[VisualElement]):
        """Render visual elements to the display"""
        pass
    
    @abstractmethod
    def clear(self):
        """Clear the display"""
        pass
    
    @abstractmethod
    def update(self):
        """Update the display"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up resources"""
        pass


class ConsoleBackend(VisualBackend):
    """
    Console backend for text-based visual output
    
    This provides the core "no compilation" experience even in
    environments without GUI support.
    """
    
    def __init__(self, **kwargs):
        self.last_elements = []
        self.console_width = kwargs.get('width', 80)
        self.show_positions = kwargs.get('show_positions', False)
        self.color_mode = kwargs.get('color_mode', 'simple')  # 'simple', 'ansi', 'none'
        
        # ANSI color codes
        self.colors = {
            '#00ff88': '\033[92m',  # Green
            '#00ffff': '\033[96m',  # Cyan
            '#ffff00': '\033[93m',  # Yellow
            '#ff4444': '\033[91m',  # Red
            '#ff88ff': '\033[95m',  # Magenta
            '#ffffff': '\033[97m',  # White
            '#88ff88': '\033[92m',  # Light Green
            '#88ffff': '\033[96m',  # Light Cyan
        }
        self.reset_color = '\033[0m'
    
    def render_elements(self, elements: List[VisualElement]):
        """Render elements to console"""
        if not elements:
            return
        
        # Only show new elements to avoid spam
        new_elements = elements[len(self.last_elements):]
        
        for element in new_elements:
            self._render_element(element)
        
        self.last_elements = elements.copy()
    
    def _render_element(self, element: VisualElement):
        """Render a single element to console"""
        # Format content
        content = element.content
        
        if self.show_positions:
            content = f"[{element.x},{element.y}] {content}"
        
        # Apply color if supported
        if self.color_mode == 'ansi' and element.color in self.colors:
            content = f"{self.colors[element.color]}{content}{self.reset_color}"
        
        # Add element type indicator
        type_indicators = {
            'variable': '📊',
            'output': '💬',
            'error': '❌',
            'function_call': '🔧',
            'loop_start': '🔄',
            'loop_iteration': '  ↳',
            'if_condition': '❓',
            'assignment_error': '⚠️',
            'parse_error': '💥'
        }
        
        indicator = type_indicators.get(element.element_type, '▶️')
        
        print(f"{indicator} {content}")
    
    def clear(self):
        """Clear console display"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        self.last_elements = []
        
        print("🎯 VisualPython Console Display")
        print("=" * self.console_width)
    
    def update(self):
        """Console doesn't need explicit updates"""
        pass
    
    def cleanup(self):
        """No cleanup needed for console"""
        print("\n" + "=" * self.console_width)
        print("🎯 VisualPython execution complete")


try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


class TkinterBackend(VisualBackend):
    """
    Tkinter-based visual backend
    
    Provides a GUI window showing Python execution as visual elements
    """
    
    def __init__(self, width=800, height=600, **kwargs):
        if not TKINTER_AVAILABLE:
            raise ImportError("Tkinter not available")
        
        self.width = width
        self.height = height
        self.kwargs = kwargs
        
        # Create GUI components
        self.root = tk.Tk()
        self.root.title("VisualPython - Live Execution")
        self.root.geometry(f"{width}x{height}")
        self.root.configure(bg='#001122')
        
        self._setup_gui()
        
        # Element tracking
        self.canvas_elements = []
        self.text_elements = []
        
        # Start GUI in separate thread
        self.gui_thread = threading.Thread(target=self._run_gui, daemon=True)
        self.gui_thread.start()
    
    def _setup_gui(self):
        """Setup the GUI layout"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="🎯 VisualPython - No Compilation Execution",
            font=("Consolas", 14, "bold"),
            bg='#001122',
            fg='#00ff88'
        )
        title_label.pack(pady=(0, 10))
        
        # Create notebook for tabbed interface
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Visual canvas tab
        self.canvas_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.canvas_frame, text="Visual Display")
        
        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg='#001122',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Text output tab
        self.text_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.text_frame, text="Text Output")
        
        self.text_output = scrolledtext.ScrolledText(
            self.text_frame,
            bg='#001122',
            fg='#00ff88',
            font=("Consolas", 10),
            wrap=tk.WORD
        )
        self.text_output.pack(fill=tk.BOTH, expand=True)
        
        # Statistics tab
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="Statistics")
        
        self.stats_text = scrolledtext.ScrolledText(
            self.stats_frame,
            bg='#001122',
            fg='#ffff88',
            font=("Consolas", 10)
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_bar = tk.Label(
            main_frame,
            text="Ready for VisualPython execution...",
            font=("Consolas", 9),
            bg='#002244',
            fg='#88ffff',
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, pady=(5, 0))
    
    def _run_gui(self):
        """Run the Tkinter main loop"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"GUI error: {e}")
    
    def render_elements(self, elements: List[VisualElement]):
        """Render elements to Tkinter display"""
        if not elements:
            return
        
        try:
            # Schedule update on GUI thread
            self.root.after(0, self._update_display, elements)
        except Exception as e:
            print(f"Render error: {e}")
    
    def _update_display(self, elements: List[VisualElement]):
        """Update display with new elements"""
        # Clear previous elements
        self.canvas.delete("visual_element")
        
        # Group elements by type for better organization
        variables = []
        outputs = []
        others = []
        
        for element in elements:
            if element.element_type == 'variable':
                variables.append(element)
            elif element.element_type in ['output', 'print']:
                outputs.append(element)
            else:
                others.append(element)
        
        # Render variables section
        if variables:
            self._render_section("Variables", variables, start_y=30)
        
        # Render output section
        if outputs:
            self._render_section("Output", outputs, start_y=30 + len(variables) * 25 + 50)
        
        # Render other elements
        if others:
            self._render_section("Operations", others, 
                               start_y=30 + len(variables) * 25 + len(outputs) * 25 + 100)
        
        # Update text output
        self._update_text_output(elements)
        
        # Update statistics
        self._update_statistics(elements)
        
        # Update status
        self.status_bar.config(
            text=f"Rendered {len(elements)} elements | "
                 f"Variables: {len(variables)} | "
                 f"Output: {len(outputs)} | "
                 f"Time: {time.strftime('%H:%M:%S')}"
        )
    
    def _render_section(self, title: str, elements: List[VisualElement], start_y: int):
        """Render a section of elements"""
        # Section title
        self.canvas.create_text(
            20, start_y,
            text=f"▶ {title}:",
            font=("Consolas", 12, "bold"),
            fill='#ffff88',
            anchor=tk.W,
            tags="visual_element"
        )
        
        # Render elements
        for i, element in enumerate(elements):
            y_pos = start_y + 25 + (i * 25)
            
            # Text content
            self.canvas.create_text(
                40, y_pos,
                text=element.content,
                font=("Consolas", 10),
                fill=element.color,
                anchor=tk.W,
                tags="visual_element"
            )
            
            # Visual bar for numeric variables
            if (element.element_type == 'variable' and 
                'bar_width' in element.metadata):
                
                bar_width = element.metadata.get('bar_width', 0)
                self.canvas.create_rectangle(
                    300, y_pos - 8,
                    300 + bar_width, y_pos + 8,
                    fill=element.color,
                    outline='',
                    tags="visual_element"
                )
    
    def _update_text_output(self, elements: List[VisualElement]):
        """Update text output tab"""
        self.text_output.delete(1.0, tk.END)
        
        for element in elements:
            color_tag = f"color_{element.color.replace('#', '')}"
            
            # Configure color tag if not exists
            try:
                self.text_output.tag_configure(color_tag, foreground=element.color)
            except:
                pass
            
            # Insert text with color
            self.text_output.insert(tk.END, f"{element.content}\n", color_tag)
        
        # Scroll to bottom
        self.text_output.see(tk.END)
    
    def _update_statistics(self, elements: List[VisualElement]):
        """Update statistics tab"""
        self.stats_text.delete(1.0, tk.END)
        
        # Element type counts
        type_counts = {}
        for element in elements:
            type_counts[element.element_type] = type_counts.get(element.element_type, 0) + 1
        
        stats_text = "VisualPython Execution Statistics\n"
        stats_text += "=" * 40 + "\n\n"
        stats_text += f"Total Elements: {len(elements)}\n\n"
        
        stats_text += "Element Types:\n"
        for elem_type, count in type_counts.items():
            stats_text += f"  {elem_type}: {count}\n"
        
        stats_text += f"\nExecution Time: {time.strftime('%H:%M:%S')}\n"
        stats_text += f"Display Update: {time.time():.3f}\n"
        
        self.stats_text.insert(1.0, stats_text)
    
    def clear(self):
        """Clear the display"""
        try:
            self.root.after(0, self._clear_display)
        except:
            pass
    
    def _clear_display(self):
        """Clear display on GUI thread"""
        self.canvas.delete("all")
        self.text_output.delete(1.0, tk.END)
        self.stats_text.delete(1.0, tk.END)
        
        # Add title
        self.canvas.create_text(
            self.width // 2, 20,
            text="VisualPython - Ready for Execution",
            font=("Consolas", 14, "bold"),
            fill='#00ff88'
        )
    
    def update(self):
        """Update display (handled by events)"""
        pass
    
    def cleanup(self):
        """Clean up Tkinter resources"""
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass


try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class PyGameBackend(VisualBackend):
    """
    Pygame-based visual backend for high-performance rendering
    """
    
    def __init__(self, width=800, height=600, **kwargs):
        if not PYGAME_AVAILABLE:
            raise ImportError("Pygame not available")
        
        pygame.init()
        
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("VisualPython - Live Execution")
        
        # Colors
        self.colors = {
            '#001122': (0, 17, 34),
            '#00ff88': (0, 255, 136),
            '#00ffff': (0, 255, 255),
            '#ffff00': (255, 255, 0),
            '#ff4444': (255, 68, 68),
            '#ff88ff': (255, 136, 255),
            '#ffffff': (255, 255, 255),
            '#88ff88': (136, 255, 136),
            '#88ffff': (136, 255, 255),
        }
        
        # Font
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Background
        self.background = self.colors['#001122']
        
        self.running = True
    
    def render_elements(self, elements: List[VisualElement]):
        """Render elements with Pygame"""
        if not self.running:
            return
        
        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
        
        # Clear screen
        self.screen.fill(self.background)
        
        # Title
        title_text = self.font.render("VisualPython - No Compilation Execution", 
                                    True, self.colors['#00ff88'])
        self.screen.blit(title_text, (20, 10))
        
        # Render elements
        for element in elements:
            self._render_element(element)
        
        pygame.display.flip()
    
    def _render_element(self, element: VisualElement):
        """Render single element with Pygame"""
        color = self.colors.get(element.color, self.colors['#ffffff'])
        
        # Render text
        text_surface = self.small_font.render(element.content, True, color)
        self.screen.blit(text_surface, (element.x, element.y))
        
        # Render visual bars for variables
        if (element.element_type == 'variable' and 
            'bar_width' in element.metadata):
            
            bar_width = element.metadata['bar_width']
            bar_height = element.metadata.get('bar_height', 10)
            
            pygame.draw.rect(
                self.screen,
                color,
                (element.x + 200, element.y - 5, bar_width, bar_height)
            )
    
    def clear(self):
        """Clear Pygame display"""
        if self.running:
            self.screen.fill(self.background)
            pygame.display.flip()
    
    def update(self):
        """Update Pygame display"""
        if self.running:
            pygame.display.flip()
    
    def cleanup(self):
        """Clean up Pygame"""
        self.running = False
        pygame.quit()


class WebBackend(VisualBackend):
    """
    Web-based backend using HTTP server and browser display
    
    This creates a local web server that displays Python execution
    in a browser for maximum compatibility.
    """
    
    def __init__(self, width=800, height=600, port=8080, **kwargs):
        self.width = width
        self.height = height
        self.port = port
        self.elements = []
        
        # HTTP server setup would go here
        # This is a placeholder for the full web implementation
        print(f"WebBackend initialized on port {port}")
        print("Web backend is a placeholder - use Tkinter or Console backends")
    
    def render_elements(self, elements: List[VisualElement]):
        """Render elements to web display"""
        self.elements = elements
        # Would send elements to web page via WebSocket or HTTP
        print(f"Would render {len(elements)} elements to web display")
    
    def clear(self):
        """Clear web display"""
        self.elements = []
        print("Would clear web display")
    
    def update(self):
        """Update web display"""
        pass
    
    def cleanup(self):
        """Clean up web backend"""
        print("Web backend cleanup")


# Backend factory function
def create_backend(backend_name: str, **kwargs) -> VisualBackend:
    """
    Create a visual backend by name
    
    Args:
        backend_name: 'tkinter', 'pygame', 'console', or 'web'
        **kwargs: Backend-specific options
        
    Returns:
        VisualBackend instance
    """
    backends = {
        'console': ConsoleBackend,
        'tkinter': TkinterBackend if TKINTER_AVAILABLE else ConsoleBackend,
        'pygame': PyGameBackend if PYGAME_AVAILABLE else ConsoleBackend,
        'web': WebBackend
    }
    
    backend_class = backends.get(backend_name, ConsoleBackend)
    
    try:
        return backend_class(**kwargs)
    except Exception as e:
        print(f"Failed to create {backend_name} backend: {e}")
        print("Falling back to console backend")
        return ConsoleBackend(**kwargs)


if __name__ == "__main__":
    # Test backends
    print("Testing VisualPython backends...")
    
    # Test console backend
    console = ConsoleBackend()
    test_elements = [
        VisualElement('variable', 'x = 42', 50, 50),
        VisualElement('output', 'Hello World!', 400, 50, '#00ffff'),
        VisualElement('variable', 'y = 84', 50, 75, '#ffff00')
    ]
    
    console.render_elements(test_elements)
    console.cleanup()