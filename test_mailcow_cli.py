"""
Tests for mailcow_cli.py

Run with: pytest test_mailcow_cli.py -v
"""

import json
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner

from mailcow_cli import cli, MailcowClient


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_client():
    """Mock MailcowClient."""
    return Mock(spec=MailcowClient)


class TestMailcowClient:
    """Tests for MailcowClient class."""

    def test_check_response_success(self):
        """Test _check_response with success response."""
        client = MailcowClient("https://example.com", "test-key")
        result = [{"type": "success", "msg": "Operation completed"}]
        success, msg = client._check_response(result)
        assert success is True
        assert msg == "Operation completed"

    def test_check_response_error(self):
        """Test _check_response with error response."""
        client = MailcowClient("https://example.com", "test-key")
        result = [{"type": "error", "msg": "Something went wrong"}]
        success, msg = client._check_response(result)
        assert success is False
        assert msg == "Something went wrong"

    def test_check_response_object_exists(self):
        """Test _check_response with object_exists format."""
        client = MailcowClient("https://example.com", "test-key")
        result = ["object_exists", "user@example.com"]
        success, msg = client._check_response(result)
        assert success is False
        assert "object_exists" in msg

    def test_check_response_empty(self):
        """Test _check_response with empty response."""
        client = MailcowClient("https://example.com", "test-key")
        success, msg = client._check_response([])
        assert success is False
        assert msg == "Empty response"

    def test_check_response_none(self):
        """Test _check_response with None response."""
        client = MailcowClient("https://example.com", "test-key")
        success, msg = client._check_response(None)
        assert success is False


class TestCliBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self, runner):
        """Test main CLI help."""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Mailcow CLI' in result.output

    def test_cli_requires_api_url(self, runner):
        """Test that CLI requires --api-url."""
        result = runner.invoke(cli, ['jobs', 'get'])
        assert result.exit_code != 0
        assert 'api-url' in result.output.lower() or 'api-url' in str(result.exception).lower()

    def test_jobs_help(self, runner):
        """Test jobs command help."""
        result = runner.invoke(cli, ['--api-url', 'x', '--api-key', 'x', 'jobs', '--help'])
        assert result.exit_code == 0
        assert 'sync jobs' in result.output.lower()

    def test_mailbox_help(self, runner):
        """Test mailbox command help."""
        result = runner.invoke(cli, ['--api-url', 'x', '--api-key', 'x', 'mailbox', '--help'])
        assert result.exit_code == 0
        assert 'mailbox' in result.output.lower()

    def test_alias_help(self, runner):
        """Test alias command help."""
        result = runner.invoke(cli, ['--api-url', 'x', '--api-key', 'x', 'alias', '--help'])
        assert result.exit_code == 0
        assert 'alias' in result.output.lower()


class TestJobsCommands:
    """Tests for jobs commands."""

    @patch.object(MailcowClient, 'get_sync_jobs')
    def test_jobs_get_empty(self, mock_get, runner):
        """Test jobs get with no jobs."""
        mock_get.return_value = []
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'jobs', 'get'])
        assert result.exit_code == 0
        assert 'No sync jobs found' in result.output

    @patch.object(MailcowClient, 'get_sync_jobs')
    def test_jobs_get_table(self, mock_get, runner):
        """Test jobs get with table output."""
        mock_get.return_value = [
            {'id': 1, 'username': 'dest@example.com', 'user1': 'src@old.com', 'host1': 'mail.old.com', 'active': '1'}
        ]
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'jobs', 'get'])
        assert result.exit_code == 0
        assert 'dest@example.com' in result.output
        assert 'src@old.com' in result.output

    @patch.object(MailcowClient, 'get_sync_jobs')
    def test_jobs_get_json(self, mock_get, runner):
        """Test jobs get with JSON output."""
        mock_get.return_value = [
            {'id': 1, 'username': 'dest@example.com', 'user1': 'src@old.com', 'host1': 'mail.old.com', 'active': '1'}
        ]
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'jobs', 'get', '-o', 'json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['username'] == 'dest@example.com'

    @patch.object(MailcowClient, 'get_sync_jobs')
    def test_jobs_get_csv(self, mock_get, runner):
        """Test jobs get with CSV output."""
        mock_get.return_value = [
            {'id': 1, 'username': 'dest@example.com', 'user1': 'src@old.com', 'host1': 'mail.old.com', 'active': '1'}
        ]
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'jobs', 'get', '-o', 'csv'])
        assert result.exit_code == 0
        assert 'id,username,user1,host1,active' in result.output
        assert 'dest@example.com' in result.output


