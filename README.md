# Mailcow CLI

A command-line tool for managing Mailcow mail servers via API. Supports mailboxes, aliases, sync jobs (imapsync), and transport maps.

## Features

- **Mailboxes**: Create, list, and update mailboxes with automatic password generation
- **Aliases**: Manage email aliases with batch import support
- **Sync Jobs**: Configure imapsync jobs for mail migration
- **Transport Maps**: Set up mail routing rules
- **Multiple Environments**: Support for multiple Mailcow instances via `.env` files
- **Batch Operations**: Import from CSV files for bulk operations
- **Multiple Output Formats**: Table, JSON, or CSV output

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd mailcow-cli

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

- Python 3.8+
- click
- requests
- python-dotenv

## Configuration

### Environment Variables

Create a `.env` file in the project directory:

```bash
# Required
MAILCOW_API_URL=https://mail.example.com
MAILCOW_API_KEY=your-api-key-here

# Optional - for sync jobs
MAILCOW_SRC_HOST=imap.old-server.com
MAILCOW_SRC_PORT=993
MAILCOW_SRC_ENC=SSL

# Optional - for mailboxes
MAILCOW_DOMAIN=example.com
```

### Multiple Environments

You can manage multiple Mailcow instances by creating multiple `.env` files:

```bash
.env              # default
.env.domain1      # for domain1.com
.env.domain2      # for domain2.com
```

Select the environment with the `-s` flag:

```bash
python mailcow_cli.py -s domain1 mailbox get
python mailcow_cli.py -s domain2 mailbox get
```

### Command Line Options

You can also pass credentials directly:

```bash
python mailcow_cli.py --api-url https://mail.example.com --api-key "YOUR_KEY" mailbox get
```

## Commands

### Mailboxes

#### List mailboxes

```bash
# List all mailboxes
python mailcow_cli.py mailbox get

# Filter by domain
python mailcow_cli.py mailbox get -d example.com

# Output as JSON
python mailcow_cli.py mailbox get -o json

# Output as CSV
python mailcow_cli.py mailbox get -o csv
```

#### Create mailbox

```bash
# Single mailbox with password
python mailcow_cli.py mailbox add -d example.com --local-part john --password "secret123"

# Single mailbox with auto-generated password
python mailcow_cli.py mailbox add -d example.com --local-part john --gen-password

# With full name
python mailcow_cli.py mailbox add -d example.com --local-part john.doe --name "John Doe" --gen-password

# Batch import from CSV
python mailcow_cli.py mailbox add -d example.com -f users.csv --gen-password

# Preview before creating
python mailcow_cli.py mailbox add -d example.com -f users.csv --gen-password --preview
```

**CSV format for mailboxes:**
```csv
local_part,name
john.doe,John Doe
jane.smith,Jane Smith
```

Or with passwords:
```csv
local_part,name,password
john.doe,John Doe,secret123
jane.smith,Jane Smith,password456
```

#### Update mailbox

```bash
# Update name
python mailcow_cli.py mailbox update john@example.com --name "John Smith"

# Change password
python mailcow_cli.py mailbox update john@example.com --password "newpassword"

# Set quota (in MB)
python mailcow_cli.py mailbox update john@example.com --quota 1024

# Deactivate mailbox
python mailcow_cli.py mailbox update john@example.com --no-active
```

### Aliases

#### List aliases

```bash
# List all aliases
python mailcow_cli.py alias get

# Filter by domain
python mailcow_cli.py alias get -d example.com

# Output as JSON
python mailcow_cli.py alias get -o json
```

#### Create alias

```bash
# Single alias
python mailcow_cli.py alias add --address info@example.com --goto john@example.com

# Multiple destinations
python mailcow_cli.py alias add --address sales@example.com --goto "john@example.com,jane@example.com"

# Batch import from CSV
python mailcow_cli.py alias add -f aliases.csv

# Preview before creating
python mailcow_cli.py alias add -f aliases.csv --preview
```

**CSV format for aliases:**
```csv
address,goto
info@example.com,john@example.com
sales@example.com,"john@example.com,jane@example.com"
```

#### Update alias

```bash
# Change destination
python mailcow_cli.py alias update 123 --goto newuser@example.com

# Deactivate alias
python mailcow_cli.py alias update 123 --no-active
```

### Sync Jobs (Mail Migration)

Sync jobs use imapsync to migrate emails from external IMAP servers to Mailcow.

#### List sync jobs

```bash
# List all sync jobs
python mailcow_cli.py jobs get

# Include logs (slower)
python mailcow_cli.py jobs get --include-log

# Output as JSON
python mailcow_cli.py jobs get -o json
```

#### Create sync job

