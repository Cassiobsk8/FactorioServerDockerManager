from pathlib import Path

import pytest

from backend.services.startup_builder import (
    RuntimeStartupBuilder,
    StartupBuilder,
    StartupConfiguration,
)


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
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
            server_settings=settings,
        )
        cmd = RuntimeStartupBuilder(config).build()
        assert f"--server-settings={settings}" in cmd

    def test_server_settings_excluded_when_missing(self, tmp_path):
        settings = tmp_path / "server-settings.json"
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
            server_settings=settings,
        )
        cmd = RuntimeStartupBuilder(config).build()
        assert not any(part.startswith("--server-settings") for part in cmd)

    def test_adminlist_included_when_exists(self, tmp_path):
        adminlist = tmp_path / "server-adminlist.json"
        adminlist.write_text("[]", encoding="utf-8")
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
            adminlist=adminlist,
        )
        cmd = RuntimeStartupBuilder(config).build()
        assert f"--server-adminlist={adminlist}" in cmd

    def test_adminlist_excluded_when_missing(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
            adminlist=tmp_path / "missing.json",
        )
        cmd = RuntimeStartupBuilder(config).build()
        assert not any(part.startswith("--server-adminlist") for part in cmd)

    def test_banlist_included_when_exists(self, tmp_path):
        banlist = tmp_path / "server-banlist.json"
        banlist.write_text("[]", encoding="utf-8")
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
            banlist=banlist,
        )
        cmd = RuntimeStartupBuilder(config).build()
        assert f"--server-banlist={banlist}" in cmd

    def test_banlist_excluded_when_missing(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
            banlist=tmp_path / "missing.json",
        )
        cmd = RuntimeStartupBuilder(config).build()
        assert not any(part.startswith("--server-banlist") for part in cmd)

    def test_whitelist_enabled_includes_flags(self, tmp_path):
        whitelist = tmp_path / "server-whitelist.json"
        whitelist.write_text("[]", encoding="utf-8")
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
            whitelist=whitelist,
        )
        cmd = RuntimeStartupBuilder(config).build()
        assert f"--server-whitelist={whitelist}" in cmd
        assert "--use-server-whitelist" in cmd

    def test_whitelist_disabled_excludes_flags(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
            whitelist=tmp_path / "missing.json",
        )
        cmd = RuntimeStartupBuilder(config).build()
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

        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
            server_settings=settings,
            adminlist=adminlist,
            banlist=banlist,
            whitelist=whitelist,
        )
        cmd = RuntimeStartupBuilder(config).build()

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

        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
        )
        builder = RuntimeStartupBuilder(config)
        builder.extend(add_verbose)
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

    def test_port_included_when_set(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
            port="34200",
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
        assert "--port=34200" in cmd

    def test_port_excluded_when_none(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
        assert not any(part.startswith("--port") for part in cmd)

    def test_bind_included_when_set(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
            bind="0.0.0.0",
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
        assert "--bind=0.0.0.0" in cmd

    def test_rcon_bind_included_when_set(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
            rcon_bind="0.0.0.0",
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
        assert "--rcon-bind=0.0.0.0" in cmd

    def test_rcon_bind_excluded_when_no_password(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="",
            rcon_bind="0.0.0.0",
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
        assert not any(part.startswith("--rcon-bind") for part in cmd)

    def test_server_id_included_when_exists(self, tmp_path):
        server_id = tmp_path / "server-id.json"
        server_id.write_text("{}", encoding="utf-8")
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
            server_id=server_id,
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
        assert f"--server-id={server_id}" in cmd

    def test_server_id_excluded_when_none(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
        assert not any(part.startswith("--server-id") for part in cmd)

    def test_authserver_bans_included_when_enabled(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
            use_authserver_bans=True,
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
        assert "--use-authserver-bans" in cmd

    def test_authserver_bans_excluded_when_disabled(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
            use_authserver_bans=False,
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
        assert not any(part.startswith("--use-authserver-bans") for part in cmd)

    def test_parameter_order_consistency(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
            port="34200",
            bind="0.0.0.0",
            rcon_bind="127.0.0.1",
            use_authserver_bans=True,
            server_settings=tmp_path / "server-settings.json",
            adminlist=tmp_path / "server-adminlist.json",
            banlist=tmp_path / "server-banlist.json",
            whitelist=tmp_path / "server-whitelist.json",
        )
        for path in [
            config.server_settings,
            config.adminlist,
            config.banlist,
            config.whitelist,
        ]:
            if path:
                path.write_text("[]", encoding="utf-8")

        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()

        bin_idx = cmd.index(str(tmp_path / "factorio"))
        start_idx = cmd.index("--start-server=save.zip")
        port_idx = cmd.index("--port=34200")
        bind_idx = cmd.index("--bind=0.0.0.0")
        rcon_port_idx = cmd.index("--rcon-port=27015")
        rcon_password_idx = cmd.index("--rcon-password=secret")
        rcon_bind_idx = cmd.index("--rcon-bind=127.0.0.1")
        authserver_idx = cmd.index("--use-authserver-bans")
        settings_idx = cmd.index(f"--server-settings={config.server_settings}")
        adminlist_idx = cmd.index(f"--server-adminlist={config.adminlist}")
        banlist_idx = cmd.index(f"--server-banlist={config.banlist}")
        whitelist_idx = cmd.index(f"--server-whitelist={config.whitelist}")
        use_whitelist_idx = cmd.index("--use-server-whitelist")

        assert bin_idx < start_idx < port_idx < bind_idx < rcon_port_idx
        assert rcon_password_idx < rcon_bind_idx < authserver_idx < settings_idx
        assert settings_idx < adminlist_idx < banlist_idx < whitelist_idx < use_whitelist_idx

    def test_factorio_services_credentials_not_exposed_as_cli_args(self, tmp_path):
        config = StartupConfiguration(
            factorio_bin=tmp_path / "factorio",
            active_save="save.zip",
            rcon_port="27015",
            rcon_password="secret",
        )
        builder = RuntimeStartupBuilder(config)
        cmd = builder.build()
        assert not any(part.startswith("--username") for part in cmd)
        assert not any(part.startswith("--password") for part in cmd)