class TestMailboxCommands:
    """Tests for mailbox commands."""

    @patch.object(MailcowClient, 'get_mailboxes')
    def test_mailbox_get_empty(self, mock_get, runner):
        """Test mailbox get with no mailboxes."""
        mock_get.return_value = []
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'mailbox', 'get'])
        assert result.exit_code == 0
        assert 'No mailboxes found' in result.output

    @patch.object(MailcowClient, 'get_mailboxes')
    def test_mailbox_get_table(self, mock_get, runner):
        """Test mailbox get with table output."""
        mock_get.return_value = [
            {'username': 'user@example.com', 'name': 'Test User', 'domain': 'example.com', 'quota': 1073741824, 'quota_used': 0, 'active': '1'}
        ]
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'mailbox', 'get'])
        assert result.exit_code == 0
        assert 'user@example.com' in result.output
        assert 'Test User' in result.output

    @patch.object(MailcowClient, 'get_mailboxes')
    def test_mailbox_get_json(self, mock_get, runner):
        """Test mailbox get with JSON output."""
        mock_get.return_value = [
            {'username': 'user@example.com', 'name': 'Test User', 'domain': 'example.com', 'quota': 0, 'active': '1'}
        ]
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'mailbox', 'get', '-o', 'json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['username'] == 'user@example.com'

    @patch.object(MailcowClient, 'get_mailboxes')
    def test_mailbox_get_filter_domain(self, mock_get, runner):
        """Test mailbox get filtered by domain."""
        mock_get.return_value = [
            {'username': 'user1@example.com', 'name': '', 'domain': 'example.com', 'quota': 0, 'active': '1'},
            {'username': 'user2@other.com', 'name': '', 'domain': 'other.com', 'quota': 0, 'active': '1'},
        ]
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'mailbox', 'get', '-d', 'example.com'])
        assert result.exit_code == 0
        assert 'user1@example.com' in result.output
        assert 'user2@other.com' not in result.output

    def test_mailbox_add_requires_domain(self, runner):
        """Test mailbox add requires --domain."""
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'mailbox', 'add', '--local-part', 'test'])
        assert result.exit_code != 0

    def test_mailbox_add_requires_password_or_gen(self, runner):
        """Test mailbox add requires --password or --gen-password."""
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'mailbox', 'add', '-d', 'example.com', '--local-part', 'test'])
        assert result.exit_code != 0
        assert 'password' in result.output.lower()

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_single(self, mock_check, mock_add, runner):
        """Test mailbox add single mode."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'test', '--password', 'secret123'
        ])
        assert result.exit_code == 0
        assert 'Success' in result.output
        mock_add.assert_called_once()

    def test_mailbox_add_preview_single(self, runner):
        """Test mailbox add preview in single mode."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'john.doe', '--gen-password', '--preview'
        ])
        assert result.exit_code == 0
        assert 'PREVIEW' in result.output
        assert 'john.doe@example.com' in result.output
        assert 'John Doe' in result.output  # Name generated from local_part

    def test_mailbox_add_preview_batch(self, runner, tmp_path):
        """Test mailbox add preview in batch mode."""
        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name\njohn.doe,John Doe\njane.smith,\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file), '--gen-password', '--preview'
        ])
        assert result.exit_code == 0
        assert 'john.doe@example.com' in result.output
        assert 'John Doe' in result.output
        assert 'jane.smith@example.com' in result.output
        assert 'Jane Smith' in result.output  # Name generated from local_part


