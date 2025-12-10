#!/usr/bin/env python3
"""Minimal test version to verify Space startup."""

import gradio as gr

# Simple test UI
with gr.Blocks() as demo:
    gr.Markdown("# ✅ Space is Working!")
    gr.Markdown("The ModelOps trainer is online. Full app coming soon...")

demo.launch(server_name="0.0.0.0", server_port=7860)
