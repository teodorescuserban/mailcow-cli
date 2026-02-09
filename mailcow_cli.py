#!/usr/bin/env python3
"""
Mailcow CLI - Tool for managing Mailcow via API

Usage:
    python mailcow_cli.py jobs get
    python mailcow_cli.py jobs add --user1 src@old.com --password1 pass --username dest@new.com
    python mailcow_cli.py jobs add -f users.csv --host1 mail.example.com
    python mailcow_cli.py mailbox get
    python mailcow_cli.py mailbox add -d example.com --local-part john --password secret
    python mailcow_cli.py mailbox add -d example.com -f users.csv --gen-password
    python mailcow_cli.py mailbox update john@example.com --name "John Doe"
    python mailcow_cli.py alias get
    python mailcow_cli.py alias add --address alias@example.com --goto user@example.com
    python mailcow_cli.py alias add -f aliases.csv
    python mailcow_cli.py alias update 123 --goto newdest@example.com
    python mailcow_cli.py transport get
    python mailcow_cli.py transport add --destination example.com --nexthop [smtp.relay.com]:587
    python mailcow_cli.py transport delete 5
    python mailcow_cli.py --api-url https://mail.example.com --api-key "KEY" jobs get

Supported environment variables (global):
    MAILCOW_API_URL - Mailcow server URL
    MAILCOW_API_KEY - API key for authentication

Supported environment variables (for sync jobs):
    MAILCOW_SRC_HOST - Source IMAP host
    MAILCOW_SRC_PORT - Source IMAP port (default: 993)
    MAILCOW_SRC_ENC  - Source encryption: SSL, TLS, PLAIN (default: SSL)

Supported environment variables (for mailboxes):
    MAILCOW_DOMAIN   - Default domain for mailbox operations

API Documentation: https://mailcow.docs.apiary.io/
"""

import csv
import json
import sys

import click
import requests
import os
import sys

# When running under pytest we should not pick up the user's shell
# environment variables for Click `envvar` options. Detect pytest by
# checking for the pytest module or pytest-specific env marker.
IN_PYTEST = 'PYTEST_CURRENT_TEST' in os.environ or 'PYTEST_RUNNING' in os.environ or 'pytest' in sys.modules

def _envvar(name: str):
    return name if not IN_PYTEST else None


# Default sync job options (imapsync best practices)
SYNC_DEFAULTS = {
    'port1': '993',
    'enc1': 'SSL',
    'mins_interval': '20',
    'timeout1': '600',
    'timeout2': '600',
    'maxage': '0',
    'maxbytespersecond': '0',
    'exclude': '(?i)spam|(?i)junk',
    'delete1': '0',
    'delete2': '0',
    'delete2duplicates': '1',
    'automap': '1',
    'skipcrossduplicates': '0',
    'subscribeall': '1',
    'active': '1',
}