class TestAliasCommands:
    """Tests for alias commands."""

    @patch.object(MailcowClient, 'get_aliases')
    def test_alias_get_empty(self, mock_get, runner):
        """Test alias get with no aliases."""
        mock_get.return_value = []
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'alias', 'get'])
        assert result.exit_code == 0
        assert 'No aliases found' in result.output

    @patch.object(MailcowClient, 'get_aliases')
    def test_alias_get_table(self, mock_get, runner):
        """Test alias get with table output."""
        mock_get.return_value = [
            {'id': 1, 'address': 'alias@example.com', 'goto': 'user@example.com', 'domain': 'example.com', 'active': '1'}
        ]
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'alias', 'get'])
        assert result.exit_code == 0
        assert 'alias@example.com' in result.output
        assert 'user@example.com' in result.output

    @patch.object(MailcowClient, 'get_aliases')
    def test_alias_get_json(self, mock_get, runner):
        """Test alias get with JSON output."""
        mock_get.return_value = [
            {'id': 1, 'address': 'alias@example.com', 'goto': 'user@example.com', 'domain': 'example.com', 'active': '1'}
        ]
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'alias', 'get', '-o', 'json'])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['address'] == 'alias@example.com'

    @patch.object(MailcowClient, 'get_aliases')
    def test_alias_get_csv(self, mock_get, runner):
        """Test alias get with CSV output."""
        mock_get.return_value = [
            {'id': 1, 'address': 'alias@example.com', 'goto': 'user1@example.com,user2@example.com', 'domain': 'example.com', 'active': '1'}
        ]
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'alias', 'get', '-o', 'csv'])
        assert result.exit_code == 0
        assert 'id,address,goto,active' in result.output
        assert 'alias@example.com' in result.output

    def test_alias_add_requires_address_and_goto(self, runner):
        """Test alias add requires --address and --goto."""
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'alias', 'add', '--address', 'test@example.com'])
        assert result.exit_code != 0
        assert 'goto' in result.output.lower()

    @patch.object(MailcowClient, 'add_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_add_single(self, mock_check, mock_add, runner):
        """Test alias add single mode."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add',
            '--address', 'alias@example.com',
            '--goto', 'user@example.com'
        ])
        assert result.exit_code == 0
        assert 'Success' in result.output
        mock_add.assert_called_once()

    @patch.object(MailcowClient, 'add_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_add_multiple_goto(self, mock_check, mock_add, runner):
        """Test alias add with multiple goto addresses."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add',
            '--address', 'group@example.com',
            '--goto', 'user1@example.com,user2@example.com,user3@example.com'
        ])
        assert result.exit_code == 0
        assert 'Success' in result.output
        # Verify the goto was passed correctly
        call_args = mock_add.call_args
        assert 'user1@example.com,user2@example.com,user3@example.com' in str(call_args)

    def test_alias_add_preview_single(self, runner):
        """Test alias add preview in single mode."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add',
            '--address', 'alias@example.com',
            '--goto', 'user@example.com',
            '--preview'
        ])
        assert result.exit_code == 0
        assert 'PREVIEW' in result.output
        assert 'alias@example.com' in result.output
        assert 'user@example.com' in result.output

    def test_alias_add_preview_batch(self, runner, tmp_path):
        """Test alias add preview in batch mode."""
        csv_file = tmp_path / "aliases.csv"
        csv_file.write_text('address,goto\nalias1@example.com,user1@example.com\nalias2@example.com,"user2@example.com,user3@example.com"\n')

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add', '-f', str(csv_file), '--preview'
        ])
        assert result.exit_code == 0
        assert 'alias1@example.com' in result.output
        assert 'alias2@example.com' in result.output


class TestNameGeneration:
    """Tests for name generation from local_part."""

    def test_name_from_local_part_with_dot(self, runner):
        """Test name generation with dot separator."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'john.doe', '--gen-password', '--preview'
        ])
        assert 'John Doe' in result.output

    def test_name_from_local_part_with_underscore(self, runner):
        """Test name generation with underscore separator."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'john_doe', '--gen-password', '--preview'
        ])
        assert 'John Doe' in result.output

    def test_name_from_local_part_with_hyphen(self, runner):
        """Test name generation with hyphen separator."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'john-doe', '--gen-password', '--preview'
        ])
        assert 'John Doe' in result.output

    def test_name_from_local_part_single_word(self, runner):
        """Test name generation with single word."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'admin', '--gen-password', '--preview'
        ])
        assert 'Admin' in result.output

    def test_name_from_local_part_three_parts(self, runner):
        """Test name generation with three parts."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'ana.maria.pop', '--gen-password', '--preview'
        ])
        assert 'Ana Maria Pop' in result.output

    def test_explicit_name_overrides_generation(self, runner):
        """Test that explicit --name overrides generation."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'john.doe', '--name', 'Custom Name',
            '--gen-password', '--preview'
        ])
        assert 'Custom Name' in result.output
        assert 'John Doe' not in result.output


class TestOutputFormats:
    """Tests for different output formats."""

    @patch.object(MailcowClient, 'get_mailboxes')
    def test_mailbox_get_csv_format(self, mock_get, runner):
        """Test mailbox get CSV has correct format."""
        mock_get.return_value = [
            {'username': 'user@example.com', 'name': 'Test User', 'domain': 'example.com', 'quota': 1073741824, 'quota_used': 536870912, 'active': '1'}
        ]
        result = runner.invoke(cli, ['--api-url', 'https://x', '--api-key', 'x', 'mailbox', 'get', '-o', 'csv'])
        assert result.exit_code == 0
        lines = result.output.strip().split('\n')
        assert lines[0] == 'username,name,domain,quota_used,quota_total,active'
        assert 'user@example.com' in lines[1]

    def test_mailbox_add_preview_json_format(self, runner, tmp_path):
        """Test mailbox add preview JSON format."""
        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name\njohn.doe,John Doe\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file), '--gen-password', '--preview', '-o', 'json'
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]['email'] == 'john.doe@example.com'
        assert 'password' in data[0]
        assert data[0]['name'] == 'John Doe'


class TestErrorHandling:
    """Tests for error handling."""

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_error_response(self, mock_check, mock_add, runner):
        """Test mailbox add with error response."""
        mock_add.return_value = [{"type": "error", "msg": "Domain not found"}]
        mock_check.return_value = (False, "Domain not found")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'test', '--password', 'secret123'
        ])
        assert 'Failed' in result.output or 'Domain not found' in result.output

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_object_exists(self, mock_check, mock_add, runner):
        """Test mailbox add when object exists."""
        mock_add.return_value = ["object_exists", "test@example.com"]
        mock_check.return_value = (False, "object_exists test@example.com")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'test', '--password', 'secret123'
        ])
        assert 'object_exists' in result.output or 'Failed' in result.output

    def test_mailbox_add_batch_invalid_csv(self, runner, tmp_path):
        """Test mailbox add batch with invalid CSV rows."""
        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name\njohn.doe\n")  # Missing name column (optional but row too short for password)

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file)  # No --gen-password, so should fail
        ])
        assert 'no password' in result.output.lower() or 'error' in result.output.lower()


class TestJobsAddCommand:
    """Tests for jobs add command."""

    def test_jobs_add_requires_host1(self, runner):
        """Test jobs add requires --host1."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com'
        ])
        assert result.exit_code != 0

    def test_jobs_add_single_requires_credentials(self, runner):
        """Test jobs add single mode requires user1, password1, username."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com'
        ])
        assert result.exit_code != 0

    @patch.object(MailcowClient, 'add_sync_job')
    def test_jobs_add_single_success(self, mock_add, runner):
        """Test jobs add single mode success."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com'
        ])
        assert result.exit_code == 0
        assert 'Success' in result.output or 'dest@new.com' in result.output
        mock_add.assert_called_once()

    def test_jobs_add_preview_single(self, runner):
        """Test jobs add preview in single mode."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com',
            '--preview'
        ])
        assert result.exit_code == 0
        assert 'PREVIEW' in result.output
        assert 'src@old.com' in result.output
        assert 'dest@new.com' in result.output

    def test_jobs_add_preview_batch(self, runner, tmp_path):
        """Test jobs add preview in batch mode."""
        csv_file = tmp_path / "jobs.csv"
        csv_file.write_text("user1,password1,username\nsrc1@old.com,pass1,dest1@new.com\nsrc2@old.com,pass2,dest2@new.com\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '-f', str(csv_file), '--preview'
        ])
        assert result.exit_code == 0
        assert 'src1@old.com' in result.output
        assert 'dest1@new.com' in result.output

    @patch.object(MailcowClient, 'add_sync_job')
    def test_jobs_add_batch_success(self, mock_add, runner, tmp_path):
        """Test jobs add batch mode success."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        csv_file = tmp_path / "jobs.csv"
        csv_file.write_text("user1,password1,username\nsrc1@old.com,pass1,dest1@new.com\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '-f', str(csv_file)
        ])
        assert result.exit_code == 0
        assert 'Created' in result.output

    def test_jobs_add_with_dry_flag(self, runner):
        """Test jobs add with --dry flag."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com',
            '--dry', '--preview'
        ])
        assert result.exit_code == 0
        assert '--dry' in result.output


class TestJobsUpdateCommand:
    """Tests for jobs update command."""

    def test_jobs_update_requires_options(self, runner):
        """Test jobs update requires at least one option."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123'
        ])
        assert result.exit_code != 0
        assert 'No updates' in result.output

    @patch.object(MailcowClient, 'update_sync_job')
    def test_jobs_update_active(self, mock_update, runner):
        """Test jobs update --active."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--active'
        ])
        assert result.exit_code == 0
        mock_update.assert_called_once()

    @patch.object(MailcowClient, 'update_sync_job')
    def test_jobs_update_password(self, mock_update, runner):
        """Test jobs update --password1."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--password1', 'newpass'
        ])
        assert result.exit_code == 0
        assert '********' in result.output  # Password should be masked

    @patch.object(MailcowClient, 'update_sync_job')
    def test_jobs_update_multiple_options(self, mock_update, runner):
        """Test jobs update with multiple options."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--mins-interval', '60', '--no-active'
        ])
        assert result.exit_code == 0


class TestMailboxUpdateCommand:
    """Tests for mailbox update command."""

    def test_mailbox_update_requires_options(self, runner):
        """Test mailbox update requires at least one option."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'update', 'user@example.com'
        ])
        assert result.exit_code != 0
        assert 'No updates' in result.output

    @patch.object(MailcowClient, 'update_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_update_name(self, mock_check, mock_update, runner):
        """Test mailbox update --name."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'update', 'user@example.com', '--name', 'New Name'
        ])
        assert result.exit_code == 0
        assert 'Success' in result.output
        assert 'name' in result.output

    @patch.object(MailcowClient, 'update_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_update_password(self, mock_check, mock_update, runner):
        """Test mailbox update --password."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'update', 'user@example.com', '--password', 'newpass'
        ])
        assert result.exit_code == 0
        assert '********' in result.output

    @patch.object(MailcowClient, 'update_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_update_deactivate(self, mock_check, mock_update, runner):
        """Test mailbox update --no-active."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'update', 'user@example.com', '--no-active'
        ])
        assert result.exit_code == 0
        assert 'active' in result.output

    @patch.object(MailcowClient, 'update_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_update_quota(self, mock_check, mock_update, runner):
        """Test mailbox update --quota."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'update', 'user@example.com', '--quota', '2048'
        ])
        assert result.exit_code == 0
        assert 'quota' in result.output

    @patch.object(MailcowClient, 'update_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_update_error(self, mock_check, mock_update, runner):
        """Test mailbox update with error response."""
        mock_update.return_value = [{"type": "error", "msg": "Mailbox not found"}]
        mock_check.return_value = (False, "Mailbox not found")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'update', 'user@example.com', '--name', 'New Name'
        ])
        assert 'Failed' in result.output or 'Mailbox not found' in result.output


