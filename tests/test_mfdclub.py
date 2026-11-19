import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mfdclub import cli, sober, steam, vdf
from mfdclub.config import Config

SAMPLE = '''"users"
{
\t"76561198000000001"
\t{
\t\t"AccountName"\t\t"club_main"
\t\t"PersonaName"\t\t"Club"
\t\t"RememberPassword"\t\t"1"
\t\t"MostRecent"\t\t"0"
\t\t"Timestamp"\t\t"100"
\t}
\t"76561198000000002"
\t{
\t\t"AccountName"\t\t"personal"
\t\t"PersonaName"\t\t"Me"
\t\t"RememberPassword"\t\t"1"
\t\t"MostRecent"\t\t"1"
\t\t"Timestamp"\t\t"200"
\t}
}
'''


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        env = {
            "MFDCLUB_CONFIG_DIR": str(self.tmp / "cfg"),
            "MFDCLUB_DATA_DIR": str(self.tmp / "data"),
            "MFDCLUB_STEAM_DIR": str(self.tmp / "steam"),
            "MFDCLUB_SOBER_DIR": str(self.tmp / "var" / "sober"),
            "MFDCLUB_SYSTEM_CONFIG": str(self.tmp / "etc" / "config.json"),
        }
        p = mock.patch.dict(os.environ, env)
        p.start()
        self.addCleanup(p.stop)
        (self.tmp / "steam" / "config").mkdir(parents=True)
        self.vdf_path = self.tmp / "steam" / "config" / "loginusers.vdf"
        self.vdf_path.write_text(SAMPLE)
        r = mock.patch("mfdclub.sober.running", return_value=False)
        r.start()
        self.addCleanup(r.stop)


class VdfTests(unittest.TestCase):
    def test_roundtrip(self):
        d = vdf.loads(SAMPLE)
        self.assertEqual(vdf.loads(vdf.dumps(d)), d)
        self.assertEqual(d["users"]["76561198000000002"]["AccountName"], "personal")


class SteamTests(Base):
    def test_list_and_club_flag(self):
        cfg = Config(steam_club=["CLUB_MAIN"])
        accs = steam.list_accounts(cfg)
        self.assertEqual([a.account_name for a in accs], ["personal", "club_main"])
        self.assertEqual([a.club for a in accs], [False, True])

    def test_logout_dry_run_changes_nothing(self):
        steam.logout_non_club(Config(steam_club=["club_main"]), dry_run=True)
        self.assertEqual(self.vdf_path.read_text(), SAMPLE)

    def test_logout_removes_non_club_and_backs_up(self):
        removed = steam.logout_non_club(Config(steam_club=["76561198000000001"]), dry_run=False)
        self.assertEqual([a.account_name for a in removed], ["personal"])
        users = vdf.loads(self.vdf_path.read_text())["users"]
        self.assertEqual(list(users), ["76561198000000001"])
        self.assertEqual(users["76561198000000001"]["MostRecent"], "1")
        self.assertTrue(list(self.vdf_path.parent.glob("loginusers.vdf.bak-*")))


class SoberTests(Base):
    def test_profile_switch_keeps_both_sessions(self):
        live = sober.live_dir()
        live.mkdir(parents=True)
        (live / "session").write_text("club")
        sober.init("club")
        sober.new("me")
        sober.use("me")
        self.assertEqual(list(live.iterdir()), [])
        (live / "session").write_text("me")
        sober.use("club")
        self.assertEqual((live / "session").read_text(), "club")
        sober.use("me")
        self.assertEqual((live / "session").read_text(), "me")

    def test_use_refused_while_running(self):
        sober.live_dir().mkdir(parents=True)
        sober.init("club")
        sober.new("me")
        with mock.patch("mfdclub.sober.running", return_value=True):
            with self.assertRaises(sober.SoberError):
                sober.use("me")

    def test_reset_non_club_spares_club(self):
        live = sober.live_dir()
        live.mkdir(parents=True)
        (live / "session").write_text("club")
        sober.init("club")
        sober.new("me")
        (sober.profiles_dir() / "me" / "session").write_text("me")
        cfg = Config(sober_club_profile="club")
        self.assertEqual(sober.reset_non_club(cfg, dry_run=True), ["me"])
        self.assertTrue((sober.profiles_dir() / "me" / "session").exists())
        sober.reset_non_club(cfg, dry_run=False)
        self.assertFalse((sober.profiles_dir() / "me" / "session").exists())
        self.assertTrue((live / "session").exists())

    def test_bad_names(self):
        for bad in ("", "../x", ".hid", "a/b"):
            with self.assertRaises(sober.SoberError):
                sober.new(bad)


class SystemConfigTests(Base):
    def test_system_config_wins(self):
        Config(steam_club=["user_level"]).save()
        sysp = self.tmp / "etc" / "config.json"
        sysp.parent.mkdir()
        sysp.write_text('{"steam_club": ["club_main"], "sober_club_profile": "club"}')
        cfg = Config.load()
        self.assertEqual(cfg.steam_club, ["club_main"])
        self.assertEqual(cfg.sober_club_profile, "club")

    def test_readonly_system_config_blocks_user_edit(self):
        sysp = self.tmp / "etc" / "config.json"
        sysp.parent.mkdir()
        sysp.write_text("{}")
        sysp.chmod(0o444)
        self.assertEqual(cli.main(["club", "add-steam", "x"]), 1)


class OtherUserTests(Base):
    def test_list_other_user_home(self):
        import io
        from contextlib import redirect_stdout
        home = self.tmp / "home" / "elev"
        (home / ".local/share/Steam/config").mkdir(parents=True)
        (home / ".local/share/Steam/config/loginusers.vdf").write_text(SAMPLE)
        env = {k: v for k, v in os.environ.items() if k != "MFDCLUB_STEAM_DIR"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("mfdclub.paths.home_of", return_value=home):
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(cli.main(["list", "--user", "elev"]), 0)
        out = buf.getvalue()
        self.assertIn("=== elev ===", out)
        self.assertIn("personal", out)
        from mfdclub import paths
        self.assertIsNone(paths._override)

    def test_unknown_user(self):
        self.assertEqual(cli.main(["list", "--user", "no_such_user_xyz"]), 1)


class CliTests(Base):
    def test_logout_refuses_without_club_config(self):
        self.assertEqual(cli.main(["logout", "--yes"]), 2)
        self.assertEqual(self.vdf_path.read_text(), SAMPLE)

    def test_logout_flow(self):
        cli.main(["club", "add-steam", "club_main"])
        with mock.patch("mfdclub.steam.steam_running", return_value=False):
            cli.main(["logout", "--yes"])
        self.assertEqual(list(vdf.loads(self.vdf_path.read_text())["users"]), ["76561198000000001"])


if __name__ == "__main__":
    unittest.main()
