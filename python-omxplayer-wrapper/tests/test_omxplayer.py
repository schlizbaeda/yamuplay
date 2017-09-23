import unittest
import os
import sys
import signal
import dbus

from parameterized import parameterized
from mock import patch, Mock, call, mock_open

from omxplayer.dbus_connection import DBusConnectionError
from omxplayer.player import OMXPlayer

if sys.version_info[0] == 2:
    builtin = '__builtin__'
else:
    builtin = 'builtins'



MOCK_OPEN = mock_open()


@patch('{}.open'.format(builtin), MOCK_OPEN)
@patch('os.killpg')
@patch('os.path.isfile')
@patch('time.sleep')
@patch('subprocess.Popen')
class OMXPlayerTests(unittest.TestCase):
    TEST_FILE_NAME = "./test.mp4"
    TEST_URL = "rtmp://192.168.0.1/live/mystream"

    def test_opens_file_in_omxplayer(self, popen, *args):
        self.patch_and_run_omxplayer()
        devnull = MOCK_OPEN()
        popen.assert_called_once_with(
            ['omxplayer', './test.mp4'],
            preexec_fn=os.setsid,
            stdin=devnull,
            stdout=devnull)

    @patch('time.sleep')
    def test_tries_to_open_dbus_again_if_it_cant_connect(self, *args):
        # TODO: Shouldn't this be DBusConnectionError not SystemError
        with self.assertRaises(SystemError):
            dbus_connection = Mock(side_effect=DBusConnectionError)
            self.patch_and_run_omxplayer(Connection=dbus_connection)
            self.assertEqual(50, self.player.tries)

    @parameterized.expand([
        ['can_quit', 'CanQuit', [], []],
        ['can_set_fullscreen', 'CanSetFullscreen', [], []],
        ['identity', 'Identity', [], []]
    ])
    def test_root_interface_commands(self, popen, sleep, isfile, killpg, command_name,
                                     interface_command_name, *args):
        self.patch_and_run_omxplayer()
        self.patch_interface_and_run_command('_get_root_interface',
                                             command_name,
                                             interface_command_name, *args)

    @parameterized.expand([
        ['pause', 'Pause', [], []],
        ['stop', 'Stop', [], []],
        ['seek', 'Seek', [100], [100]],
        ['set_position', 'SetPosition', [1], [dbus.ObjectPath("/not/used"),
                                              dbus.Int64(1000000)]],
        ['list_subtitles', 'ListSubtitles', [], []],
        ['action', 'Action', ['p'], ['p']]
    ])
    def test_player_interface_commands(self, popen, sleep, isfile, killpg, command_name,
                                       interface_command_name, *args):
        self.patch_and_run_omxplayer()
        self.patch_interface_and_run_command('_get_player_interface',
                                             command_name,
                                             interface_command_name, *args)

    @parameterized.expand([
        ['can_play', 'CanPlay', [], []],
        ['can_seek', 'CanSeek', [], []],
        ['can_control', 'CanControl', [], []],
        ['playback_status', 'PlaybackStatus', [], []],
        ['volume', 'Volume', [], []],
        ['mute', 'Mute', [], []],
        ['unmute', 'Unmute', [], []],
        ['position', 'Position', [], []],
        ['duration', 'Duration', [], []],
        ['minimum_rate', 'MinimumRate', [], []],
        ['maximum_rate', 'MaximumRate', [], []],
    ])
    def test_properties_interface_commands(self, popen, sleep, isfile, killpg, command_name,
                                           interface_command_name, *args):
        self.patch_and_run_omxplayer()
        self.patch_interface_and_run_command('_get_properties_interface',
                                             command_name,
                                             interface_command_name, *args)

    def test_quitting(self, popen, sleep, isfile, killpg, *args):
        omxplayer_process = Mock()
        popen.return_value = omxplayer_process
        self.patch_and_run_omxplayer()
        with patch('os.getpgid', Mock(return_value=omxplayer_process.pid)):
            self.player.quit()
            killpg.assert_called_once_with(omxplayer_process.pid, signal.SIGTERM)

    def test_quitting_waits_for_omxplayer_to_die(self, popen, sleep, isfile, killpg, *args):
        omxplayer_process = Mock()
        popen.return_value = omxplayer_process
        self.patch_and_run_omxplayer()
        with patch('os.getpgid'):
            self.player.quit()
            omxplayer_process.wait.assert_has_calls([call()])

    def test_check_process_still_exists_before_dbus_call(self, *args):
        self.patch_and_run_omxplayer()
        self.player._process = process = Mock(return_value=None)
        process.poll.return_value = None

        self.player.can_quit()

        process.poll.assert_called_once_with()

    def test_checks_media_file_exists_before_launching_player(self, *args):
        with patch('os.path') as ospath:
            self.patch_and_run_omxplayer()
            ospath.isfile.assert_called_once_with(self.TEST_FILE_NAME)

    def test_player_doesnt_check_source_path_exists_for_a_url(self, *args):
        with patch('os.path') as ospath:
            self.patch_and_run_omxplayer_url()
            ospath.isfile.assert_not_called()

    def test_stop_event(self, *args):
        self.patch_and_run_omxplayer(active=True)
        callback = Mock()
        self.player.stopEvent += callback

        self.player.stop()

        callback.assert_called_once_with(self.player)

    def test_play_event(self, *args):
        self.patch_and_run_omxplayer(active=True)
        callback = Mock()
        self.player.playEvent += callback

        with patch.object(self.player, 'is_playing', return_value=False):
            self.player.play()

            callback.assert_called_once_with(self.player)

    def test_pause_event(self, *args):
        self.patch_and_run_omxplayer(active=True)
        callback = Mock()
        self.player.pauseEvent += callback

        with patch.object(self.player, 'is_playing', return_value=True):
            self.player.pause()

            callback.assert_called_once_with(self.player)

    def test_play_event_by_play_pause(self, *args):
        self.patch_and_run_omxplayer(active=True)
        callback = Mock()
        self.player.playEvent += callback

        with patch.object(self.player, 'is_playing', return_value=False):
            self.player.pause()

            # play
            self.player.play_pause()

            callback.assert_called_once_with(self.player)

    def test_pause_event_by_play_pause(self, *args):
        self.patch_and_run_omxplayer(active=True)
        callback = Mock()
        self.player.pauseEvent += callback

        with patch.object(self.player, 'is_playing', return_value=True):
            self.player.play()

            # pause
            self.player.play_pause()

            callback.assert_called_once_with(self.player)

    def test_seek_event(self, *args):
        self.patch_and_run_omxplayer(active=True)
        callback = Mock()
        self.player.seekEvent += callback

        self.player.seek(3.4)

        callback.assert_called_once_with(self.player, 3.4)

    def test_position_event(self, *args):
        self.patch_and_run_omxplayer(active=True)
        callback = Mock()
        self.player.positionEvent += callback

        self.player.set_position(5.01)

        callback.assert_called_once_with(self.player, 5.01)

    def patch_interface_and_run_command(self, interface_name,
                                        command_name, interface_command_name,
                                        command_args,
                                        expected_args):
        self.player._process.poll = Mock(return_value=None)
        with patch.object(self.player, interface_name) as interface:
            self.run_command(command_name, *command_args)
            # generates a call of the form `call().CanQuit`
            expected_call = getattr(call(), interface_command_name)(*expected_args)
            interface.assert_has_calls([expected_call])

    def run_command(self, command_name, *args):
        command = getattr(self.player, command_name)
        command(*args)

    # Must have the prefix 'patch' for the decorators to take effect
    def patch_and_run_omxplayer(self, Connection=Mock(), active=False):
        bus_address_finder = Mock()
        bus_address_finder.get_address.return_val = "example_bus_address"
        self.player = OMXPlayer(self.TEST_FILE_NAME,
                                bus_address_finder=bus_address_finder,
                                Connection=Connection)
        if active:
            self.player._process.poll = Mock(return_value=None)

    def patch_and_run_omxplayer_url(self, Connection=Mock(), active=False):
        bus_address_finder = Mock()
        bus_address_finder.get_address.return_val = "example_bus_address"
        self.player = OMXPlayer(self.TEST_URL,
                                bus_address_finder=bus_address_finder,
                                Connection=Connection)
        if active:
            self.player._process.poll = Mock(return_value=None)

    def test_load(self, popen, sleep, isfile, killpg, *args):
        omxplayer_process = Mock()
        popen.return_value = omxplayer_process
        with patch('os.getpgid', Mock(return_value=omxplayer_process.pid)):
            self.patch_and_run_omxplayer(active=True)
            # initial load
            self.assertEqual(self.player.get_filename(), './test.mp4')
            killpg.assert_not_called()
            popen.assert_called_once_with(['omxplayer', './test.mp4'],
                                        preexec_fn=os.setsid,
                                        stdin=MOCK_OPEN(),
                                        stdout=MOCK_OPEN())
            # load new video in same OMXPlayer instance
            self.player.load('./test2.mp4')
            # verify new video is registered in OMXPlayer
            self.assertEqual(self.player.get_filename(), './test2.mp4')
            # verify omxplayer process for previous video was killed
            killpg.assert_called_once_with(omxplayer_process.pid, signal.SIGTERM)
            # verify a new process was started for the second time
            self.assertEqual(popen.call_count, 2)


    def test_init_without_pause(self, popen, sleep, isfile, killpg, *args):
        with patch.object(OMXPlayer, 'pause', return_value=None) as mock_method:
            self.patch_and_run_omxplayer()
            self.assertEqual(mock_method.call_count, 0)

    def test_init_pause(self, popen, sleep, isfile, killpg, *args):
        with patch.object(OMXPlayer, 'pause', return_value=None) as mock_method:
            # self.patch_and_run_omxplayer(pause=False)
            bus_address_finder = Mock()
            bus_address_finder.get_address.return_val = "example_bus_address"
            self.player = OMXPlayer(self.TEST_FILE_NAME,
                                bus_address_finder=bus_address_finder,
                                Connection=Mock(),
                                pause=True)

            self.assertEqual(mock_method.call_count, 1)

    def test_load_and_pause(self, popen, sleep, isfile, killpg, *args):
        with patch.object(OMXPlayer, 'pause', return_value=None) as mock_method:
            self.patch_and_run_omxplayer()
            self.player.load('./test2.mp4', pause=True)
            self.assertEqual(mock_method.call_count, 1)

    def test_load_without_pause(self, popen, sleep, isfile, killpg, *args):
        with patch.object(OMXPlayer, 'pause', return_value=None) as mock_method:
            self.patch_and_run_omxplayer()
            self.player.load('./test2.mp4')
            self.assertEqual(mock_method.call_count, 0)