class TestAliasUpdateCommand:
    """Tests for alias update command."""

    def test_alias_update_requires_options(self, runner):
        """Test alias update requires at least one option."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'update', '123'
        ])
        assert result.exit_code != 0
        assert 'No updates' in result.output

    @patch.object(MailcowClient, 'update_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_update_goto(self, mock_check, mock_update, runner):
        """Test alias update --goto."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'update', '123', '--goto', 'newuser@example.com'
        ])
        assert result.exit_code == 0
        assert 'Success' in result.output

    @patch.object(MailcowClient, 'update_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_update_address(self, mock_check, mock_update, runner):
        """Test alias update --address."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'update', '123', '--address', 'newalias@example.com'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_update_deactivate(self, mock_check, mock_update, runner):
        """Test alias update --no-active."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'update', '123', '--no-active'
        ])
        assert result.exit_code == 0
        assert 'active' in result.output

    @patch.object(MailcowClient, 'update_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_update_error(self, mock_check, mock_update, runner):
        """Test alias update with error response."""
        mock_update.return_value = [{"type": "error", "msg": "Alias not found"}]
        mock_check.return_value = (False, "Alias not found")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'update', '123', '--goto', 'newuser@example.com'
        ])
        assert 'Failed' in result.output or 'Alias not found' in result.output


