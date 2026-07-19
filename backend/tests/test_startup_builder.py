from pathlib import Path

import pytest

from backend.services.startup_builder import RuntimeStartupBuilder, StartupBuilder


def test_startup_builder_empty():
    builder = StartupBuilder()
    assert builder.build() == []


def test_startup_builder_add():
    builder = StartupBuilder()
    result = builder.add("--foo", "--bar=1").build()
    assert result == ["--foo", "--bar=1"]


def test_startup_builder_extension():
    builder = StartupBuilder()
    builder.extend(lambda b: b.add("--ext"))
    assert builder.build() == ["--ext"]


class TestRuntimeStartupBuilder:
    def test_mandatory_args(self, tmp_path):
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
        )
        cmd = builder.build()
        assert cmd[0] == str(tmp_path / "factorio")
        assert cmd[1] == "--start-server=save.zip"
        assert "--rcon-port=27015" in cmd
        assert "--rcon-password=secret" in cmd

    def test_rcon_excluded_without_password(self, tmp_path):
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        cmd = builder.build()
        assert not any(part.startswith("--rcon-port") for part in cmd)
        assert not any(part.startswith("--rcon-password") for part in cmd)

    def test_server_settings_included_when_exists(self, tmp_path):
        settings = tmp_path / "server-settings.json"
        settings.write_text("{}", encoding="utf-8")
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        builder.with_server_settings(settings)
        cmd = builder.build()
        assert f"--server-settings={settings}" in cmd

    def test_server_settings_excluded_when_missing(self, tmp_path):
        settings = tmp_path / "server-settings.json"
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        builder.with_server_settings(settings)
        cmd = builder.build()
        assert not any(part.startswith("--server-settings") for part in cmd)

    def test_adminlist_included_when_exists(self, tmp_path):
        adminlist = tmp_path / "server-adminlist.json"
        adminlist.write_text("[]", encoding="utf-8")
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        builder.with_access_lists(adminlist=adminlist)
        cmd = builder.build()
        assert f"--server-adminlist={adminlist}" in cmd

    def test_adminlist_excluded_when_missing(self, tmp_path):
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        builder.with_access_lists(adminlist=tmp_path / "missing.json")
        cmd = builder.build()
        assert not any(part.startswith("--server-adminlist") for part in cmd)

    def test_banlist_included_when_exists(self, tmp_path):
        banlist = tmp_path / "server-banlist.json"
        banlist.write_text("[]", encoding="utf-8")
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        builder.with_access_lists(banlist=banlist)
        cmd = builder.build()
        assert f"--server-banlist={banlist}" in cmd

    def test_banlist_excluded_when_missing(self, tmp_path):
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        builder.with_access_lists(banlist=tmp_path / "missing.json")
        cmd = builder.build()
        assert not any(part.startswith("--server-banlist") for part in cmd)

    def test_whitelist_enabled_includes_flags(self, tmp_path):
        whitelist = tmp_path / "server-whitelist.json"
        whitelist.write_text("[]", encoding="utf-8")
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        builder.with_access_lists(whitelist=whitelist)
        cmd = builder.build()
        assert f"--server-whitelist={whitelist}" in cmd
        assert "--use-server-whitelist" in cmd

    def test_whitelist_disabled_excludes_flags(self, tmp_path):
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        builder.with_access_lists(whitelist=tmp_path / "missing.json")
        cmd = builder.build()
        assert not any(part.startswith("--server-whitelist") for part in cmd)
        assert not any(part.startswith("--use-server-whitelist") for part in cmd)

    def test_all_conditional_flags_together(self, tmp_path):
        settings = tmp_path / "server-settings.json"
        settings.write_text("{}", encoding="utf-8")
        adminlist = tmp_path / "server-adminlist.json"
        adminlist.write_text("[]", encoding="utf-8")
        banlist = tmp_path / "server-banlist.json"
        banlist.write_text("[]", encoding="utf-8")
        whitelist = tmp_path / "server-whitelist.json"
        whitelist.write_text("[]", encoding="utf-8")

        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
        )
        builder.with_server_settings(settings)
        builder.with_access_lists(adminlist=adminlist, banlist=banlist, whitelist=whitelist)
        cmd = builder.build()

        assert f"--server-settings={settings}" in cmd
        assert f"--server-adminlist={adminlist}" in cmd
        assert f"--server-banlist={banlist}" in cmd
        assert f"--server-whitelist={whitelist}" in cmd
        assert "--use-server-whitelist" in cmd
        assert "--rcon-port=27015" in cmd
        assert "--rcon-password=secret" in cmd

    def test_extension_hook(self, tmp_path):
        def add_verbose(builder: RuntimeStartupBuilder) -> None:
            builder.add("--verbose")

        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        builder.with_extensions(add_verbose)
        cmd = builder.build()
        assert "--verbose" in cmd

    def test_password_masked_in_logs(self, tmp_path, caplog):
        import logging

        caplog.set_level(logging.INFO, logger="fsm.startup")
        builder = RuntimeStartupBuilder(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
        )
        cmd = builder.build()
        assert any("--rcon-password=******" in record.message for record in caplog.records)
        assert not any("secret" in record.message for record in caplog.records)