class MailcowClient:
    """Client for Mailcow API."""

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Execute an HTTP request to the API."""
        url = f"{self.api_url}/api/v1/{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            click.echo(f"HTTP Error {response.status_code}: {response.text}", err=True)
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            click.echo(f"Connection error: {e}", err=True)
            sys.exit(1)

    def _check_response(self, result) -> tuple[bool, str]:
        """
        Check Mailcow API response.
        Returns (success: bool, message: str)

        Mailcow returns various formats:
        - [{"type": "success/error", "msg": "..."}]
        - ["object_exists", "email@domain.com"]
        """
        if not result:
            return False, "Empty response"

        if isinstance(result, list) and len(result) > 0:
            first = result[0]

            # Format: [{"type": "success/error", "msg": "..."}]
            if isinstance(first, dict):
                msg_type = first.get('type', 'unknown')
                msg = first.get('msg', str(result))
                return msg_type == 'success', msg

            # Format: ["object_exists", "email@domain.com"]
            if isinstance(first, str):
                if first in ('object_exists', 'error'):
                    return False, ' '.join(result)
                # Could be success in some other format
                return False, ' '.join(result)

        return False, str(result)

    def get_sync_jobs(self, include_log: bool = False) -> list:
        """
        Get all sync jobs.

        API: GET /api/v1/get/syncjobs/all/no_log
        """
        endpoint = "get/syncjobs/all" if include_log else "get/syncjobs/all/no_log"
        return self._request("GET", endpoint)

    def add_sync_job(self, username: str, host1: str, user1: str, password1: str,
                     port1: str = None, enc1: str = None, **kwargs) -> dict:
        """
        Create a new sync job.

        API: POST /api/v1/add/syncjob

        Required:
            username: destination mailbox in Mailcow
            host1: source IMAP server
            user1: source mailbox username
            password1: source mailbox password

        Optional (with defaults from SYNC_DEFAULTS):
            port1, enc1, mins_interval, timeout1, timeout2,
            maxage, maxbytespersecond, exclude, delete1, delete2,
            delete2duplicates, automap, skipcrossduplicates, subscribeall, active
        """
        payload = {**SYNC_DEFAULTS}
        payload.update({
            'username': username,
            'host1': host1,
            'user1': user1,
            'password1': password1,
        })
        if port1:
            payload['port1'] = port1
        if enc1:
            payload['enc1'] = enc1

        # Override with any extra kwargs
        for k, v in kwargs.items():
            if v is not None:
                payload[k] = str(v) if not isinstance(v, str) else v

        return self._request("POST", "add/syncjob", payload)

    def update_sync_job(self, job_id: str, **kwargs) -> dict:
        """
        Update an existing sync job.

        API: POST /api/v1/edit/syncjob

        Required:
            job_id: sync job ID (or list of IDs)

        Optional:
            All syncjob parameters except username (destination)
        """
        payload = {
            'items': [job_id] if not isinstance(job_id, list) else job_id,
            'attr': {}
        }

        # Map CLI option names to API parameter names
        for k, v in kwargs.items():
            if v is not None:
                payload['attr'][k] = str(v) if not isinstance(v, str) else v

        return self._request("POST", "edit/syncjob", payload)

    def get_mailboxes(self) -> list:
        """
        Get all mailboxes.

        API: GET /api/v1/get/mailbox/all
        """
        return self._request("GET", "get/mailbox/all")

    def add_mailbox(self, local_part: str, domain: str, password: str,
                    name: str = '', quota: str = '0', active: str = '1',
                    force_pw_update: str = '0', tls_enforce_in: str = '0',
                    tls_enforce_out: str = '0', **kwargs) -> dict:
        """
        Create a new mailbox.

        API: POST /api/v1/add/mailbox

        Required:
            local_part: local part of email (before @)
            domain: domain part of email (after @)
            password: mailbox password

        Optional:
            name: full name of user
            quota: quota in MB (0 = domain default)
            active: 1 = active, 0 = inactive
            force_pw_update: force password change on first login
            tls_enforce_in: require TLS for incoming
            tls_enforce_out: require TLS for outgoing
        """
        payload = {
            'local_part': local_part,
            'domain': domain,
            'password': password,
            'password2': password,
            'name': name,
            'quota': quota,
            'active': active,
            'force_pw_update': force_pw_update,
            'tls_enforce_in': tls_enforce_in,
            'tls_enforce_out': tls_enforce_out,
        }

        # Override with any extra kwargs
        for k, v in kwargs.items():
            if v is not None:
                payload[k] = str(v) if not isinstance(v, str) else v

        return self._request("POST", "add/mailbox", payload)

    def update_mailbox(self, username: str, **kwargs) -> dict:
        """
        Update an existing mailbox.

        API: POST /api/v1/edit/mailbox

        Required:
            username: full email address of the mailbox

        Optional:
            name, quota, active, force_pw_update, password,
            tls_enforce_in, tls_enforce_out, etc.
        """
        payload = {
            'items': [username] if not isinstance(username, list) else username,
            'attr': {}
        }

        for k, v in kwargs.items():
            if v is not None:
                payload['attr'][k] = str(v) if not isinstance(v, str) else v

        return self._request("POST", "edit/mailbox", payload)

    def get_aliases(self) -> list:
        """
        Get all aliases.

        API: GET /api/v1/get/alias/all
        """
        return self._request("GET", "get/alias/all")

    def add_alias(self, address: str, goto: str, active: str = '1',
                  sogo_visible: str = '1', **kwargs) -> dict:
        """
        Create a new alias.

        API: POST /api/v1/add/alias

        Required:
            address: alias email address
            goto: comma-separated list of destination addresses

        Optional:
            active: 1 = active, 0 = inactive
            sogo_visible: 1 = visible in SOGo, 0 = hidden
        """
        payload = {
            'address': address,
            'goto': goto,
            'active': active,
            'sogo_visible': sogo_visible,
        }

        for k, v in kwargs.items():
            if v is not None:
                payload[k] = str(v) if not isinstance(v, str) else v

        return self._request("POST", "add/alias", payload)

    def update_alias(self, alias_id: str, **kwargs) -> dict:
        """
        Update an existing alias.

        API: POST /api/v1/edit/alias

        Required:
            alias_id: alias ID (or list of IDs)

        Optional:
            address, goto, active, sogo_visible
        """
        payload = {
            'items': [alias_id] if not isinstance(alias_id, list) else alias_id,
            'attr': {}
        }

        for k, v in kwargs.items():
            if v is not None:
                payload['attr'][k] = str(v) if not isinstance(v, str) else v

        return self._request("POST", "edit/alias", payload)

    def get_transports(self) -> list:
        """
        Get all transport maps.

        API: GET /api/v1/get/transport/all
        """
        return self._request("GET", "get/transport/all")

    def add_transport(self, destination: str, nexthop: str,
                      username: str = '', password: str = '',
                      active: str = '1', **kwargs) -> dict:
        """
        Create a new transport map.

        API: POST /api/v1/add/transport

        Required:
            destination: destination domain/pattern (e.g., example.com or .example.com)
            nexthop: next hop server (e.g., [smtp.relay.com]:587)

        Optional:
            username: SMTP auth username
            password: SMTP auth password
            active: 1 = active, 0 = inactive
        """
        payload = {
            'destination': destination,
            'nexthop': nexthop,
            'username': username,
            'password': password,
            'active': active,
        }

        for k, v in kwargs.items():
            if v is not None:
                payload[k] = str(v) if not isinstance(v, str) else v

        return self._request("POST", "add/transport", payload)

    def delete_transport(self, transport_ids: list) -> dict:
        """
        Delete transport map(s).

        API: POST /api/v1/delete/transport

        Required:
            transport_ids: list of transport IDs to delete
        """
        if not isinstance(transport_ids, list):
            transport_ids = [transport_ids]

        return self._request("POST", "delete/transport", transport_ids)


class Context:
    """Context object for passing the client between commands."""
    def __init__(self):
        self.client = None


pass_context = click.make_pass_decorator(Context, ensure=True)


def _select_env_callback(ctx, param, value):
    """
    Callback to set MAILCOW_ENV_FILE based on --select-env option.
    This is eager=True so it runs before other options are processed.
    """
    if value:
        # Set the env file name (will be loaded at module __main__)
        os.environ['MAILCOW_ENV_FILE'] = value
    return value


@click.group()
@click.option(
    '-s', '--select-env',
    default=None,
    callback=_select_env_callback,
    is_eager=True,
    expose_value=False,
    help='Select .env file variant (e.g., -s domeniu1 loads .env.domeniu1)'
)
@click.option(
    '--api-url',
    envvar=_envvar('MAILCOW_API_URL'),
    required=True,
    help='Mailcow server URL (env: MAILCOW_API_URL)'
)
@click.option(
    '--api-key',
    envvar=_envvar('MAILCOW_API_KEY'),
    required=True,
    help='Mailcow API key (env: MAILCOW_API_KEY)'
)
@pass_context
def cli(ctx, api_url, api_key):
    """Mailcow CLI - Manage Mailcow via API.

    API Documentation: https://mailcow.docs.apiary.io/
    """
    ctx.client = MailcowClient(api_url, api_key)


@cli.group()
def jobs():
    """Manage sync jobs (imapsync).

    Sync jobs are used to copy/move emails
    from an external IMAP server to Mailcow.
    """
    pass


@jobs.command('get')
@click.option(
    '--output', '-o',
    type=click.Choice(['table', 'json', 'csv']),
    default='table',
    help='Output format (default: table)'
)
@click.option(
    '--include-log',
    is_flag=True,
    default=False,
    help='Include logs in response (can be slow)'
)
@pass_context
def jobs_get(ctx, output, include_log):
    """List all sync jobs.

    API: GET /api/v1/get/syncjobs/all/no_log
    """
    jobs_list = ctx.client.get_sync_jobs(include_log=include_log)

    if not jobs_list:
        click.echo("No sync jobs found.")
        return

    if output == 'json':
        click.echo(json.dumps(jobs_list, indent=2, ensure_ascii=False))
    elif output == 'csv':
        click.echo('id,username,user1,host1,active')
        for job in jobs_list:
            click.echo(f"{job.get('id', '')},{job.get('username', job.get('user2', ''))},{job.get('user1', '')},{job.get('host1', '')},{job.get('active', '0')}")
    else:
        # Table format with dynamic column widths (max 24 chars)
        max_col = 24

        def trunc(s, length=max_col):
            s = str(s) if s else 'N/A'
            return s[:length-2] + '..' if len(s) > length else s

        # Prepare data
        headers = ['ID', 'Username (dest)', 'User1 (src)', 'Host1 (src)', 'Active']
        rows = []
        for job in jobs_list:
            rows.append([
                trunc(job.get('id', 'N/A'), 6),
                trunc(job.get('username', job.get('user2'))),
                trunc(job.get('user1')),
                trunc(job.get('host1')),
                '✓' if str(job.get('active', '0')) == '1' else '✗'
            ])

        # Calculate column widths based on content
        widths = [min(max_col, max(len(h), max((len(r[i]) for r in rows), default=0))) for i, h in enumerate(headers)]

        # Print header
        header_line = ' '.join(h.ljust(widths[i]) for i, h in enumerate(headers))
        click.echo(header_line)
        click.echo('-' * len(header_line))

        # Print rows
        for row in rows:
            click.echo(' '.join(str(col).ljust(widths[i]) for i, col in enumerate(row)))

        click.echo(f"\nTotal: {len(jobs_list)} sync job(s)")


@jobs.command('add')
@click.option('--file', '-f', 'csv_file', type=click.Path(exists=True), help='CSV file for batch mode (columns: user1,password1,username)')
@click.option('--host1', envvar=_envvar('MAILCOW_SRC_HOST'), required=True, help='Source IMAP host (env: MAILCOW_SRC_HOST)')
@click.option('--port1', envvar=_envvar('MAILCOW_SRC_PORT'), default='993', help='Source IMAP port (default: 993)')
@click.option('--enc1', envvar=_envvar('MAILCOW_SRC_ENC'), default='SSL', type=click.Choice(['SSL', 'TLS', 'PLAIN'], case_sensitive=False), help='Encryption type (default: SSL)')
@click.option('--user1', default=None, help='Source mailbox username/email (required without -f)')
@click.option('--password1', default=None, help='Source mailbox password (required without -f)')
@click.option('--username', default=None, help='Destination mailbox in Mailcow (required without -f)')
@click.option('--mins-interval', default='20', help='Sync interval in minutes (default: 20)')
@click.option('--exclude', default='(?i)spam|(?i)junk', help='Regex to exclude folders (default: spam/junk)')
@click.option('--delete2duplicates/--no-delete2duplicates', default=True, help='Delete duplicates on destination (default: yes)')
@click.option('--automap/--no-automap', default=True, help='Auto-map folder names (default: yes)')
@click.option('--subscribeall/--no-subscribeall', default=True, help='Subscribe to all folders (default: yes)')
@click.option('--active/--no-active', default=True, help='Activate job immediately (default: yes)')
@click.option('--dry', is_flag=True, help='Pass --dry to imapsync (simulate without transferring)')
@click.option('--custom-params', default='', help='Additional imapsync parameters')
@click.option('--preview', is_flag=True, help='Show what would be created without making API call')
@pass_context
def jobs_add(ctx, csv_file, host1, port1, enc1, user1, password1, username, mins_interval, exclude, delete2duplicates, automap, subscribeall, active, dry, custom_params, preview):
    """Add sync job(s).

    \b
    Single mode:
        jobs add --host1 imap.src.com --user1 u@src.com --password1 pass --username u@dest.com [options]

    \b
    Batch mode:
        jobs add --host1 imap.src.com -f users.csv [options]
        CSV format: user1,password1,username

    \b
    Options: --port1, --enc1, --mins-interval, --exclude, --dry, --preview, etc.

    API: POST /api/v1/add/syncjob
    """
    # Build custom_params with --dry if requested
    params = custom_params
    if dry:
        params = f"--dry {params}".strip()

    # Common options for creating a job
    def create_job(u1, p1, uname):
        return ctx.client.add_sync_job(
            username=uname,
            host1=host1,
            user1=u1,
            password1=p1,
            port1=port1,
            enc1=enc1.upper(),
            mins_interval=mins_interval,
            exclude=exclude,
            delete2duplicates='1' if delete2duplicates else '0',
            automap='1' if automap else '0',
            subscribeall='1' if subscribeall else '0',
            active='1' if active else '0',
            custom_params=params,
        )

    # Batch mode
    if csv_file:
        success_count = 0
        error_count = 0

        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)

            for row_num, row in enumerate(reader, 1):
                if not row or all(not cell.strip() for cell in row):
                    continue

                if row_num == 1 and row[0].lower() in ('user1', 'source', 'src_user', 'email'):
                    continue

                if len(row) < 3:
                    click.echo(f"Row {row_num}: Skipping - need 3 columns (user1,password1,username)", err=True)
                    error_count += 1
                    continue

                u1, p1, uname = [cell.strip() for cell in row[:3]]

                if not all([u1, p1, uname]):
                    click.echo(f"Row {row_num}: Skipping - empty required field", err=True)
                    error_count += 1
                    continue

                if preview:
                    click.echo(f"[PREVIEW] {u1} -> {uname}")
                    success_count += 1
                    continue

                try:
                    create_job(u1, p1, uname)
                    click.echo(f"Created: {u1} -> {uname}")
                    success_count += 1
                except Exception as e:
                    click.echo(f"Error for {uname}: {e}", err=True)
                    error_count += 1

        click.echo(f"\nCompleted: {success_count} created, {error_count} errors")

    # Single mode
    else:
        if not all([user1, password1, username]):
            raise click.UsageError("Single mode requires --user1, --password1, and --username (or use -f for batch)")

        if preview:
            click.echo(f"[PREVIEW] Would create sync job:")
            click.echo(f"  Source: {user1}@{host1}:{port1} ({enc1})")
            click.echo(f"  Destination: {username}")
            click.echo(f"  Options: interval={mins_interval}min, active={active}, automap={automap}")
            if params:
                click.echo(f"  Custom params: {params}")
            return

        result = create_job(user1, password1, username)

        if result:
            click.echo(f"Success: Sync job created for {username}")
            click.echo(f"  Source: {user1}@{host1}:{port1} ({enc1})")
        else:
            click.echo(f"Failed to create sync job for {username}", err=True)


@jobs.command('update')
@click.argument('job_id')
@click.option('--host1', default=None, help='Source IMAP host')
@click.option('--port1', default=None, help='Source IMAP port')
@click.option('--enc1', default=None, type=click.Choice(['SSL', 'TLS', 'PLAIN'], case_sensitive=False), help='Encryption type')
@click.option('--user1', default=None, help='Source mailbox username/email')
@click.option('--password1', default=None, help='Source mailbox password')
@click.option('--mins-interval', default=None, help='Sync interval in minutes')
@click.option('--exclude', default=None, help='Regex to exclude folders')
@click.option('--delete2duplicates/--no-delete2duplicates', default=None, help='Delete duplicates on destination')
@click.option('--automap/--no-automap', default=None, help='Auto-map folder names')
@click.option('--subscribeall/--no-subscribeall', default=None, help='Subscribe to all folders')
@click.option('--active/--no-active', default=None, help='Activate/deactivate job')
@click.option('--dry', is_flag=True, default=False, help='Pass --dry to imapsync')
@click.option('--no-dry', is_flag=True, default=False, help='Remove --dry from imapsync')
@click.option('--custom-params', default=None, help='Additional imapsync parameters')
@pass_context
def jobs_update(ctx, job_id, host1, port1, enc1, user1, password1, mins_interval, exclude, delete2duplicates, automap, subscribeall, active, dry, no_dry, custom_params):
    """Update an existing sync job.

    \b
    Usage:
        jobs update JOB_ID [options]

    \b
    Examples:
        jobs update 5 --active                    # activate job
        jobs update 5 --no-active                 # deactivate job
        jobs update 5 --mins-interval 60          # change sync interval
        jobs update 5 --password1 newpass         # update source password

    API: POST /api/v1/edit/syncjob
    """
    updates = {}

    if host1 is not None:
        updates['host1'] = host1
    if port1 is not None:
        updates['port1'] = port1
    if enc1 is not None:
        updates['enc1'] = enc1.upper()
    if user1 is not None:
        updates['user1'] = user1
    if password1 is not None:
        updates['password1'] = password1
    if mins_interval is not None:
        updates['mins_interval'] = mins_interval
    if exclude is not None:
        updates['exclude'] = exclude
    if delete2duplicates is not None:
        updates['delete2duplicates'] = '1' if delete2duplicates else '0'
    if automap is not None:
        updates['automap'] = '1' if automap else '0'
    if subscribeall is not None:
        updates['subscribeall'] = '1' if subscribeall else '0'
    if active is not None:
        updates['active'] = '1' if active else '0'

    # Handle custom_params and --dry
    if custom_params is not None:
        updates['custom_params'] = custom_params
    if dry:
        current = updates.get('custom_params', '')
        updates['custom_params'] = f"--dry {current}".strip()
    if no_dry and 'custom_params' in updates:
        updates['custom_params'] = updates['custom_params'].replace('--dry', '').strip()

    if not updates:
        raise click.UsageError("No updates specified. Use --help to see available options.")

    result = ctx.client.update_sync_job(job_id, **updates)
    success, msg = ctx.client._check_response(result)

    if success:
        click.echo(f"Success: Sync job {job_id} updated")
        for k, v in updates.items():
            if k != 'password1':
                click.echo(f"  {k}: {v}")
            else:
                click.echo(f"  {k}: ********")
    else:
        click.echo(f"Failed to update sync job {job_id}: {msg}", err=True)


@cli.group()
def mailbox():
    """Manage mailboxes.

    Create, list, and update mailboxes in Mailcow.
    """
    pass


@mailbox.command('get')
@click.option(
    '--output', '-o',
    type=click.Choice(['table', 'json', 'csv']),
    default='table',
    help='Output format (default: table)'
)
@click.option(
    '--domain', '-d',
    default=None,
    help='Filter by domain'
)
@pass_context
def mailbox_get(ctx, output, domain):
    """List all mailboxes.

    API: GET /api/v1/get/mailbox/all
    """
    mailboxes = ctx.client.get_mailboxes()

    if not mailboxes:
        click.echo("No mailboxes found.")
        return

    # Filter by domain if specified
    if domain:
        mailboxes = [m for m in mailboxes if m.get('domain') == domain]
        if not mailboxes:
            click.echo(f"No mailboxes found for domain: {domain}")
            return

    if output == 'json':
        click.echo(json.dumps(mailboxes, indent=2, ensure_ascii=False))
    elif output == 'csv':
        click.echo('username,name,domain,quota_used,quota_total,active')
        for m in mailboxes:
            name = m.get('name', '') or ''
            click.echo(f"{m.get('username', '')},\"{name}\",{m.get('domain', '')},{m.get('quota_used', 0)},{m.get('quota', 0)},{m.get('active', '0')}")
    else:
        max_col = 28

        def trunc(s, length=max_col):
            s = str(s) if s else ''
            return s[:length-2] + '..' if len(s) > length else s

        headers = ['Username', 'Name', 'Domain', 'Quota (MB)', 'Active']
        rows = []
        for m in mailboxes:
            quota_used = m.get('quota_used', 0) or 0
            quota_total = m.get('quota', 0) or 0
            quota_str = f"{quota_used // (1024*1024)}/{quota_total // (1024*1024)}" if quota_total > 0 else 'unlimited'
            rows.append([
                trunc(m.get('username', 'N/A')),
                trunc(m.get('name', '')),
                trunc(m.get('domain', '')),
                trunc(quota_str, 12),
                '✓' if str(m.get('active', '0')) == '1' else '✗'
            ])

        widths = [min(max_col, max(len(h), max((len(r[i]) for r in rows), default=0))) for i, h in enumerate(headers)]

        header_line = ' '.join(h.ljust(widths[i]) for i, h in enumerate(headers))
        click.echo(header_line)
        click.echo('-' * len(header_line))

        for row in rows:
            click.echo(' '.join(str(col).ljust(widths[i]) for i, col in enumerate(row)))

        click.echo(f"\nTotal: {len(mailboxes)} mailbox(es)")


@mailbox.command('add')
@click.option('--file', '-f', 'csv_file', type=click.Path(exists=True), help='CSV file for batch mode (columns: local_part,name or local_part,name,password)')
@click.option('--domain', '-d', envvar=_envvar('MAILCOW_DOMAIN'), required=True, help='Domain for the mailbox (env: MAILCOW_DOMAIN)')
@click.option('--local-part', default=None, help='Local part of email (required without -f)')
@click.option('--name', default='', help='Full name of user')
@click.option('--password', default=None, help='Password (required without -f, or use --gen-password)')
@click.option('--gen-password', is_flag=True, help='Generate random password')
@click.option('--quota', default='0', help='Quota in MB (0 = domain default)')
@click.option('--active/--no-active', default=True, help='Activate mailbox (default: yes)')
@click.option('--force-pw-update/--no-force-pw-update', default=False, help='Force password change on first login (default: no)')
@click.option('--tls-enforce-in/--no-tls-enforce-in', default=True, help='Require TLS for incoming (default: yes)')
@click.option('--tls-enforce-out/--no-tls-enforce-out', default=True, help='Require TLS for outgoing (default: yes)')
@click.option('--preview', is_flag=True, help='Show what would be created without making API call')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format for preview/credentials (default: table)')
@pass_context
def mailbox_add(ctx, csv_file, domain, local_part, name, password, gen_password, quota, active, force_pw_update, tls_enforce_in, tls_enforce_out, preview, output):
    """Add mailbox(es).

    \b
    Single mode:
        mailbox add -d example.com --local-part john --name "John Doe" --password secret

    \b
    Batch mode:
        mailbox add -d example.com -f users.csv --gen-password
        CSV format: local_part,name (password generated)
        CSV format: local_part,name,password (password from CSV)

    API: POST /api/v1/add/mailbox
    """
    import secrets
    import string

    def generate_password(length=16):
        """Generate a password with at least one lowercase, uppercase, digit, and special char."""
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = '!@#$%&*'
        alphabet = lowercase + uppercase + digits + special

        # Ensure at least one character from each required category
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special),
        ]
        # Fill the rest with random characters from the full alphabet
        password += [secrets.choice(alphabet) for _ in range(length - 4)]
        # Shuffle to randomize the position of required characters
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)

    def name_from_local_part(lp):
        """Generate full name from local_part: prenume.nume -> Prenume Nume"""
        # Split by common separators: . _ -
        import re
        parts = re.split(r'[._-]', lp)
        return ' '.join(part.capitalize() for part in parts if part)

    def create_mailbox(lp, nm, pw):
        return ctx.client.add_mailbox(
            local_part=lp,
            domain=domain,
            password=pw,
            name=nm,
            quota=quota,
            active='1' if active else '0',
            force_pw_update='1' if force_pw_update else '0',
            tls_enforce_in='1' if tls_enforce_in else '0',
            tls_enforce_out='1' if tls_enforce_out else '0',
        )

    def output_json(rows, headers):
        """Output rows as JSON."""
        data = [dict(zip([h.lower().replace(' ', '_') for h in headers], row)) for row in rows]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))

    def output_table(rows, headers):
        """Output rows as a formatted table."""
        max_col = 32
        def trunc(s, length=max_col):
            s = str(s) if s else ''
            return s[:length-2] + '..' if len(s) > length else s

        display_rows = [[trunc(col) for col in row] for row in rows]
        widths = [max(len(h), max((len(r[i]) for r in display_rows), default=0)) for i, h in enumerate(headers)]

        click.echo(' '.join(h.ljust(widths[i]) for i, h in enumerate(headers)))
        click.echo('-' * sum(widths) + '-' * (len(widths) - 1))
        for row in display_rows:
            click.echo(' '.join(str(col).ljust(widths[i]) for i, col in enumerate(row)))

    def output_csv(rows, headers):
        """Output rows as CSV."""
        click.echo(','.join(headers))
        for row in rows:
            click.echo(','.join(str(col) for col in row))

    # Batch mode
    if csv_file:
        success_count = 0
        error_count = 0
        created_accounts = []
        preview_accounts = []

        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)

            for row_num, row in enumerate(reader, 1):
                if not row or all(not cell.strip() for cell in row):
                    continue

                # Skip header row
                if row_num == 1 and row[0].lower() in ('local_part', 'localpart', 'email', 'username', 'user'):
                    continue

                if len(row) < 1:
                    click.echo(f"Row {row_num}: Skipping - empty row", err=True)
                    error_count += 1
                    continue

                lp = row[0].strip()
                nm = row[1].strip() if len(row) > 1 else ''
                pw = row[2].strip() if len(row) > 2 else None

                if not lp:
                    click.echo(f"Row {row_num}: Skipping - empty local_part", err=True)
                    error_count += 1
                    continue

                # Generate password if not provided and flag is set
                if not pw:
                    if gen_password:
                        pw = generate_password()
                    else:
                        click.echo(f"Row {row_num}: Skipping - no password (use --gen-password)", err=True)
                        error_count += 1
                        continue

                email = f"{lp}@{domain}"

                # Generate name from local_part if not provided
                if not nm:
                    nm = name_from_local_part(lp)

                if preview:
                    preview_accounts.append((email, pw, nm))
                    success_count += 1
                    continue

                try:
                    result = create_mailbox(lp, nm, pw)
                    success, msg = ctx.client._check_response(result)
                    if success:
                        click.echo(f"Created: {email}")
                        created_accounts.append((email, pw, nm))
                        success_count += 1
                    else:
                        click.echo(f"Error for {email}: {msg}", err=True)
                        error_count += 1
                except Exception as e:
                    click.echo(f"Error for {email}: {e}", err=True)
                    error_count += 1

        # Output preview results
        if preview and preview_accounts:
            headers = ['Email', 'Password', 'Name']
            if output == 'json':
                output_json(preview_accounts, headers)
            elif output == 'csv':
                output_csv(preview_accounts, headers)
            else:
                output_table(preview_accounts, headers)
                click.echo(f"\nTotal: {success_count} mailbox(es) to create")
            return

        click.echo(f"\nCompleted: {success_count} created, {error_count} errors")

        # Output generated passwords
        if created_accounts and gen_password:
            headers = ['Email', 'Password', 'Name']
            if output != 'json':
                click.echo("\n--- Generated credentials ---")
            if output == 'json':
                output_json(created_accounts, headers)
            elif output == 'csv':
                output_csv(created_accounts, headers)
            else:
                output_table(created_accounts, headers)

    # Single mode
    else:
        if not local_part:
            raise click.UsageError("Single mode requires --local-part (or use -f for batch)")

        if not password and not gen_password:
            raise click.UsageError("Single mode requires --password or --gen-password")

        pw = password if password else generate_password()
        email = f"{local_part}@{domain}"

        # Generate name from local_part if not provided
        full_name = name if name else name_from_local_part(local_part)

        if preview:
            click.echo(f"[PREVIEW] Would create mailbox:")
            click.echo(f"  Email: {email}")
            click.echo(f"  Name: {full_name}")
            click.echo(f"  Quota: {quota} MB")
            click.echo(f"  Active: {active}")
            return

        result = create_mailbox(local_part, full_name, pw)
        success, msg = ctx.client._check_response(result)

        if success:
            click.echo(f"Success: Mailbox created")
            click.echo(f"  Email: {email}")
            click.echo(f"  Name: {full_name}")
            if gen_password:
                click.echo(f"  Password: {pw}")
        else:
            click.echo(f"Failed to create mailbox {email}: {msg}", err=True)


@mailbox.command('update')
@click.argument('username')
@click.option('--name', default=None, help='Full name of user')
@click.option('--password', default=None, help='New password')
@click.option('--quota', default=None, help='Quota in MB (0 = domain default)')
@click.option('--active/--no-active', default=None, help='Activate/deactivate mailbox')
@click.option('--force-pw-update/--no-force-pw-update', default=None, help='Force password change on first login')
@click.option('--tls-enforce-in/--no-tls-enforce-in', default=None, help='Require TLS for incoming')
@click.option('--tls-enforce-out/--no-tls-enforce-out', default=None, help='Require TLS for outgoing')
@pass_context
def mailbox_update(ctx, username, name, password, quota, active, force_pw_update, tls_enforce_in, tls_enforce_out):
    """Update an existing mailbox.

    \b
    Usage:
        mailbox update USER@DOMAIN [options]

    \b
    Examples:
        mailbox update john@example.com --name "John Smith"
        mailbox update john@example.com --no-active
        mailbox update john@example.com --password newpass
        mailbox update john@example.com --quota 1024

    API: POST /api/v1/edit/mailbox
    """
    updates = {}

    if name is not None:
        updates['name'] = name
    if password is not None:
        updates['password'] = password
        updates['password2'] = password
    if quota is not None:
        updates['quota'] = quota
    if active is not None:
        updates['active'] = '1' if active else '0'
    if force_pw_update is not None:
        updates['force_pw_update'] = '1' if force_pw_update else '0'
    if tls_enforce_in is not None:
        updates['tls_enforce_in'] = '1' if tls_enforce_in else '0'
    if tls_enforce_out is not None:
        updates['tls_enforce_out'] = '1' if tls_enforce_out else '0'

    if not updates:
        raise click.UsageError("No updates specified. Use --help to see available options.")

    result = ctx.client.update_mailbox(username, **updates)
    success, msg = ctx.client._check_response(result)

    if success:
        click.echo(f"Success: Mailbox {username} updated")
        for k, v in updates.items():
            if k not in ('password', 'password2'):
                click.echo(f"  {k}: {v}")
            elif k == 'password':
                click.echo(f"  password: ********")
    else:
        click.echo(f"Failed to update mailbox {username}: {msg}", err=True)


@cli.group()
def alias():
    """Manage aliases.

    Create, list, and update email aliases in Mailcow.
    """
    pass


@alias.command('get')
@click.option(
    '--output', '-o',
    type=click.Choice(['table', 'json', 'csv']),
    default='table',
    help='Output format (default: table)'
)
@click.option(
    '--domain', '-d',
    default=None,
    help='Filter by domain'
)
@pass_context
def alias_get(ctx, output, domain):
    """List all aliases.

    API: GET /api/v1/get/alias/all
    """
    aliases = ctx.client.get_aliases()

    if not aliases:
        click.echo("No aliases found.")
        return

    # Filter by domain if specified
    if domain:
        aliases = [a for a in aliases if a.get('domain') == domain]
        if not aliases:
            click.echo(f"No aliases found for domain: {domain}")
            return

    if output == 'json':
        click.echo(json.dumps(aliases, indent=2, ensure_ascii=False))
    elif output == 'csv':
        click.echo('id,address,goto,active')
        for a in aliases:
            goto = a.get('goto', '')
            click.echo(f"{a.get('id', '')},{a.get('address', '')},\"{goto}\",{a.get('active', '0')}")
    else:
        max_col = 35

        def trunc(s, length=max_col):
            s = str(s) if s else ''
            return s[:length-2] + '..' if len(s) > length else s

        headers = ['ID', 'Address', 'Goto', 'Active']
        rows = []
        for a in aliases:
            rows.append([
                trunc(str(a.get('id', 'N/A')), 6),
                trunc(a.get('address', '')),
                trunc(a.get('goto', '')),
                '✓' if str(a.get('active', '0')) == '1' else '✗'
            ])

        widths = [min(max_col, max(len(h), max((len(r[i]) for r in rows), default=0))) for i, h in enumerate(headers)]

        header_line = ' '.join(h.ljust(widths[i]) for i, h in enumerate(headers))
        click.echo(header_line)
        click.echo('-' * len(header_line))

        for row in rows:
            click.echo(' '.join(str(col).ljust(widths[i]) for i, col in enumerate(row)))

        click.echo(f"\nTotal: {len(aliases)} alias(es)")


@alias.command('add')
@click.option('--file', '-f', 'csv_file', type=click.Path(exists=True), help='CSV file for batch mode (columns: address,goto)')
@click.option('--address', default=None, help='Alias email address (required without -f)')
@click.option('--goto', default=None, help='Comma-separated destination addresses (required without -f)')
@click.option('--active/--no-active', default=True, help='Activate alias (default: yes)')
@click.option('--sogo-visible/--no-sogo-visible', default=True, help='Visible in SOGo (default: yes)')
@click.option('--preview', is_flag=True, help='Show what would be created without making API call')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format for preview (default: table)')
@pass_context
def alias_add(ctx, csv_file, address, goto, active, sogo_visible, preview, output):
    """Add alias(es).

    \b
    Single mode:
        alias add --address alias@example.com --goto user@example.com

    \b
    Batch mode:
        alias add -f aliases.csv
        CSV format: address,goto

    API: POST /api/v1/add/alias
    """
    def output_json(rows, headers):
        data = [dict(zip([h.lower() for h in headers], row)) for row in rows]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))

    def output_table(rows, headers):
        max_col = 40
        def trunc(s, length=max_col):
            s = str(s) if s else ''
            return s[:length-2] + '..' if len(s) > length else s

        display_rows = [[trunc(col) for col in row] for row in rows]
        widths = [max(len(h), max((len(r[i]) for r in display_rows), default=0)) for i, h in enumerate(headers)]

        click.echo(' '.join(h.ljust(widths[i]) for i, h in enumerate(headers)))
        click.echo('-' * sum(widths) + '-' * (len(widths) - 1))
        for row in display_rows:
            click.echo(' '.join(str(col).ljust(widths[i]) for i, col in enumerate(row)))

    def output_csv(rows, headers):
        click.echo(','.join(headers))
        for row in rows:
            # Quote fields that contain commas
            click.echo(','.join(f'"{col}"' if ',' in str(col) else str(col) for col in row))

    def create_alias(addr, gt):
        return ctx.client.add_alias(
            address=addr,
            goto=gt,
            active='1' if active else '0',
            sogo_visible='1' if sogo_visible else '0',
        )

    # Batch mode
    if csv_file:
        success_count = 0
        error_count = 0
        preview_items = []
        created_items = []

        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)

            for row_num, row in enumerate(reader, 1):
                if not row or all(not cell.strip() for cell in row):
                    continue

                # Skip header row
                if row_num == 1 and row[0].lower() in ('address', 'alias', 'source', 'from'):
                    continue

                if len(row) < 2:
                    click.echo(f"Row {row_num}: Skipping - need 2 columns (address,goto)", err=True)
                    error_count += 1
                    continue

                addr = row[0].strip()
                gt = row[1].strip()

                if not addr or not gt:
                    click.echo(f"Row {row_num}: Skipping - empty address or goto", err=True)
                    error_count += 1
                    continue

                if preview:
                    preview_items.append((addr, gt))
                    success_count += 1
                    continue

                try:
                    result = create_alias(addr, gt)
                    success, msg = ctx.client._check_response(result)
                    if success:
                        click.echo(f"Created: {addr} -> {gt[:50]}{'...' if len(gt) > 50 else ''}")
                        created_items.append((addr, gt))
                        success_count += 1
                    else:
                        click.echo(f"Error for {addr}: {msg}", err=True)
                        error_count += 1
                except Exception as e:
                    click.echo(f"Error for {addr}: {e}", err=True)
                    error_count += 1

        # Output preview results
        if preview and preview_items:
            headers = ['Address', 'Goto']
            if output == 'json':
                output_json(preview_items, headers)
            elif output == 'csv':
                output_csv(preview_items, headers)
            else:
                output_table(preview_items, headers)
                click.echo(f"\nTotal: {success_count} alias(es) to create")
            return

        click.echo(f"\nCompleted: {success_count} created, {error_count} errors")

    # Single mode
    else:
        if not address or not goto:
            raise click.UsageError("Single mode requires --address and --goto (or use -f for batch)")

        if preview:
            click.echo(f"[PREVIEW] Would create alias:")
            click.echo(f"  Address: {address}")
            click.echo(f"  Goto: {goto}")
            click.echo(f"  Active: {active}")
            return

        result = create_alias(address, goto)
        success, msg = ctx.client._check_response(result)

        if success:
            click.echo(f"Success: Alias created")
            click.echo(f"  Address: {address}")
            click.echo(f"  Goto: {goto}")
        else:
            click.echo(f"Failed to create alias {address}: {msg}", err=True)


@alias.command('update')
@click.argument('alias_id')
@click.option('--address', default=None, help='New alias address')
@click.option('--goto', default=None, help='New comma-separated destination addresses')
@click.option('--active/--no-active', default=None, help='Activate/deactivate alias')
@click.option('--sogo-visible/--no-sogo-visible', default=None, help='Visible in SOGo')
@pass_context
def alias_update(ctx, alias_id, address, goto, active, sogo_visible):
    """Update an existing alias.

    \b
    Usage:
        alias update ALIAS_ID [options]

    \b
    Examples:
        alias update 5 --goto newuser@example.com
        alias update 5 --no-active
        alias update 5 --address newalias@example.com

    API: POST /api/v1/edit/alias
    """
    updates = {}

    if address is not None:
        updates['address'] = address
    if goto is not None:
        updates['goto'] = goto
    if active is not None:
        updates['active'] = '1' if active else '0'
    if sogo_visible is not None:
        updates['sogo_visible'] = '1' if sogo_visible else '0'

    if not updates:
        raise click.UsageError("No updates specified. Use --help to see available options.")

    result = ctx.client.update_alias(alias_id, **updates)
    success, msg = ctx.client._check_response(result)

    if success:
        click.echo(f"Success: Alias {alias_id} updated")
        for k, v in updates.items():
            click.echo(f"  {k}: {v}")
    else:
        click.echo(f"Failed to update alias {alias_id}: {msg}", err=True)


@cli.group()
def transport():
    """Manage transport maps.

    Transport maps define how mail for specific destinations
    should be routed (e.g., to a relay server).
    """
    pass


@transport.command('get')
@click.option(
    '--output', '-o',
    type=click.Choice(['table', 'json', 'csv']),
    default='table',
    help='Output format (default: table)'
)
@pass_context
def transport_get(ctx, output):
    """List all transport maps.

    API: GET /api/v1/get/transport/all
    """
    transports = ctx.client.get_transports()

    if not transports:
        click.echo("No transport maps found.")
        return

    if output == 'json':
        click.echo(json.dumps(transports, indent=2, ensure_ascii=False))
    elif output == 'csv':
        click.echo('id,destination,nexthop,username,active')
        for t in transports:
            click.echo(f"{t.get('id', '')},{t.get('destination', '')},{t.get('nexthop', '')},{t.get('username', '')},{t.get('active', '0')}")
    else:
        max_col = 30

        def trunc(s, length=max_col):
            s = str(s) if s else ''
            return s[:length-2] + '..' if len(s) > length else s

        headers = ['ID', 'Destination', 'Nexthop', 'Username', 'Active']
        rows = []
        for t in transports:
            rows.append([
                trunc(str(t.get('id', 'N/A')), 6),
                trunc(t.get('destination', '')),
                trunc(t.get('nexthop', '')),
                trunc(t.get('username', '') or '-'),
                '✓' if str(t.get('active', '0')) == '1' else '✗'
            ])

        widths = [min(max_col, max(len(h), max((len(r[i]) for r in rows), default=0))) for i, h in enumerate(headers)]

        header_line = ' '.join(h.ljust(widths[i]) for i, h in enumerate(headers))
        click.echo(header_line)
        click.echo('-' * len(header_line))

        for row in rows:
            click.echo(' '.join(str(col).ljust(widths[i]) for i, col in enumerate(row)))

        click.echo(f"\nTotal: {len(transports)} transport map(s)")


@transport.command('add')
@click.option('--file', '-f', 'csv_file', type=click.Path(exists=True), help='CSV file for batch mode (columns: destination,nexthop[,username,password])')
@click.option('--destination', default=None, help='Destination domain/pattern (e.g., example.com)')
@click.option('--nexthop', default=None, help='Next hop server (e.g., [smtp.relay.com]:587)')
@click.option('--username', default='', help='SMTP auth username (optional)')
@click.option('--password', default='', help='SMTP auth password (optional)')
@click.option('--active/--no-active', default=True, help='Activate transport (default: yes)')
@click.option('--preview', is_flag=True, help='Show what would be created without making API call')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', help='Output format for preview (default: table)')
@pass_context
def transport_add(ctx, csv_file, destination, nexthop, username, password, active, preview, output):
    """Add transport map(s).

    \b
    Single mode:
        transport add --destination example.com --nexthop [smtp.relay.com]:587

    \b
    Batch mode:
        transport add -f transports.csv
        CSV format: destination,nexthop[,username,password]

    API: POST /api/v1/add/transport
    """
    def output_json(rows, headers):
        data = [dict(zip([h.lower() for h in headers], row)) for row in rows]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))

    def output_table(rows, headers):
        max_col = 35
        def trunc(s, length=max_col):
            s = str(s) if s else ''
            return s[:length-2] + '..' if len(s) > length else s

        display_rows = [[trunc(col) for col in row] for row in rows]
        widths = [max(len(h), max((len(r[i]) for r in display_rows), default=0)) for i, h in enumerate(headers)]

        click.echo(' '.join(h.ljust(widths[i]) for i, h in enumerate(headers)))
        click.echo('-' * sum(widths) + '-' * (len(widths) - 1))
        for row in display_rows:
            click.echo(' '.join(str(col).ljust(widths[i]) for i, col in enumerate(row)))

    def output_csv(rows, headers):
        click.echo(','.join(headers))
        for row in rows:
            click.echo(','.join(str(col) for col in row))

    def create_transport(dest, nh, user='', passwd=''):
        return ctx.client.add_transport(
            destination=dest,
            nexthop=nh,
            username=user,
            password=passwd,
            active='1' if active else '0',
        )

    # Batch mode
    if csv_file:
        success_count = 0
        error_count = 0
        preview_items = []
        created_items = []

        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)

            for row_num, row in enumerate(reader, 1):
                if not row or all(not cell.strip() for cell in row):
                    continue

                # Skip header row
                if row_num == 1 and row[0].lower() in ('destination', 'dest', 'domain'):
                    continue

                if len(row) < 2:
                    click.echo(f"Row {row_num}: Skipping - need at least 2 columns (destination,nexthop)", err=True)
                    error_count += 1
                    continue

                dest = row[0].strip()
                nh = row[1].strip()
                user = row[2].strip() if len(row) > 2 else ''
                passwd = row[3].strip() if len(row) > 3 else ''

                if not dest or not nh:
                    click.echo(f"Row {row_num}: Skipping - empty destination or nexthop", err=True)
                    error_count += 1
                    continue

                if preview:
                    preview_items.append((dest, nh, user or '-'))
                    success_count += 1
                    continue

                try:
                    result = create_transport(dest, nh, user, passwd)
                    success, msg = ctx.client._check_response(result)
                    if success:
                        click.echo(f"Created: {dest} -> {nh}")
                        created_items.append((dest, nh, user or '-'))
                        success_count += 1
                    else:
                        click.echo(f"Error for {dest}: {msg}", err=True)
                        error_count += 1
                except Exception as e:
                    click.echo(f"Error for {dest}: {e}", err=True)
                    error_count += 1

        # Output preview results
        if preview and preview_items:
            headers = ['Destination', 'Nexthop', 'Username']
            if output == 'json':
                output_json(preview_items, headers)
            elif output == 'csv':
                output_csv(preview_items, headers)
            else:
                output_table(preview_items, headers)
                click.echo(f"\nTotal: {success_count} transport map(s) to create")
            return

        click.echo(f"\nCompleted: {success_count} created, {error_count} errors")

    # Single mode
    else:
        if not destination or not nexthop:
            raise click.UsageError("Single mode requires --destination and --nexthop (or use -f for batch)")

        if preview:
            click.echo(f"[PREVIEW] Would create transport map:")
            click.echo(f"  Destination: {destination}")
            click.echo(f"  Nexthop: {nexthop}")
            if username:
                click.echo(f"  Username: {username}")
            click.echo(f"  Active: {active}")
            return

        result = create_transport(destination, nexthop, username, password)
        success, msg = ctx.client._check_response(result)

        if success:
            click.echo(f"Success: Transport map created")
            click.echo(f"  Destination: {destination}")
            click.echo(f"  Nexthop: {nexthop}")
            if username:
                click.echo(f"  Username: {username}")
        else:
            click.echo(f"Failed to create transport map: {msg}", err=True)


@transport.command('delete')
@click.argument('transport_ids', nargs=-1, required=True)
@click.option('--force', '-y', is_flag=True, help='Skip confirmation prompt')
@pass_context
def transport_delete(ctx, transport_ids, force):
    """Delete transport map(s).

    \b
    Usage:
        transport delete ID [ID ...]

    \b
    Examples:
        transport delete 5
        transport delete 5 6 7
        transport delete 5 -y  (skip confirmation)

    API: POST /api/v1/delete/transport
    """
    if not transport_ids:
        raise click.UsageError("At least one transport ID is required")

    ids_list = list(transport_ids)

    if not force:
        click.echo(f"About to delete {len(ids_list)} transport map(s): {', '.join(ids_list)}")
        if not click.confirm("Continue?"):
            click.echo("Aborted.")
            return

    result = ctx.client.delete_transport(ids_list)
    success, msg = ctx.client._check_response(result)

    if success:
        click.echo(f"Success: Deleted {len(ids_list)} transport map(s)")
    else:
        click.echo(f"Failed to delete transport map(s): {msg}", err=True)


if __name__ == '__main__':
    # Load environment variables from a .env file in the project directory when
    # the script is executed directly. This avoids loading .env during test
    # imports which could make required env-var tests pass unexpectedly.
    #
    # Use MAILCOW_ENV_FILE to specify a different .env file:
    #   MAILCOW_ENV_FILE=.env.domeniu1 python mailcow_cli.py
    # Default is .env
    try:
        from dotenv import load_dotenv
        env_file = os.environ.get('MAILCOW_ENV_FILE', '.env')
        env_path = os.path.join(os.path.dirname(__file__), env_file)
        load_dotenv(dotenv_path=env_path, override=False)
    except Exception:
        pass

    cli()
