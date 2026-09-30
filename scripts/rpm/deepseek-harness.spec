Name:           deepseek-harness
Version:        0.2.0
Release:        1%{?dist}
Summary:        DeepSeek Harness Desktop & CLI for CentOS Stream 9 & 10
License:        MIT
URL:            https://github.com/deepseek-ai/deepseek-harness
Group:          Development/Tools
AutoReq:        no
AutoProv:       no
Requires:       bash, glibc >= 2.34, gtk3, libnotify, nss, xdg-utils, at-spi2-core

%define debug_package %{nil}
%define __strip /bin/true
%define __os_install_post %{nil}
%define _build_id_links none
%define _unpackaged_files_terminate_build 0
%define __check_files %{nil}

%description
DeepSeek Harness is an all-plugin agent harness developed by DeepSeek AI.
This package provides the official Native Electron Desktop Client and
command-line interface (dsh) for CentOS Stream / RHEL 9 and 10 (x86_64),
complete with an integrated CPython 3.12 primary runtime, Office skill
dependencies, and zero external Node.js requirement.

%prep

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/lib/deepseek-harness
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/lib/systemd/system
mkdir -p %{buildroot}/etc/sysconfig
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/pixmaps
mkdir -p %{buildroot}/usr/share/icons/hicolor/1024x1024/apps

