# Contributing to Pentagent

Thank you for your interest in contributing to Pentagent! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/pentagent.git`
3. Create a feature branch: `git checkout -b feature/amazing-feature`
4. Make your changes
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to your branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📋 Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions small and focused

### Testing
- Write tests for new features
- Ensure all existing tests pass
- Test with different target types (web apps, APIs, etc.)

### Documentation
- Update README.md for new features
- Add docstrings to new functions
- Update API documentation if applicable

## 🛠️ Tool Development

### Adding New Tools

1. Create a new tool file in `tools/` directory
2. Inherit from `MCPTool` base class
3. Implement required methods:
   - `run_tool()`: Main tool execution
   - `_create_final_output()`: Output formatting
   - `_generate_recommendations()`: Dynamic recommendations

### Tool Structure
```python
class NewToolModule(MCPTool):
    def __init__(self):
        super().__init__(
            name="new_tool",
            description="Tool description",
            category=ToolCategory.CATEGORY
        )
    
    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Tool implementation
        pass
```

## 🐛 Bug Reports

When reporting bugs, please include:
- Description of the bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)
- Error messages/logs

## 💡 Feature Requests

When requesting features, please include:
- Description of the feature
- Use case/justification
- Proposed implementation (if you have ideas)
- Any additional context

## 📝 Pull Request Process

1. Ensure your code follows the style guidelines
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass
5. Request review from maintainers

## 🔒 Security

- Never commit API keys or sensitive data
- Report security vulnerabilities privately
- Follow responsible disclosure practices

## 📞 Contact

- Discord: [Pentagent Community](https://discord.gg/pentagent)
- Email: security@pentagent.com

Thank you for contributing to Pentagent! 🛡️
