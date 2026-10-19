import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

import main


class CodexTranslationTests(unittest.TestCase):
    def setUp(self):
        self.run = self.enterContext(patch('main.subprocess.run'))
        self.enterContext(patch.multiple(
            main,
            CODEX_BIN='codex',
            CODEX_MODEL='gpt-6.1-sol',
            TRANSLATION_PROMPT='Translate into Traditional Chinese.',
        ))

    def successful_run(self, command, **kwargs):
        output_path = Path(command[command.index('--output-last-message') + 1])
        output_path.write_text(json.dumps({
            'translated_title': '維護公告',
            'translated_body': '- 暫停充值。\n- 維護時間：10 月 20 日。',
        }), encoding='utf-8')
        return subprocess.CompletedProcess(command, 0, 'CLI progress output', '')

    def test_translation_uses_requested_model_and_chatgpt_auth(self):
        def invoke(command, **kwargs):
            schema_path = Path(command[command.index('--output-schema') + 1])
            schema = json.loads(schema_path.read_text(encoding='utf-8'))
            self.assertFalse(schema['additionalProperties'])
            self.assertEqual(set(schema['required']), {'translated_title', 'translated_body'})
            self.assertEqual(Path(kwargs['cwd']), schema_path.parent)
            return self.successful_run(command, **kwargs)

        self.run.side_effect = invoke
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'unused-key', 'CODEX_API_KEY': 'unused-key'}):
            self.assertEqual(main.translate('Maintenance announcement'), (
                '維護公告', '- 暫停充值。\n- 維護時間：10 月 20 日。',
            ))
        self.run.assert_called_once()
        args, kwargs = self.run.call_args
        command = args[0]
        self.assertEqual(command[:4], ['codex', 'exec', '--model', 'gpt-6.1-sol'])
        self.assertIn('forced_login_method="chatgpt"', command)
        self.assertIn('model_reasoning_effort="low"', command)
        self.assertEqual(command[command.index('--sandbox') + 1], 'read-only')
        self.assertEqual(command[-1], '-')
        self.assertIn('Maintenance announcement', kwargs['input'])
        self.assertIn('Translate into Traditional Chinese.', kwargs['input'])
        self.assertNotIn('OPENAI_API_KEY', kwargs['env'])
        self.assertNotIn('CODEX_API_KEY', kwargs['env'])
        self.assertEqual(kwargs['timeout'], 120)
        self.assertFalse(Path(kwargs['cwd']).exists())

    def test_cli_failure_reports_diagnostic(self):
        self.run.return_value = subprocess.CompletedProcess([], 1, '', 'Please sign in again.')
        with self.assertRaisesRegex(RuntimeError, 'Please sign in again'):
            main.translate('announcement')
        self.run.assert_called_once()

    def test_timeout_is_propagated(self):
        error = subprocess.TimeoutExpired('codex', 120)
        self.run.side_effect = error
        with self.assertRaises(subprocess.TimeoutExpired) as raised:
            main.translate('announcement')
        self.assertIs(raised.exception, error)
        self.run.assert_called_once()

    def test_missing_executable_is_propagated(self):
        self.run.side_effect = FileNotFoundError('codex not found')
        with self.assertRaises(FileNotFoundError):
            main.translate('announcement')
        self.run.assert_called_once()

    def test_stdout_is_not_used_when_output_file_is_missing(self):
        self.run.return_value = subprocess.CompletedProcess([], 0, '{"translated_title":"title","translated_body":"body"}', '')
        with self.assertRaises(FileNotFoundError):
            main.translate('announcement')

    def test_invalid_structured_output_is_rejected(self):
        for content in (
            'not json', '{}',
            '{"translated_title":123,"translated_body":"body"}',
            '{"translated_title":"title","translated_body":"body","extra":"value"}',
        ):
            with self.subTest(content=content):
                def invoke(command, **kwargs):
                    output_path = Path(command[command.index('--output-last-message') + 1])
                    output_path.write_text(content, encoding='utf-8')
                    return subprocess.CompletedProcess(command, 0, '', '')

                self.run.side_effect = invoke
                with self.assertRaises(ValidationError):
                    main.translate('announcement')

    def test_missing_prompt_does_not_start_codex(self):
        with patch.object(main, 'TRANSLATION_PROMPT', ''):
            with self.assertRaisesRegex(ValueError, 'TRANSLATION_PROMPT'):
                main.translate('announcement')
        self.run.assert_not_called()

    def test_announcement_is_sent_once_after_translation(self):
        self.run.side_effect = self.successful_run
        announcement = {
            'title': 'Maintenance', 'body': 'Deposits paused.',
            'catalogName': 'Maintenance Updates', 'publishDate': 1792454400000,
        }
        message = json.dumps({'type': 'DATA', 'topic': main.TOPIC, 'data': json.dumps(announcement)})
        with patch.object(main.SyncWebhook, 'from_url') as webhook, patch('builtins.print'):
            main.on_message(None, message)
        webhook.return_value.send.assert_called_once()
        embed = webhook.return_value.send.call_args.kwargs['embed']
        self.assertEqual(embed.title, '維護公告')
        self.assertIn('gpt-6.1-sol', embed.footer.text)

    def test_discord_sync_webhook_can_be_created(self):
        webhook_id = 123456789012345678
        url = f'https://discord.com/api/webhooks/{webhook_id}/' + 'a' * 68
        webhook = main.SyncWebhook.from_url(url)
        self.assertEqual(webhook.id, webhook_id)


if __name__ == '__main__':
    unittest.main()
