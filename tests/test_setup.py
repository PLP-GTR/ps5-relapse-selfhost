"""Offline integration checks for the setup helper; no upstream code is fetched."""

import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get("BASH_BIN") or shutil.which("bash")


@unittest.skipUnless(BASH and shutil.which("git"), "Bash and Git are required")
class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="relapse-setup-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        for name in ("scripts", "overlay", "dnsmasq", "nginx", "unraid", "docs", "docker"):
            shutil.copytree(ROOT / name, self.repo / name)
        for name in (".env.example", ".gitignore", "README.md", "docker-compose.yml"):
            shutil.copyfile(ROOT / name, self.repo / name)

        # Keep the tests usable with Git Bash and a Windows Python installation.
        shim = self.repo / "test-bin"
        shim.mkdir()
        python = shlex.quote(sys.executable.replace("\\", "/"))
        (shim / "python3").write_text(
            f'#!/usr/bin/env bash\nexec {python} "$@"\n', encoding="utf-8"
        )
        (shim / "python3").chmod(0o755)
        self.env = os.environ.copy()
        for key in (
            "SERVER_IP", "GUIDE_IP", "HOST_REPO", "HOST_REF", "WWW_DIR",
            "OVERLAY_DIR", "CERT_DIR", "CERT_DAYS", "FTPSRV_URL", "FTPSRV_SHA256",
        ):
            self.env.pop(key, None)
        self.env["GIT_CONFIG_GLOBAL"] = os.devnull
        self.env["GIT_CONFIG_NOSYSTEM"] = "1"
        if os.name == "nt":
            # Git Bash otherwise rewrites OpenSSL's /CN= subject as a path.
            self.env["MSYS2_ARG_CONV_EXCL"] = "/CN="
            self.env["MSYS2_ENV_CONV_EXCL"] = "MSYS2_ARG_CONV_EXCL"

        # A local Git fixture exercises checkout and overlay behavior without
        # downloading an exploit or running any payload.
        upstream = self.base / "upstream"
        (upstream / "payloads").mkdir(parents=True)
        (upstream / "payloads/payloads.json").write_text("[]\n", encoding="utf-8")
        (upstream / "index.html").write_text("fixture\n", encoding="utf-8")
        self.git(upstream, "init", "-q")
        self.git(upstream, "add", ".")
        self.git(upstream, "-c", "user.name=Fixture", "-c",
                 "user.email=fixture@example.invalid", "commit", "-qm", "Fixture")
        revision = self.git(upstream, "rev-parse", "HEAD").strip()
        self.settings = {
            "SERVER_IP": "192.168.1.50",
            "HOST_REPO": upstream.as_posix(),
            "HOST_REF": revision,
        }

    def git(self, directory, *args):
        return subprocess.check_output(
            ["git", "-C", str(directory), *args], env=self.env, text=True
        )

    def configure(self, **overrides):
        settings = self.settings | overrides
        (self.repo / ".env").write_text(
            "".join(f"{key}={shlex.quote(value)}\n" for key, value in settings.items()),
            encoding="utf-8",
        )

    def run_helper(self, *args, expected=0):
        result = subprocess.run(
            [BASH, "-c", 'export PATH="$PWD/test-bin:$PATH"; '
             'exec python3 docker/setup/entrypoint.py "$@"', "setup-test", *args],
            cwd=self.repo, env=self.env, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def ftp_fixture(self):
        payload = self.base / "fixture.elf"
        payload.write_bytes(b"inert checksum fixture; never executed\n")
        return payload, hashlib.sha256(payload.read_bytes()).hexdigest()

    def test_prepare_and_rerun_preserve_certificate(self):
        self.configure()
        self.run_helper()
        certificate = (self.repo / "certs/manuals.crt").read_bytes()
        self.assertEqual((self.repo / "www/index.html").read_bytes(),
                         (self.repo / "overlay/index.html").read_bytes())
        self.assertIn("address=/manuals.playstation.net/192.168.1.50",
                      (self.repo / "dnsmasq/dnsmasq.conf").read_text())
        self.assertFalse((self.repo / "www/payloads/ftpsrv-ps5.elf").exists())
        self.run_helper("prepare")
        self.assertEqual((self.repo / "certs/manuals.crt").read_bytes(), certificate)

    def test_prepare_with_ftp_verifies_and_installs_payload(self):
        payload, digest = self.ftp_fixture()
        self.configure(FTPSRV_URL=payload.as_uri(), FTPSRV_SHA256=digest)
        self.run_helper("prepare", "--with-ftp")
        self.assertEqual((self.repo / "www/payloads/ftpsrv-ps5.elf").read_bytes(),
                         payload.read_bytes())
        self.assertIn("ftpsrv-ps5.elf",
                      (self.repo / "www/payloads/payloads.json").read_text())

    def test_bad_checksum_does_not_install_payload(self):
        payload, _ = self.ftp_fixture()
        self.configure(FTPSRV_URL=payload.as_uri(), FTPSRV_SHA256="0" * 64)
        result = self.run_helper("prepare", "--with-ftp", expected=1)
        self.assertIn("SHA-256 mismatch", result.stderr)
        self.assertFalse((self.repo / "www/payloads/ftpsrv-ps5.elf").exists())
        self.assertEqual((self.repo / "www/payloads/payloads.json").read_text(), "[]\n")

    def test_invalid_address_stops_preparation_before_writing(self):
        self.configure(GUIDE_IP="invalid.example")
        result = self.run_helper("prepare", expected=1)
        self.assertIn("GUIDE_IP must be an IPv4 address", result.stderr)
        for name in ("certs", "www", "dnsmasq/dnsmasq.conf", "nginx/default.conf"):
            self.assertFalse((self.repo / name).exists())

    def test_render_only_supports_separate_proxy_ip(self):
        self.configure(GUIDE_IP="192.168.1.51")
        self.run_helper("render-config")
        self.assertIn("address=/manuals.playstation.net/192.168.1.51",
                      (self.repo / "dnsmasq/dnsmasq.conf").read_text())
        self.assertFalse((self.repo / "www").exists())
        self.assertFalse((self.repo / "certs").exists())

    def test_prepare_accepts_crlf_scripts_and_env(self):
        self.configure(GUIDE_IP="192.168.1.51")
        paths = list((self.repo / "scripts").glob("*.sh")) + [self.repo / ".env"]
        for path in paths:
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.run_helper("prepare")
        for path in paths:
            self.assertNotIn(b"\r\n", path.read_bytes())
        self.assertIn("address=/manuals.playstation.net/192.168.1.51",
                      (self.repo / "dnsmasq/dnsmasq.conf").read_text())
        self.assertTrue((self.repo / "certs/manuals.key").is_file())

    def test_bootstrap_accepts_crlf_runner(self):
        self.configure()
        runner = self.repo / "docker/setup/entrypoint.sh"
        runner.write_bytes(runner.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.run_helper("render-config")
        self.assertTrue((self.repo / "dnsmasq/dnsmasq.conf").is_file())

    def test_help_and_invalid_arguments_do_not_prepare(self):
        self.run_helper("help")
        self.run_helper("prepare", "--unknown", expected=2)
        self.run_helper("verify", "extra", expected=2)
        self.run_helper("unknown", expected=2)
        self.assertFalse((self.repo / "www").exists())


if __name__ == "__main__":
    unittest.main()