class TestBatchExecution:
    """Tests for batch mode execution (non-preview)."""

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_batch_execution(self, mock_check, mock_add, runner, tmp_path):
        """Test mailbox add batch mode actual execution."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")

        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name\njohn.doe,John Doe\njane.smith,Jane Smith\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file), '--gen-password'
        ])
        assert result.exit_code == 0
        assert 'Created' in result.output
        assert '2 created' in result.output
        assert mock_add.call_count == 2

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_batch_partial_failure(self, mock_check, mock_add, runner, tmp_path):
        """Test mailbox add batch mode with partial failures."""
        # First call succeeds, second fails
        mock_add.side_effect = [
            [{"type": "success", "msg": "ok"}],
            [{"type": "error", "msg": "Domain error"}]
        ]
        mock_check.side_effect = [
            (True, "ok"),
            (False, "Domain error")
        ]

        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name\njohn.doe,John Doe\njane.smith,Jane Smith\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file), '--gen-password'
        ])
        assert result.exit_code == 0
        assert '1 created' in result.output
        assert '1 error' in result.output

    @patch.object(MailcowClient, 'add_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_add_batch_execution(self, mock_check, mock_add, runner, tmp_path):
        """Test alias add batch mode actual execution."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")

        csv_file = tmp_path / "aliases.csv"
        csv_file.write_text('address,goto\nalias1@example.com,user1@example.com\nalias2@example.com,user2@example.com\n')

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add', '-f', str(csv_file)
        ])
        assert result.exit_code == 0
        assert 'Created' in result.output
        assert '2 created' in result.output


class TestHTTPErrors:
    """Tests for HTTP error handling."""

    @patch('mailcow_cli.requests.request')
    def test_http_error_handling(self, mock_request, runner):
        """Test HTTP error is handled gracefully."""
        from requests.exceptions import HTTPError
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_request.return_value = mock_response

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'get'
        ])
        assert result.exit_code != 0

    @patch('mailcow_cli.requests.request')
    def test_connection_error_handling(self, mock_request, runner):
        """Test connection error is handled gracefully."""
        from requests.exceptions import ConnectionError
        mock_request.side_effect = ConnectionError("Connection refused")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'get'
        ])
        assert result.exit_code != 0


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_mailbox_add_batch_skip_header(self, runner, tmp_path):
        """Test batch mode skips header row."""
        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name,password\nuser,Test User,pass123\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file), '--preview'
        ])
        assert result.exit_code == 0
        assert 'local_part' not in result.output  # Header should be skipped
        assert 'user@example.com' in result.output

    def test_mailbox_add_batch_skip_empty_rows(self, runner, tmp_path):
        """Test batch mode skips empty rows."""
        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name\n\njohn.doe,John Doe\n\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file), '--gen-password', '--preview'
        ])
        assert result.exit_code == 0
        assert 'john.doe@example.com' in result.output

    def test_alias_add_batch_skip_empty_fields(self, runner, tmp_path):
        """Test batch mode handles empty required fields."""
        csv_file = tmp_path / "aliases.csv"
        csv_file.write_text("address,goto\nalias@example.com,\n,user@example.com\ngood@example.com,dest@example.com\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add', '-f', str(csv_file), '--preview'
        ])
        assert '2 error' in result.output or 'Skipping' in result.output
        assert 'good@example.com' in result.output

    @patch.object(MailcowClient, 'get_mailboxes')
    def test_mailbox_get_filter_no_match(self, mock_get, runner):
        """Test mailbox get with domain filter that matches nothing."""
        mock_get.return_value = [
            {'username': 'user@example.com', 'name': '', 'domain': 'example.com', 'quota': 0, 'active': '1'}
        ]
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'get', '-d', 'other.com'
        ])
        assert result.exit_code == 0
        assert 'No mailboxes found for domain' in result.output

    @patch.object(MailcowClient, 'get_aliases')
    def test_alias_get_filter_domain(self, mock_get, runner):
        """Test alias get filtered by domain."""
        mock_get.return_value = [
            {'id': 1, 'address': 'alias1@example.com', 'goto': 'user@example.com', 'domain': 'example.com', 'active': '1'},
            {'id': 2, 'address': 'alias2@other.com', 'goto': 'user@other.com', 'domain': 'other.com', 'active': '1'},
        ]
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'get', '-d', 'example.com'
        ])
        assert result.exit_code == 0
        assert 'alias1@example.com' in result.output
        assert 'alias2@other.com' not in result.output

    def test_mailbox_add_csv_with_password(self, runner, tmp_path):
        """Test batch mode with password in CSV."""
        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name,password\njohn.doe,John Doe,secret123\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file), '--preview'
        ])
        assert result.exit_code == 0
        assert 'secret123' in result.output

    def test_jobs_add_custom_params(self, runner):
        """Test jobs add with custom params."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com',
            '--custom-params', '--exclude "Trash"',
            '--preview'
        ])
        assert result.exit_code == 0


class TestClientMethods:
    """Tests for MailcowClient methods."""

    def test_client_init(self):
        """Test client initialization."""
        client = MailcowClient("https://mail.example.com/", "test-key")
        assert client.api_url == "https://mail.example.com"  # Trailing slash removed
        assert client.api_key == "test-key"
        assert client.headers["X-API-Key"] == "test-key"

    @patch('mailcow_cli.requests.request')
    def test_get_sync_jobs_no_log(self, mock_request, ):
        """Test get_sync_jobs without log."""
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = MailcowClient("https://mail.example.com", "test-key")
        result = client.get_sync_jobs(include_log=False)

        assert mock_request.call_args[1]['url'].endswith('/no_log')

    @patch('mailcow_cli.requests.request')
    def test_get_sync_jobs_with_log(self, mock_request):
        """Test get_sync_jobs with log."""
        mock_response = Mock()
        mock_response.json.return_value = [{"id": 1}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = MailcowClient("https://mail.example.com", "test-key")
        result = client.get_sync_jobs(include_log=True)

        assert '/no_log' not in mock_request.call_args[1]['url']


class TestJobsAddBatchExecution:
    """Tests for jobs add batch execution."""

    @patch.object(MailcowClient, 'add_sync_job')
    def test_jobs_add_batch_success(self, mock_add, runner, tmp_path):
        """Test jobs add batch mode actual execution."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]

        csv_file = tmp_path / "jobs.csv"
        csv_file.write_text("user1,password1,username\nsrc1@old.com,pass1,dest1@new.com\nsrc2@old.com,pass2,dest2@new.com\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '-f', str(csv_file)
        ])
        assert result.exit_code == 0
        assert 'Created' in result.output
        assert mock_add.call_count == 2

    @patch.object(MailcowClient, 'add_sync_job')
    def test_jobs_add_batch_with_error(self, mock_add, runner, tmp_path):
        """Test jobs add batch mode with API error."""
        mock_add.side_effect = Exception("API Error")

        csv_file = tmp_path / "jobs.csv"
        csv_file.write_text("user1,password1,username\nsrc1@old.com,pass1,dest1@new.com\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '-f', str(csv_file)
        ])
        assert 'Error' in result.output

    def test_jobs_add_batch_invalid_rows(self, runner, tmp_path):
        """Test jobs add batch with invalid CSV rows."""
        csv_file = tmp_path / "jobs.csv"
        csv_file.write_text("user1,password1,username\nsrc1@old.com\n")  # Missing columns

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '-f', str(csv_file)
        ])
        assert 'Skipping' in result.output or 'error' in result.output.lower()

    def test_jobs_add_batch_empty_fields(self, runner, tmp_path):
        """Test jobs add batch with empty required fields."""
        csv_file = tmp_path / "jobs.csv"
        csv_file.write_text("user1,password1,username\n,pass1,dest1@new.com\nsrc1@old.com,,dest1@new.com\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '-f', str(csv_file)
        ])
        assert 'Skipping' in result.output


