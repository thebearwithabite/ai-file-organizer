# Contributing to AI File Organizer

First off, thank you for considering contributing to the AI File Organizer! 🎉

## 🎯 Project Philosophy

This is an **ADHD-friendly AI file organizer** designed to make file management effortless. When contributing, please keep these principles in mind:

- **Reduce cognitive load** - Features should simplify, not complicate
- **Clear visual feedback** - Users should always know what's happening
- **Easy rollback** - Users must be able to undo any operation
- **Privacy first** - No PII in code, commits, or public issues

## 📋 Code of Conduct

- Be respectful and collaborative
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Protect user privacy at all costs

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Git
- Virtual environment (recommended)

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/thebearwithabite/ai-file-organizer.git
cd ai-file-organizer

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR: venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements_v3.txt
pip install -r requirements_cloud.txt

# Start the development server
python main.py
```

## 🔧 Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Your Changes

- Write clear, self-documenting code
- Follow existing code style and patterns
- Add comments for complex logic
- Keep changes focused and minimal

### 3. Test Your Changes

```bash
# Run relevant test files
python test_integration.py
python test_your_feature.py

# Start the server and test manually
python main.py
# Navigate to http://localhost:8000
```

### 4. Check for PII and Security Issues

**CRITICAL: Before committing:**

```bash
# Scrub any personal information
python scrub_personal_info.py

# Verify no credentials are exposed
git diff | grep -i "api_key\|password\|secret\|token"
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "type: Brief description

Longer explanation if needed. Focus on WHY the change was made.
"
```

Commit message types:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style/formatting
- `refactor:` Code refactoring
- `test:` Adding/updating tests
- `chore:` Maintenance tasks

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a PR using the template provided.

## 📝 Pull Request Guidelines

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No PII or sensitive data exposed
- [ ] Manual testing completed
- [ ] PR description is clear and complete

### PR Review Process

1. **Automated Checks** - CI will run tests and security scans
2. **Code Review** - Maintainer will review code quality
3. **Testing** - Manual testing of new features
4. **Approval** - Once approved, PR will be merged

## 🧪 Testing

### Running Tests

```bash
# Run specific test files
python test_integration.py
python test_hierarchical_organization.py

# Test the web interface
python main.py
# Then test at http://localhost:8000
```

### Writing Tests

- Create test files as `test_*.py`
- Use descriptive test names
- Test both success and failure cases
- Avoid hardcoding personal paths or data

## 🎨 Code Style

### Python Guidelines

- Follow PEP 8 style guide
- Use type hints where helpful
- Write docstrings for functions and classes
- Keep functions focused and small

Example:
```python
def organize_file(file_path: str, target_dir: str) -> bool:
    """
    Organize a file into the target directory.
    
    Args:
        file_path: Path to the file to organize
        target_dir: Destination directory
        
    Returns:
        True if successful, False otherwise
    """
    # Implementation here
    pass
```

### Documentation

- Keep README.md up to date
- Document new features in docs/
- Use clear, beginner-friendly language
- Include code examples

## 🔒 Security Guidelines

### PII Protection

**NEVER commit:**
- Real names, email addresses, phone numbers
- API keys, tokens, or credentials
- Actual file paths with personal information
- Screenshots containing personal data

**ALWAYS:**
- Use placeholder names (e.g., "Client Name", "User")
- Store credentials in environment variables
- Use `scrub_personal_info.py` before commits
- Review `.gitignore` entries

### Security Vulnerabilities

If you discover a security vulnerability:
1. **DO NOT** create a public issue
2. Contact the maintainer directly
3. Provide details privately
4. Wait for the fix before disclosing

## 📚 Documentation

### Where to Add Documentation

- **README.md** - Quick start and overview
- **CLAUDE.md** - AI assistant context
- **docs/** - Detailed guides and API docs
- **Code comments** - Complex logic explanation

### Documentation Style

- Write for beginners
- Include code examples
- Use clear headings
- Add screenshots for UI features

## 🤝 Getting Help

### Resources

- **Issues** - Check existing issues or create new ones
- **Discussions** - Ask questions or share ideas
- **Code** - Review CLAUDE.md for project context

### Questions?

Don't hesitate to:
- Open an issue with the "question" label
- Ask for clarification on existing issues
- Request help with development setup

## 🌟 Recognition

All contributors will be:
- Listed in the project's contributor section
- Credited in release notes
- Appreciated for their contributions!

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

**Thank you for contributing to making file organization easier for everyone, especially those with ADHD! 🎉**
