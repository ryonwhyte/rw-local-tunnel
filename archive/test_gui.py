#!/usr/bin/env python3
"""
Simple test for GUI functionality without requiring root
"""

import customtkinter as ctk
import tkinter as tk

def test_gui():
    """Test basic GUI functionality"""

    # Set theme
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Create root window
    root = ctk.CTk()
    root.title("RW Tunnel GUI Test")
    root.geometry("800x600")

    # Main frame
    main_frame = ctk.CTkFrame(root)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Title
    title = ctk.CTkLabel(
        main_frame,
        text="🌐 RW Local Tunnel GUI Test",
        font=ctk.CTkFont(size=24, weight="bold")
    )
    title.pack(pady=20)

    # Status frame
    status_frame = ctk.CTkFrame(main_frame)
    status_frame.pack(fill="x", padx=20, pady=10)

    status_label = ctk.CTkLabel(
        status_frame,
        text="✅ GUI Framework Working",
        font=ctk.CTkFont(size=14)
    )
    status_label.pack(pady=10)

    # Test components
    test_frame = ctk.CTkFrame(main_frame)
    test_frame.pack(fill="x", padx=20, pady=10)

    ctk.CTkLabel(
        test_frame,
        text="Test Components:",
        font=ctk.CTkFont(size=16, weight="bold")
    ).pack(pady=5)

    # Port entry
    port_frame = ctk.CTkFrame(test_frame)
    port_frame.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(port_frame, text="Port:").pack(side="left", padx=5)
    port_entry = ctk.CTkEntry(port_frame, placeholder_text="8080")
    port_entry.pack(side="left", padx=5)

    # Radio buttons
    radio_frame = ctk.CTkFrame(test_frame)
    radio_frame.pack(fill="x", padx=10, pady=5)

    radio_var = ctk.StringVar(value="vps")
    ctk.CTkLabel(radio_frame, text="Access:").pack(side="left", padx=5)
    ctk.CTkRadioButton(radio_frame, text="VPS Only", variable=radio_var, value="vps").pack(side="left", padx=5)
    ctk.CTkRadioButton(radio_frame, text="Full Tailnet", variable=radio_var, value="tailnet").pack(side="left", padx=5)

    # Test button
    def test_action():
        port = port_entry.get() or "8080"
        scope = radio_var.get()
        result_label.configure(text=f"✅ Would create tunnel: Port {port}, Scope: {scope.upper()}")

    test_btn = ctk.CTkButton(
        test_frame,
        text="🧪 Test Action",
        command=test_action
    )
    test_btn.pack(pady=10)

    # Result label
    result_label = ctk.CTkLabel(
        test_frame,
        text="Click test button to verify functionality",
        font=ctk.CTkFont(size=12)
    )
    result_label.pack(pady=5)

    # Scrollable frame test
    scroll_frame = ctk.CTkScrollableFrame(main_frame, height=200)
    scroll_frame.pack(fill="x", padx=20, pady=10)

    ctk.CTkLabel(
        scroll_frame,
        text="Scrollable Area Test",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(pady=5)

    for i in range(10):
        item_frame = ctk.CTkFrame(scroll_frame)
        item_frame.pack(fill="x", padx=5, pady=2)

        ctk.CTkLabel(
            item_frame,
            text=f"📊 Test Tunnel Item {i+1}",
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=10, pady=5)

        ctk.CTkButton(
            item_frame,
            text="Stop",
            width=60,
            height=25
        ).pack(side="right", padx=10, pady=5)

    # Info
    info_label = ctk.CTkLabel(
        main_frame,
        text="GUI test successful! All components working properly.",
        font=ctk.CTkFont(size=12),
        text_color="gray"
    )
    info_label.pack(pady=10)

    # Run the GUI
    root.mainloop()

if __name__ == "__main__":
    test_gui()