```bash
# Single sync job
python mailcow_cli.py jobs add \
    --host1 imap.old-server.com \
    --user1 user@old-server.com \
    --password1 "oldpassword" \
    --username user@example.com

# With custom options
python mailcow_cli.py jobs add \
    --host1 imap.old-server.com \
    --port1 993 \
    --enc1 SSL \
    --user1 user@old-server.com \
    --password1 "oldpassword" \
    --username user@example.com \
    --mins-interval 60

# Dry run (simulate without transferring)
python mailcow_cli.py jobs add \
    --host1 imap.old-server.com \
    --user1 user@old-server.com \
    --password1 "oldpassword" \
    --username user@example.com \
    --dry

# Batch import from CSV
python mailcow_cli.py jobs add --host1 imap.old-server.com -f migrations.csv

# Preview before creating
python mailcow_cli.py jobs add --host1 imap.old-server.com -f migrations.csv --preview
```

**CSV format for sync jobs:**
```csv
user1,password1,username
old@old-server.com,oldpass,new@example.com
another@old-server.com,anotherpass,another@example.com
```

#### Update sync job

```bash
# Change sync interval
python mailcow_cli.py jobs update 5 --mins-interval 60

# Update source password
python mailcow_cli.py jobs update 5 --password1 "newpassword"

# Deactivate job
python mailcow_cli.py jobs update 5 --no-active

# Enable dry run mode
python mailcow_cli.py jobs update 5 --dry
```

### Transport Maps

Transport maps define how mail for specific destinations should be routed.

#### List transport maps

```bash
# List all transport maps
python mailcow_cli.py transport get

# Output as JSON
python mailcow_cli.py transport get -o json
```

#### Create transport map

```bash
# Route all mail for a domain through a relay
python mailcow_cli.py transport add \
    --destination example.com \
    --nexthop "[smtp.relay.com]:587"

# With authentication
python mailcow_cli.py transport add \
    --destination example.com \
    --nexthop "[smtp.relay.com]:587" \
    --username relay_user \
    --password relay_pass

# Batch import from CSV
python mailcow_cli.py transport add -f transports.csv

# Preview before creating
python mailcow_cli.py transport add -f transports.csv --preview
```

**CSV format for transport maps:**
```csv
destination,nexthop,username,password
example.com,[smtp.relay.com]:587,user,pass
other.com,[smtp2.relay.com]:25,,
```

#### Delete transport map

```bash
# Delete single transport map
python mailcow_cli.py transport delete 5

# Delete multiple
python mailcow_cli.py transport delete 5 6 7

# Skip confirmation
python mailcow_cli.py transport delete 5 -y
```

## Output Formats

All `get` commands support multiple output formats:

| Format | Flag | Description |
|--------|------|-------------|
| Table | `-o table` | Human-readable table (default) |
| JSON | `-o json` | Machine-readable JSON |
| CSV | `-o csv` | Comma-separated values |

Example:
```bash
python mailcow_cli.py mailbox get -o json > mailboxes.json
python mailcow_cli.py alias get -o csv > aliases.csv
```

## Password Generation

When using `--gen-password`, passwords are automatically generated with:
- 16 characters length
- At least 1 lowercase letter (a-z)
- At least 1 uppercase letter (A-Z)
- At least 1 digit (0-9)
- At least 1 special character (!@#$%&*)

Generated passwords are displayed in the output after successful creation.

## Preview Mode

All `add` commands support `--preview` to see what would be created without making API calls:

```bash
python mailcow_cli.py mailbox add -d example.com -f users.csv --gen-password --preview
python mailcow_cli.py alias add -f aliases.csv --preview
python mailcow_cli.py transport add -f transports.csv --preview
```

## API Documentation

This tool uses the Mailcow API. For more information:
- [Mailcow API Documentation](https://mailcow.docs.apiary.io/)
- Your Mailcow instance: `https://your-mailcow-server/api/`

## Examples

### Complete Mail Migration Workflow

```bash
# 1. Configure environment
cat > .env << EOF
MAILCOW_API_URL=https://mail.newserver.com
MAILCOW_API_KEY=your-api-key
MAILCOW_SRC_HOST=imap.oldserver.com
MAILCOW_DOMAIN=example.com
EOF

# 2. Create mailboxes from CSV
python mailcow_cli.py mailbox add -d example.com -f users.csv --gen-password -o csv > credentials.csv

# 3. Create sync jobs to migrate emails
python mailcow_cli.py jobs add --host1 imap.oldserver.com -f migrations.csv

# 4. Create aliases
python mailcow_cli.py alias add -f aliases.csv

# 5. Monitor sync jobs
python mailcow_cli.py jobs get
```

### Managing Multiple Domains

```bash
# Create environment files
echo "MAILCOW_API_URL=https://mail1.com
MAILCOW_API_KEY=key1
MAILCOW_DOMAIN=domain1.com" > .env.domain1

echo "MAILCOW_API_URL=https://mail2.com
MAILCOW_API_KEY=key2
MAILCOW_DOMAIN=domain2.com" > .env.domain2

# Work with domain1
python mailcow_cli.py -s domain1 mailbox get
python mailcow_cli.py -s domain1 mailbox add --local-part john --gen-password

# Work with domain2
python mailcow_cli.py -s domain2 mailbox get
python mailcow_cli.py -s domain2 mailbox add --local-part jane --gen-password
```

## License

MIT License
