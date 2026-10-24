CHIRAQ CHRONICLES PRIZE WHEEL

STARTING PRIZES
- Donor Car
- $5,000 Cash
- $5,000 Cash
- $2,500 Cash
- Air Soft Gun
- Melee Weapon
- Legal Item Pack
- Illegal Item Pack

SETUP
1. Create a Discord application/bot in the Discord Developer Portal.
2. Enable Server Members Intent for the bot.
3. Invite the bot with bot + applications.commands scopes.
4. In your cloud host, set environment variables using .env.example.
   Never post or share your bot token.
5. Install: pip install -r requirements.txt
6. Start: python bot.py

COMMANDS
/prizewheel @winner - authorized staff starts a winner's wheel
/prize_list - view wheel slots
/prize_add <name> - Admin/Head Staff adds a slot
/prize_remove <exact name> - Admin/Head Staff removes one matching slot
/prize_reset - resets the original 8 slots

HOW IT WORKS
Staff selects the winner. Only that winner can press SPIN THE WHEEL. The bot visibly cycles through a short spinning/slowing animation, reveals one randomly selected prize publicly, disables the button, asks the winner to give staff their City ID #, and logs the result to the configured staff log channel.

NOTE
This Discord-native version animates by updating the message through several spin states. A literal rotating graphical wheel/GIF can be added later, but this version is ready to run without external image hosting.
