#!/bin/bash
#
# Setup Weekly Cleanup Cron Job on Droplet
#
# This script:
# 1. Copies the weekly-cleanup.sh script to the droplet
# 2. Makes it executable
# 3. Installs a cron job to run it every Sunday at 3 AM
#

set -e

DROPLET_HOST="codechef.appsmithery.co"
DROPLET_IP="45.55.173.72"  # For SSH
DROPLET_USER="root"
DEPLOY_PATH="/opt/Dev-Tools"
SCRIPT_NAME="weekly-cleanup.sh"
CRON_SCHEDULE="0 3 * * 0"

echo "🔧 Setting up weekly Docker cleanup cron job on $DROPLET_HOST..."
echo ""

# Check if cleanup script exists locally
if [ ! -f "support/scripts/maintenance/$SCRIPT_NAME" ]; then
    echo "❌ Error: $SCRIPT_NAME not found in support/scripts/maintenance/"
    exit 1
fi

# Copy script to droplet
echo "📤 Copying cleanup script to droplet..."
scp support/scripts/maintenance/$SCRIPT_NAME $DROPLET_USER@$DROPLET_IP:$DEPLOY_PATH/support/scripts/maintenance/

# Make script executable and install cron job
echo "⚙️  Installing cron job..."
ssh $DROPLET_USER@$DROPLET_IP << 'EOF'
    SCRIPT_PATH="/opt/Dev-Tools/support/scripts/maintenance/weekly-cleanup.sh"
    CRON_SCHEDULE="0 3 * * 0"
    LOG_FILE="/var/log/docker-cleanup.log"
    
    # Make script executable
    chmod +x "$SCRIPT_PATH"
    
    # Create log file with proper permissions
    touch "$LOG_FILE"
    chmod 644 "$LOG_FILE"
    
    # Remove existing cron job if it exists
    crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH" | crontab - || true
    
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $SCRIPT_PATH >> $LOG_FILE 2>&1") | crontab -
    
    # Verify cron job was added
    echo ""
    echo "✅ Cron job installed successfully"
    echo ""
    echo "Current crontab:"
    crontab -l | grep -E "(weekly-cleanup|SHELL|PATH)" || crontab -l
    
    echo ""
    echo "Schedule: Every Sunday at 3:00 AM UTC"
    echo "Script: $SCRIPT_PATH"
    echo "Log: $LOG_FILE"
EOF

echo ""
echo "✅ Weekly cleanup cron job setup complete!"
echo ""
echo "Next steps:"
echo "  1. Verify cron job: ssh $DROPLET_USER@$DROPLET_IP 'crontab -l'"
echo "  2. Test script manually: ssh $DROPLET_USER@$DROPLET_IP '$DEPLOY_PATH/support/scripts/maintenance/$SCRIPT_NAME'"
echo "  3. Check logs: ssh $DROPLET_USER@$DROPLET_IP 'tail -f /var/log/docker-cleanup.log'"
echo ""
