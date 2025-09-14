# scripts/config.sh

if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

PROJECT_ID="qminesweeper"
REGION="europe-west1"
REPO="qms"
SERVICE="quantum-minesweeper"