PAYLOAD_DIR="%{_sourcedir}/apps/desktop/.desktop-build/targets/linux-x64/artifacts/linux-unpacked"
cp -a "$PAYLOAD_DIR"/* %{buildroot}/usr/lib/deepseek-harness/

chmod 0755 %{buildroot}/usr/lib/deepseek-harness/deepseek-harness
chmod 0755 %{buildroot}/usr/lib/deepseek-harness/chrome_crashpad_handler
chmod 4755 %{buildroot}/usr/lib/deepseek-harness/chrome-sandbox || chmod 0755 %{buildroot}/usr/lib/deepseek-harness/chrome-sandbox
if [ -f %{buildroot}/usr/lib/deepseek-harness/resources/runtime/cli/bin/dsh ]; then
    chmod 0755 %{buildroot}/usr/lib/deepseek-harness/resources/runtime/cli/bin/dsh
fi

cat << 'GUI_LAUNCHER' > %{buildroot}/usr/bin/deepseek-harness
#!/usr/bin/env bash
set -e

FLAGS=()
if [ -n "${WAYLAND_DISPLAY:-}" ] || [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
    FLAGS+=("--ozone-platform-hint=auto")
fi

if [ "$(id -u)" -eq 0 ]; then
    FLAGS+=("--no-sandbox")
fi

exec /usr/lib/deepseek-harness/deepseek-harness "${FLAGS[@]}" "$@"
GUI_LAUNCHER
chmod 0755 %{buildroot}/usr/bin/deepseek-harness

cat << 'LAUNCHER' > %{buildroot}/usr/bin/dsh
#!/usr/bin/env bash
set -e
exec /usr/lib/deepseek-harness/resources/runtime/cli/bin/dsh "$@"
LAUNCHER
chmod 0755 %{buildroot}/usr/bin/dsh

cat << 'SERVICE' > %{buildroot}/usr/lib/systemd/system/deepseek-harness.service
[Unit]
Description=DeepSeek Harness Web Service
After=network.target

[Service]
Type=simple
Environment="DSH_PORT=3080"
Environment="DSH_HOST=127.0.0.1"
EnvironmentFile=-/etc/sysconfig/deepseek-harness
ExecStart=/usr/bin/dsh web --no-open --port $DSH_PORT --host $DSH_HOST
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
SERVICE

cat << 'SYSCONFIG' > %{buildroot}/etc/sysconfig/deepseek-harness
# DeepSeek Harness Service Configuration
# DEEPSEEK_API_KEY=your_api_key_here
DSH_PORT=3080
DSH_HOST=127.0.0.1
SYSCONFIG

cp %{_sourcedir}/apps/desktop/resources/icon.png %{buildroot}/usr/share/pixmaps/deepseek-harness.png
cp %{_sourcedir}/apps/desktop/resources/icon.png %{buildroot}/usr/share/icons/hicolor/1024x1024/apps/deepseek-harness.png

cat << 'DESKTOP' > %{buildroot}/usr/share/applications/deepseek-harness.desktop
[Desktop Entry]
Name=DeepSeek Harness
GenericName=AI Agent Harness
Comment=DeepSeek AI Agent Harness Desktop Client
Exec=/usr/bin/deepseek-harness %U
Icon=deepseek-harness
Terminal=false
Type=Application
StartupNotify=true
StartupWMClass=deepseek-harness
Categories=Development;Utility;
MimeType=x-scheme-handler/dsh;
DESKTOP
chmod 0644 %{buildroot}/usr/share/applications/deepseek-harness.desktop

%pre
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME="${NAME:-Linux}"
    OS_VER="${VERSION_ID:-}"
    MAJOR_VER="${OS_VER%%.*}"
    echo "[DeepSeek Harness] Detected OS: ${OS_NAME} ${OS_VER} ($(uname -m))"
    if [ -n "$MAJOR_VER" ] && [ "$MAJOR_VER" -lt 9 ] 2>/dev/null; then
        echo "[DeepSeek Harness] Error: DeepSeek Harness requires CentOS Stream / RHEL 9 or 10. Detected version ${OS_VER} is not supported." >&2
        exit 1
    fi
fi

%post
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME="${NAME:-Linux}"
    OS_VER="${VERSION_ID:-}"
    MAJOR_VER="${OS_VER%%.*}"
    echo "[DeepSeek Harness] Configuring for ${OS_NAME} ${OS_VER}..."

    if command -v dnf >/dev/null 2>&1; then
        MISSING_PKGS=()
        for pkg in gtk3 libnotify nss xdg-utils at-spi2-core; do
            if ! rpm -q "$pkg" >/dev/null 2>&1; then
                MISSING_PKGS+=("$pkg")
            fi
        done

        if [ "$MAJOR_VER" = "9" ]; then
            if ! rpm -q mesa-dri-drivers >/dev/null 2>&1; then
                MISSING_PKGS+=("mesa-dri-drivers")
            fi
        fi

        if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
            echo "[DeepSeek Harness] Resolving ${OS_NAME} dependencies: ${MISSING_PKGS[*]}..."
            dnf install -y "${MISSING_PKGS[@]}" >/dev/null 2>&1 || :
        fi
    fi
fi

update-desktop-database >/dev/null 2>&1 || :
gtk-update-icon-cache /usr/share/icons/hicolor >/dev/null 2>&1 || :
systemctl daemon-reload >/dev/null 2>&1 || :
systemctl enable --now deepseek-harness.service >/dev/null 2>&1 || :

TARGET_USER="${SUDO_USER:-$(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $3}' | head -n 1)}"
if [ -n "$TARGET_USER" ]; then
    USER_UID=$(id -u "$TARGET_USER" 2>/dev/null || echo "")
    if [ -n "$USER_UID" ] && [ -d "/run/user/$USER_UID" ]; then
        (
            sleep 1
            systemd-run --user --machine="${TARGET_USER}@.host" /usr/bin/deepseek-harness >/dev/null 2>&1 || \
            sudo -u "$TARGET_USER" DISPLAY="${DISPLAY:-:0}" WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}" XDG_RUNTIME_DIR="/run/user/$USER_UID" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$USER_UID/bus" /usr/bin/deepseek-harness >/dev/null 2>&1 || :
        ) >/dev/null 2>&1 &
    fi
fi

%preun
if [ $1 -eq 0 ]; then
    systemctl --no-reload disable --now deepseek-harness.service >/dev/null 2>&1 || :
fi

%postun
systemctl daemon-reload >/dev/null 2>&1 || :
update-desktop-database >/dev/null 2>&1 || :
gtk-update-icon-cache /usr/share/icons/hicolor >/dev/null 2>&1 || :

%files
/usr/bin/dsh
/usr/bin/deepseek-harness
/usr/lib/deepseek-harness
/usr/lib/systemd/system/deepseek-harness.service
/usr/share/applications/deepseek-harness.desktop
/usr/share/pixmaps/deepseek-harness.png
/usr/share/icons/hicolor/1024x1024/apps/deepseek-harness.png
%config(noreplace) /etc/sysconfig/deepseek-harness
