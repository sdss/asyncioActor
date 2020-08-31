#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2019-05-20
# @Filename: __main__.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import asyncio
import os

import click
import prompt_toolkit
import pygments
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from pygments.lexers import JsonLexer

import clu


loop = asyncio.get_event_loop()
prompt_toolkit.eventloop.use_asyncio_event_loop()


style = prompt_toolkit.styles.style_from_pygments_cls(
    pygments.styles.get_style_by_name('solarized-dark'))


color_codes = {'i': 'lightblue',
               'd': 'gray',
               'w': 'yellow',
               'f': 'red',
               ':': 'green'}


class ShellClient(clu.AMQPClient):
    """A shell client."""

    async def handle_reply(self, message):
        """Prints the formatted reply."""

        message = await super().handle_reply(message)

        if message is None:
            return

        message_info = message.info()
        headers = message_info['headers']

        message_code = headers.get('message_code', b'').decode()
        sender = headers.get('sender', b'').decode()

        message_code_formatted = prompt_toolkit.formatted_text.HTML(
            f'<style font-weight="bold" '
            f'fg="{color_codes[message_code]}">{message_code}</style>')

        body = message.body.decode()

        body_tokens = list(pygments.lex(body, lexer=JsonLexer()))

        if sender:
            print(f'{sender} ', end='')

        if message_code:
            print(message_code_formatted, end='')
            print(' ', end='')

        if body:
            print(PygmentsTokens(body_tokens), end='', style=style)


async def shell_client_prompt(user=None, host=None, port=None):

    client = await ShellClient('shell_client',
                               user=user, host=host,
                               log=False).run()

    history = FileHistory(os.path.expanduser('~/.clu_history'))

    session = prompt_toolkit.PromptSession('', history=history)

    while True:
        try:
            text = await session.prompt(async_=True)
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        else:
            text = text.strip()
            if text.startswith('quit'):
                break
            elif text == '':
                continue
            else:
                chunks = text.split()
                if len(chunks) < 2:
                    print(f'Invalid command {text!r}')
                    continue

                actor = chunks[0]
                command_string = ' '.join(chunks[1:])

                await client.send_command(actor, command_string)


@click.command(name='clu')
@click.option('--user', '-U', type=str, show_default=True, default='guest',
              help='the AMQP username.')
@click.option('--host', '-H', type=str, show_default=True, default='localhost',
              help='the host running the AMQP server.')
@click.option('--port', '-P', type=int, show_default=True, default=5672,
              help='the port on which the server is running')
def clu_cli(user=None, host=None, port=None):
    """Runs the AMQP command line interpreter."""

    with patch_stdout():

        shell_task = loop.create_task(shell_client_prompt(user=user,
                                                          host=host,
                                                          port=port))
        loop.run_until_complete(shell_task)


def main():
    clu_cli(obj={})


if __name__ == '__main__':
    main()