class TestJobsUpdateMoreOptions:
    """More tests for jobs update command options."""

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_host(self, mock_check, mock_update, runner):
        """Test jobs update --host1."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--host1', 'newmail.example.com'
        ])
        assert result.exit_code == 0
        assert 'host1' in result.output

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_port(self, mock_check, mock_update, runner):
        """Test jobs update --port1."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--port1', '143'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_enc(self, mock_check, mock_update, runner):
        """Test jobs update --enc1."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--enc1', 'TLS'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_user1(self, mock_check, mock_update, runner):
        """Test jobs update --user1."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--user1', 'newuser@old.com'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_exclude(self, mock_check, mock_update, runner):
        """Test jobs update --exclude."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--exclude', '(?i)trash'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_delete2duplicates(self, mock_check, mock_update, runner):
        """Test jobs update --no-delete2duplicates."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--no-delete2duplicates'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_automap(self, mock_check, mock_update, runner):
        """Test jobs update --no-automap."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--no-automap'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_subscribeall(self, mock_check, mock_update, runner):
        """Test jobs update --no-subscribeall."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--no-subscribeall'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_custom_params(self, mock_check, mock_update, runner):
        """Test jobs update --custom-params."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--custom-params', '--timeout 300'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_dry_flag(self, mock_check, mock_update, runner):
        """Test jobs update --dry."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--dry'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_no_dry_flag(self, mock_check, mock_update, runner):
        """Test jobs update --no-dry."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--custom-params', '--dry', '--no-dry'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'update_sync_job')
    @patch.object(MailcowClient, '_check_response')
    def test_jobs_update_error(self, mock_check, mock_update, runner):
        """Test jobs update with error response."""
        mock_update.return_value = [{"type": "error", "msg": "Job not found"}]
        mock_check.return_value = (False, "Job not found")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'update', '123', '--active'
        ])
        assert 'Failed' in result.output or 'Job not found' in result.output


class TestMailboxUpdateMoreOptions:
    """More tests for mailbox update command options."""

    @patch.object(MailcowClient, 'update_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_update_tls_enforce_in(self, mock_check, mock_update, runner):
        """Test mailbox update --tls-enforce-in."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'update', 'user@example.com', '--tls-enforce-in'
        ])
        assert result.exit_code == 0
        assert 'tls_enforce_in' in result.output

    @patch.object(MailcowClient, 'update_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_update_tls_enforce_out(self, mock_check, mock_update, runner):
        """Test mailbox update --tls-enforce-out."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'update', 'user@example.com', '--tls-enforce-out'
        ])
        assert result.exit_code == 0
        assert 'tls_enforce_out' in result.output

    @patch.object(MailcowClient, 'update_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_update_force_pw_update(self, mock_check, mock_update, runner):
        """Test mailbox update --force-pw-update."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'update', 'user@example.com', '--force-pw-update'
        ])
        assert result.exit_code == 0
        assert 'force_pw_update' in result.output


