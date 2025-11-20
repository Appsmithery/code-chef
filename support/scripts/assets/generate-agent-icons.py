#!/usr/bin/env python3
"""
Generate agent-specific icons from base minion design
Uses the 6 color variants provided in attachments
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
ICON_DIR = os.path.join(REPO_ROOT, "extensions", "vscode-devtools-copilot", "src", "icons")

# Icon size
SIZE = 512

# Agent configurations with color schemes from attachments
AGENTS = {
    "orchestrator": {
        "name": "Orchestrator",
        "bg_color": (203, 153, 201),  # Pink/Purple
        "fg_color": (60, 60, 60),
        "text": ".orchestrator",
        "letter": "O",
        "description": "Task Coordination"
    },
    "feature-dev": {
        "name": "Feature Dev",
        "bg_color": (255, 116, 92),  # Coral orange
        "fg_color": (60, 60, 60),
        "text": ".feature-dev",
        "letter": "F",
        "description": "Development"
    },
    "code-review": {
        "name": "Code Review",
        "bg_color": (42, 54, 99),  # Navy blue
        "fg_color": (255, 220, 100),  # Yellow text
        "text": ".code-review",
        "letter": "C",
        "description": "Quality Assurance"
    },
    "infrastructure": {
        "name": "Infrastructure",
        "bg_color": (162, 225, 218),  # Mint green
        "fg_color": (80, 80, 100),
        "text": ".infrastructure",
        "letter": "I",
        "description": "DevOps"
    },
    "cicd": {
        "name": "CI/CD",
        "bg_color": (42, 87, 46),  # Dark green
        "fg_color": (200, 220, 120),  # Light green text
        "text": ".cicd",
        "letter": "P",  # P for Pipeline
        "description": "Pipeline Automation"
    },
    "documentation": {
        "name": "Documentation",
        "bg_color": (71, 92, 214),  # Royal blue
        "fg_color": (255, 140, 70),  # Orange text
        "text": ".documentation",
        "letter": "D",
        "description": "Knowledge Management"
    }
}

def create_minion_icon(agent_id: str, config: dict):
    """Create a minion-style icon for an agent"""
    
    # Create base image with background color
    img = Image.new('RGBA', (SIZE, SIZE), config["bg_color"] + (255,))
    draw = ImageDraw.Draw(img)
    
    # Draw minion body (rounded rectangle)
    body_margin = 60
    corner_radius = 40
    
    # Draw rounded rectangle for body
    draw.rounded_rectangle(
        [(body_margin, body_margin + 20), (SIZE - body_margin, SIZE - body_margin - 20)],
        radius=corner_radius,
        fill=config["bg_color"] + (255,),
        outline=config["fg_color"] + (255,),
        width=8
    )
    
    # Draw antenna
    antenna_width = 8
    antenna_height = 30
    antenna_x = SIZE // 2
    draw.rectangle(
        [(antenna_x - antenna_width//2, body_margin - 10),
         (antenna_x + antenna_width//2, body_margin + 20)],
        fill=config["fg_color"] + (255,)
    )
    
    # Draw antenna ball
    ball_radius = 15
    draw.ellipse(
        [(antenna_x - ball_radius, body_margin - 10 - ball_radius*2),
         (antenna_x + ball_radius, body_margin - 10)],
        fill=config["fg_color"] + (255,)
    )
    
    # Draw eyes (two circles)
    eye_y = SIZE // 3 + 20
    eye_spacing = SIZE // 5
    eye_radius = 45
    
    # Left eye
    draw.ellipse(
        [(SIZE//2 - eye_spacing - eye_radius, eye_y - eye_radius),
         (SIZE//2 - eye_spacing + eye_radius, eye_y + eye_radius)],
        fill=(255, 255, 255, 255),
        outline=config["fg_color"] + (255,),
        width=6
    )
    
    # Right eye
    draw.ellipse(
        [(SIZE//2 + eye_spacing - eye_radius, eye_y - eye_radius),
         (SIZE//2 + eye_spacing + eye_radius, eye_y + eye_radius)],
        fill=(255, 255, 255, 255),
        outline=config["fg_color"] + (255,),
        width=6
    )
    
    # Draw pupils
    pupil_radius = 18
    draw.ellipse(
        [(SIZE//2 - eye_spacing - pupil_radius, eye_y - pupil_radius),
         (SIZE//2 - eye_spacing + pupil_radius, eye_y + pupil_radius)],
        fill=config["fg_color"] + (255,)
    )
    draw.ellipse(
        [(SIZE//2 + eye_spacing - pupil_radius, eye_y - pupil_radius),
         (SIZE//2 + eye_spacing + pupil_radius, eye_y + pupil_radius)],
        fill=config["fg_color"] + (255,)
    )
    
    # Draw smile
    mouth_y = eye_y + 70
    mouth_width = 120
    draw.arc(
        [(SIZE//2 - mouth_width//2, mouth_y - 30),
         (SIZE//2 + mouth_width//2, mouth_y + 30)],
        start=0, end=180,
        fill=config["fg_color"] + (255,),
        width=6
    )
    
    # Draw text at bottom
    try:
        # Try to load a nice font
        font = ImageFont.truetype("arial.ttf", 32)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        except:
            font = ImageFont.load_default()
    
    text = config["text"]
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (SIZE - text_width) // 2
    text_y = SIZE - 80
    
    draw.text((text_x, text_y), text, font=font, fill=config["fg_color"] + (255,))
    
    # Save the icon
    os.makedirs(ICON_DIR, exist_ok=True)
    output_path = os.path.join(ICON_DIR, f"{agent_id}.png")
    img.save(output_path)
    print(f"✓ Created {agent_id}.png ({config['name']})")
    
    return output_path

def create_agent_mapping_doc():
    """Create documentation for agent icon mapping"""
    
    doc_content = f"""# Agent Icon Mapping

