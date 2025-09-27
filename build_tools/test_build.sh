#!/bin/bash

# Test build process (dry run)
# Checks if all dependencies are available for building

set -e

echo "🧪 Testing build requirements..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ Python: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

# Check if in virtual environment or can install packages
echo -e "\n${BLUE}📦 Checking Python packages...${NC}"

# Test if we can import required packages
python3 -c "
import sys
packages = ['customtkinter', 'psutil', 'rich', 'PIL']
missing = []

for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg}')
    except ImportError:
        missing.append(pkg)
        print(f'❌ {pkg} - MISSING')

if missing:
    print(f'\n📥 To install missing packages:')
    print(f'pip install {\" \".join(missing)}')
    sys.exit(1)
else:
    print('\n✅ All required packages available')
"

# Check PyInstaller
if command -v pyinstaller &> /dev/null; then
    echo -e "${GREEN}✅ PyInstaller available${NC}"
else
    echo -e "${RED}❌ PyInstaller not found${NC}"
    echo "Install with: pip install pyinstaller"
    exit 1
fi

# Check if files exist
echo -e "\n${BLUE}📁 Checking source files...${NC}"

required_files=("rw_tunnel_gui.py" "rw-local-tunnel.py" "requirements.txt")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ $file - MISSING${NC}"
        exit 1
    fi
done

echo -e "\n${GREEN}🎉 All build requirements satisfied!${NC}"
echo -e "\n${BLUE}To build the applications:${NC}"
echo -e "1. ${BLUE}source venv/bin/activate${NC} (if using virtual environment)"
echo -e "2. ${BLUE}./scripts/build.sh${NC}"
echo -e "3. ${BLUE}./scripts/install-desktop.sh${NC} (for desktop integration)"

echo -e "\n${BLUE}Expected outputs:${NC}"
echo -e "• ${GREEN}dist/rw-local-tunnel-cli${NC} - Command line version"
echo -e "• ${GREEN}dist/rw-local-tunnel-gui${NC} - Desktop GUI version"