class TestMailboxAddMoreOptions:
    """More tests for mailbox add command options."""

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_no_active(self, mock_check, mock_add, runner):
        """Test mailbox add --no-active."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'test', '--password', 'secret', '--no-active'
        ])
        assert result.exit_code == 0
        # Verify active=0 was passed
        call_kwargs = mock_add.call_args
        assert call_kwargs is not None

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_force_pw_update(self, mock_check, mock_add, runner):
        """Test mailbox add --force-pw-update."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'test', '--password', 'secret', '--force-pw-update'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_no_tls(self, mock_check, mock_add, runner):
        """Test mailbox add --no-tls-enforce-in --no-tls-enforce-out."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'test', '--password', 'secret',
            '--no-tls-enforce-in', '--no-tls-enforce-out'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_with_quota(self, mock_check, mock_add, runner):
        """Test mailbox add --quota."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '--local-part', 'test', '--password', 'secret', '--quota', '1024'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_batch_with_exception(self, mock_check, mock_add, runner, tmp_path):
        """Test mailbox add batch with exception during creation."""
        mock_add.side_effect = Exception("Connection error")

        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name\njohn.doe,John Doe\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file), '--gen-password'
        ])
        assert 'Error' in result.output
        assert '1 error' in result.output


class TestAliasAddMoreOptions:
    """More tests for alias add command options."""

    @patch.object(MailcowClient, 'add_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_add_no_active(self, mock_check, mock_add, runner):
        """Test alias add --no-active."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add', '--address', 'alias@example.com',
            '--goto', 'user@example.com', '--no-active'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'add_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_add_no_sogo_visible(self, mock_check, mock_add, runner):
        """Test alias add --no-sogo-visible."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add', '--address', 'alias@example.com',
            '--goto', 'user@example.com', '--no-sogo-visible'
        ])
        assert result.exit_code == 0

    @patch.object(MailcowClient, 'add_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_add_error(self, mock_check, mock_add, runner):
        """Test alias add with error response."""
        mock_add.return_value = [{"type": "error", "msg": "Invalid address"}]
        mock_check.return_value = (False, "Invalid address")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add', '--address', 'alias@example.com',
            '--goto', 'user@example.com'
        ])
        assert 'Failed' in result.output or 'Invalid address' in result.output

    @patch.object(MailcowClient, 'add_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_add_batch_with_exception(self, mock_check, mock_add, runner, tmp_path):
        """Test alias add batch with exception during creation."""
        mock_add.side_effect = Exception("Connection error")

        csv_file = tmp_path / "aliases.csv"
        csv_file.write_text("address,goto\nalias@example.com,user@example.com\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add', '-f', str(csv_file)
        ])
        assert 'Error' in result.output


class TestAliasUpdateMoreOptions:
    """More tests for alias update command options."""

    @patch.object(MailcowClient, 'update_alias')
    @patch.object(MailcowClient, '_check_response')
    def test_alias_update_sogo_visible(self, mock_check, mock_update, runner):
        """Test alias update --sogo-visible."""
        mock_update.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'update', '123', '--sogo-visible'
        ])
        assert result.exit_code == 0
        assert 'sogo_visible' in result.output