Generated: {os.path.basename(__file__)}

## Icon Files

"""
    
    for agent_id, config in AGENTS.items():
        doc_content += f"### {config['name']} (`{agent_id}`)\n"
        doc_content += f"- **File**: `src/icons/{agent_id}.png`\n"
        doc_content += f"- **Color**: RGB{config['bg_color']}\n"
        doc_content += f"- **Letter**: {config['letter']}\n"
        doc_content += f"- **Description**: {config['description']}\n\n"
    
    doc_content += """
## Usage

### In Linear

1. Go to Linear → Settings → Teams → Project Roadmaps
2. Navigate to Labels
3. For each agent label, click to edit
4. Upload the corresponding icon from `extensions/vscode-devtools-copilot/src/icons/`

### In VS Code Extension

Icons are automatically available via the `src/icons/` directory. Reference them in TypeScript:

```typescript
const agentIcons: Record<string, vscode.Uri> = {
    orchestrator: vscode.Uri.file(path.join(context.extensionPath, 'src/icons/orchestrator.png')),
    'feature-dev': vscode.Uri.file(path.join(context.extensionPath, 'src/icons/feature-dev.png')),
    'code-review': vscode.Uri.file(path.join(context.extensionPath, 'src/icons/code-review.png')),
    infrastructure: vscode.Uri.file(path.join(context.extensionPath, 'src/icons/infrastructure.png')),
    cicd: vscode.Uri.file(path.join(context.extensionPath, 'src/icons/cicd.png')),
    documentation: vscode.Uri.file(path.join(context.extensionPath, 'src/icons/documentation.png'))
};
```

## Color Scheme

| Agent | Background | Text/Outline | Theme |
|-------|-----------|--------------|-------|
| Orchestrator | Pink/Purple | Dark Gray | Coordination |
| Feature Dev | Coral Orange | Dark Gray | Development |
| Code Review | Navy Blue | Yellow | Quality |
| Infrastructure | Mint Green | Blue-Gray | DevOps |
| CI/CD | Dark Green | Light Green | Automation |
| Documentation | Royal Blue | Orange | Knowledge |
"""
    
    doc_path = os.path.join(ICON_DIR, "README.md")
    with open(doc_path, 'w') as f:
        f.write(doc_content)
    
    print(f"✓ Created icon documentation: {doc_path}")

def main():
    """Generate all agent icons"""
    print("Generating agent icons...")
    print(f"Output directory: {ICON_DIR}\n")
    
    for agent_id, config in AGENTS.items():
        create_minion_icon(agent_id, config)
    
    create_agent_mapping_doc()
    
    print(f"\n✅ Generated {len(AGENTS)} agent icons successfully!")
    print("\nNext steps:")
    print("1. Review icons in extensions/vscode-devtools-copilot/src/icons/")
    print("2. Update extension.ts to use agent-specific icons")
    print("3. Upload icons to Linear labels")
    print("4. Commit and push changes")

if __name__ == "__main__":
    main()
