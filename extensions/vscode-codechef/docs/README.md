# Visual Assets for VS Code Marketplace

This folder contains visual assets for the VS Code Marketplace listing.

## Required Assets

### Screenshots (5-7 recommended)

Create these screenshots at **1920x1080px or higher**:

1. **screenshot-chat.png** - Chat participant in action (@chef responding to user)
2. **screenshot-settings.png** - Settings UI showcase
3. **screenshot-modelops.png** - ModelOps training wizard
4. **screenshot-approval.png** - Approval workflow notification
5. **screenshot-tokens.png** - Token usage tracking display
6. **screenshot-statusbar.png** - Status bar menu
7. **screenshot-workflow.png** - Workflow selection interface

### Animated Demo (Optional but Recommended)

- **demo.gif** or **demo.mp4** - 30-second workflow showing "@chef build REST API" end-to-end
- Keep file size < 10MB for marketplace
- Show: prompt → routing → agent response → code generation

### Marketplace Banner

- **marketplace-banner.png** - 1280x640px
- Include chef hat logo + tagline
- Use brand colors: Mint (#bcece0), Lavender (#887bb0), Butter (#fff4bd)
- Export as PNG with transparency

## Brand Guidelines

Follow the brand standards defined in `/frontend/brand-standards.md`:

- **Primary colors**: Mint (#bcece0), Lavender (#887bb0)
- **Accent colors**: Butter (#fff4bd), Salmon (#f4b9b8)
- **Font**: Fira Code

## File Naming

Use consistent naming:

- `screenshot-*.png` for static images
- `demo.gif` or `demo.mp4` for animations
- `marketplace-banner.png` for the marketplace header

## Usage in README

Reference these in the main README.md:

```markdown
![Chat Participant](docs/screenshot-chat.png)
![Settings](docs/screenshot-settings.png)
```