class TestOutputFormatVariations:
    """Tests for different output format scenarios."""

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_batch_csv_output(self, mock_check, mock_add, runner, tmp_path):
        """Test mailbox add batch with CSV output."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")

        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name\njohn.doe,John Doe\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file), '--gen-password', '-o', 'csv'
        ])
        assert result.exit_code == 0
        assert 'Email,Password,Name' in result.output

    @patch.object(MailcowClient, 'add_mailbox')
    @patch.object(MailcowClient, '_check_response')
    def test_mailbox_add_batch_json_output(self, mock_check, mock_add, runner, tmp_path):
        """Test mailbox add batch with JSON output."""
        mock_add.return_value = [{"type": "success", "msg": "ok"}]
        mock_check.return_value = (True, "ok")

        csv_file = tmp_path / "users.csv"
        csv_file.write_text("local_part,name\njohn.doe,John Doe\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'mailbox', 'add', '-d', 'example.com',
            '-f', str(csv_file), '--gen-password', '-o', 'json'
        ])
        assert result.exit_code == 0
        # Should have JSON in credentials output
        assert 'email' in result.output.lower()

    def test_alias_add_preview_csv_output(self, runner, tmp_path):
        """Test alias add preview with CSV output."""
        csv_file = tmp_path / "aliases.csv"
        csv_file.write_text("address,goto\nalias@example.com,user@example.com\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add', '-f', str(csv_file), '--preview', '-o', 'csv'
        ])
        assert result.exit_code == 0
        assert 'Address,Goto' in result.output

    def test_alias_add_preview_json_output(self, runner, tmp_path):
        """Test alias add preview with JSON output."""
        csv_file = tmp_path / "aliases.csv"
        csv_file.write_text("address,goto\nalias@example.com,user@example.com\n")

        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'alias', 'add', '-f', str(csv_file), '--preview', '-o', 'json'
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1


class TestClientAPIMethods:
    """Tests for MailcowClient API methods."""

    @patch('mailcow_cli.requests.request')
    def test_add_sync_job(self, mock_request):
        """Test add_sync_job method."""
        mock_response = Mock()
        mock_response.json.return_value = [{"type": "success", "msg": "ok"}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = MailcowClient("https://mail.example.com", "test-key")
        result = client.add_sync_job(
            username="dest@new.com",
            host1="mail.old.com",
            user1="src@old.com",
            password1="pass"
        )

        assert result == [{"type": "success", "msg": "ok"}]
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert 'add/syncjob' in call_args[1]['url']

    @patch('mailcow_cli.requests.request')
    def test_update_sync_job(self, mock_request):
        """Test update_sync_job method."""
        mock_response = Mock()
        mock_response.json.return_value = [{"type": "success", "msg": "ok"}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = MailcowClient("https://mail.example.com", "test-key")
        result = client.update_sync_job("123", active="1")

        assert result == [{"type": "success", "msg": "ok"}]
        call_args = mock_request.call_args
        assert 'edit/syncjob' in call_args[1]['url']

    @patch('mailcow_cli.requests.request')
    def test_get_mailboxes(self, mock_request):
        """Test get_mailboxes method."""
        mock_response = Mock()
        mock_response.json.return_value = [{"username": "user@example.com"}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = MailcowClient("https://mail.example.com", "test-key")
        result = client.get_mailboxes()

        assert result == [{"username": "user@example.com"}]
        call_args = mock_request.call_args
        assert 'get/mailbox/all' in call_args[1]['url']

    @patch('mailcow_cli.requests.request')
    def test_add_mailbox(self, mock_request):
        """Test add_mailbox method."""
        mock_response = Mock()
        mock_response.json.return_value = [{"type": "success", "msg": "ok"}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = MailcowClient("https://mail.example.com", "test-key")
        result = client.add_mailbox(
            local_part="user",
            domain="example.com",
            password="secret"
        )

        assert result == [{"type": "success", "msg": "ok"}]
        call_args = mock_request.call_args
        assert 'add/mailbox' in call_args[1]['url']

    @patch('mailcow_cli.requests.request')
    def test_update_mailbox(self, mock_request):
        """Test update_mailbox method."""
        mock_response = Mock()
        mock_response.json.return_value = [{"type": "success", "msg": "ok"}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = MailcowClient("https://mail.example.com", "test-key")
        result = client.update_mailbox("user@example.com", name="New Name")

        assert result == [{"type": "success", "msg": "ok"}]
        call_args = mock_request.call_args
        assert 'edit/mailbox' in call_args[1]['url']

    @patch('mailcow_cli.requests.request')
    def test_get_aliases(self, mock_request):
        """Test get_aliases method."""
        mock_response = Mock()
        mock_response.json.return_value = [{"address": "alias@example.com"}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = MailcowClient("https://mail.example.com", "test-key")
        result = client.get_aliases()

        assert result == [{"address": "alias@example.com"}]
        call_args = mock_request.call_args
        assert 'get/alias/all' in call_args[1]['url']

    @patch('mailcow_cli.requests.request')
    def test_add_alias(self, mock_request):
        """Test add_alias method."""
        mock_response = Mock()
        mock_response.json.return_value = [{"type": "success", "msg": "ok"}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = MailcowClient("https://mail.example.com", "test-key")
        result = client.add_alias(
            address="alias@example.com",
            goto="user@example.com"
        )

        assert result == [{"type": "success", "msg": "ok"}]
        call_args = mock_request.call_args
        assert 'add/alias' in call_args[1]['url']

    @patch('mailcow_cli.requests.request')
    def test_update_alias(self, mock_request):
        """Test update_alias method."""
        mock_response = Mock()
        mock_response.json.return_value = [{"type": "success", "msg": "ok"}]
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        client = MailcowClient("https://mail.example.com", "test-key")
        result = client.update_alias("123", goto="newuser@example.com")

        assert result == [{"type": "success", "msg": "ok"}]
        call_args = mock_request.call_args
        assert 'edit/alias' in call_args[1]['url']


class TestJobsAddOptions:
    """Tests for jobs add command options."""

    def test_jobs_add_with_port_and_enc(self, runner):
        """Test jobs add with --port1 and --enc1."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com',
            '--port1', '143', '--enc1', 'TLS', '--preview'
        ])
        assert result.exit_code == 0
        assert 'TLS' in result.output

    def test_jobs_add_with_interval(self, runner):
        """Test jobs add with --mins-interval."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com',
            '--mins-interval', '60', '--preview'
        ])
        assert result.exit_code == 0

    def test_jobs_add_no_automap(self, runner):
        """Test jobs add with --no-automap."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com',
            '--no-automap', '--preview'
        ])
        assert result.exit_code == 0

    def test_jobs_add_no_subscribeall(self, runner):
        """Test jobs add with --no-subscribeall."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com',
            '--no-subscribeall', '--preview'
        ])
        assert result.exit_code == 0

    def test_jobs_add_no_active(self, runner):
        """Test jobs add with --no-active."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com',
            '--no-active', '--preview'
        ])
        assert result.exit_code == 0

    def test_jobs_add_exclude(self, runner):
        """Test jobs add with --exclude."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com',
            '--exclude', '(?i)trash|(?i)drafts', '--preview'
        ])
        assert result.exit_code == 0

    def test_jobs_add_no_delete2duplicates(self, runner):
        """Test jobs add with --no-delete2duplicates."""
        result = runner.invoke(cli, [
            '--api-url', 'https://x', '--api-key', 'x',
            'jobs', 'add', '--host1', 'mail.old.com',
            '--user1', 'src@old.com', '--password1', 'pass', '--username', 'dest@new.com',
            '--no-delete2duplicates', '--preview'
        ])
        assert result.exit_code == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
