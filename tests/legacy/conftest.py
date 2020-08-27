#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2020-08-04
# @Filename: conftest.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)


import asyncio
import os

import pytest

from sdsstools import get_logger

from clu.legacy import LegacyActor
from clu.legacy.tron import TronConnection
from clu.protocol import TCPStreamServer, open_connection


get_keys_reply = (
    'client.client 1 keys_alerts i version="2.0.1"; '
    'activeAlerts=camCheck.SP2R1HeaterVRead; '
    'alert=camCheck.SP2R1HeaterVRead,warn'
    ',"at 2020-08-04 22:30:18 UT found \'Reported by camCheck\'"'
    ',enabled,noack,-1; disabledAlertRules; downInstruments; '
    'instrumentNames=apogee,boss,boss.SP2,boss.SP2.R,boss.SP2.B,'
    'boss.SP1,boss.SP1.R,boss.SP1.B,mcp; text="Now you know all I know"\n'
)


@pytest.fixture
async def tron_server(unused_tcp_port_factory):

    received = []

    async def echo(transport, data):

        received.append(data)

        if 'getFor=alerts' in data.decode():
            transport.write(get_keys_reply.encode())
        else:
            transport.write(data)

    server = TCPStreamServer('localhost',
                             unused_tcp_port_factory(),
                             data_received_callback=echo)

    server.received = received

    await server.start()

    yield server

    server.stop()


@pytest.fixture
async def tron_client(tron_server):

    # Used to trigger echo messages from the tron server.

    log = get_logger('tron-test')

    model_names = ['alerts'] if 'ACTORKEYS_DIR' in os.environ else None

    _tron = TronConnection('localhost', tron_server.port,
                           model_names=model_names, log=log)

    await _tron.start()
    await asyncio.sleep(0.01)

    yield _tron

    _tron.stop()
    del log


@pytest.fixture
async def actor(tron_server, unused_tcp_port_factory, tmp_path):

    model_names = ['alerts'] if 'ACTORKEYS_DIR' in os.environ else None

    _actor = LegacyActor('test_actor', 'localhost',
                         unused_tcp_port_factory(),
                         tron_host=tron_server.host,
                         tron_port=tron_server.port,
                         model_names=model_names,
                         version='0.1.0', log_dir=tmp_path)

    await _actor.start()
    await asyncio.sleep(0.01)

    yield _actor

    await _actor.stop()


@pytest.fixture
async def actor_client(actor):

    _client = await open_connection(actor.host, actor.port)
    _client.actor = actor

    # Drain the buffer
    await _client.reader.read(100)

    yield _client

    _client.close()
