# Release Template

## Release Title Format
**v{VERSION} - {BRIEF_DESCRIPTION}**

## Release Description Template

### For Feature Releases
```markdown
## 🚀 Release {VERSION} - {RELEASE_NAME}

### ✨ New Features
- **Feature 1** - description
- **Feature 2** - description

### 🔧 Improvements  
- **Improvement 1** - description
- **Improvement 2** - description

### 🐛 Bug Fixes
- **Fix 1** - description
- **Fix 2** - description

## 📦 Installation

### Via pip (recommended)
```bash
pip install llm-proxifier=={VERSION}
```

### Pre-built Binaries
Platform-specific zip files available below:
- **Linux (amd64)** - `llm-proxifier-linux-amd64.zip`
- **Windows (amd64)** - `llm-proxifier-windows-amd64.exe.zip` 
- **macOS (amd64)** - `llm-proxifier-macos-amd64.zip`

## 🔗 Links
- **PyPI**: https://pypi.org/project/llm-proxifier/{VERSION}/
- **GitHub**: https://github.com/fluffypony/llm-proxifier
```

### For Patch/Fix Releases
```markdown
## 🔧 Release {VERSION} - {FIX_DESCRIPTION}

{BRIEF_DESCRIPTION_OF_WHAT_WAS_FIXED}

**Download**: Pre-built binaries available below or install via `pip install llm-proxifier=={VERSION}`

### What's Fixed
- {SPECIFIC_FIX_DETAILS}

### Installation
```bash
pip install llm-proxifier=={VERSION}
```
```

### For Infrastructure/Build Releases
```markdown
## 🏗️ Release {VERSION} - Infrastructure Improvements

{BRIEF_DESCRIPTION_OF_INFRASTRUCTURE_CHANGES}

**Download**: Pre-built binaries available below or install via `pip install llm-proxifier=={VERSION}`

### Build/Infrastructure Changes
- {CHANGE_1}
- {CHANGE_2}

*This release focuses on build system improvements. Core functionality unchanged.*
```

## Guidelines

### Release Naming Conventions
- **Major features**: `v0.2.0 - Feature Name`
- **Minor improvements**: `v0.1.8 - Improvements & Fixes`  
- **Bug fixes**: `v0.1.7 - Windows Build Fix`
- **Infrastructure**: `v0.1.6 - Enhanced Release Infrastructure`

### Description Guidelines
- Keep it concise for minor fixes
- Use emojis for visual appeal (🚀 ✨ 🔧 🐛 📦 🔗 🏗️)
- Always include installation instructions
- Link to PyPI for the specific version
- Mention if it's breaking change
- For infrastructure changes, note that core functionality is unchanged

### Binary Download Note
Always include: "Pre-built binaries available below or install via `pip install llm-proxifier`"

### Version Links
- Always link to the specific PyPI version page
- Include GitHub repository link
