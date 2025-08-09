#!/bin/bash
# setup.sh — Make your Eve experience soar
# ------------------------------------------
set -e

# 1. Set up a Python virtual environment (if not already present)
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# 2. Activate the virtual environment
echo "Activating virtualenv..."
source venv/bin/activate

# 3. Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Provide a .env stub if user doesn't have one
if [ ! -f ".env" ]; then
    echo "Creating a .env file stub. Don’t forget to fill in your secrets!"
    cat <<EOT > .env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-0613
USERNAME=your_name
EOT
else
    echo ".env file already exists."
fi

echo "\nAll done! To begin your adventure, run:"
echo "source venv/bin/activate && python agent.py"
echo "(Or use: ./setup.sh whenever you need to reinvoke setup magic!)"
echo "\nEve is ready to soar. 🐉✨"