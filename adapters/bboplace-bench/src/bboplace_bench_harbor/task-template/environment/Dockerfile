FROM {base_image}

RUN set -eux; \
    for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do \
        [ -f "$f" ] || continue; \
        if grep -q "developer.download.nvidia.com/compute/cuda" "$f"; then \
            sed -i 's|^[[:space:]]*deb |# disabled stale cuda repo: deb |' "$f"; \
        fi; \
    done

RUN set -eux; \
    if command -v rg >/dev/null 2>&1 && ! dpkg-query -W -f='$${Status}' ripgrep 2>/dev/null | grep -q "install ok installed"; then \
        mkdir -p /tmp/ripgrep-dummy/DEBIAN; \
        printf '%s\n' \
            'Package: ripgrep' \
            'Version: 0.0.0-local' \
            'Section: utils' \
            'Priority: optional' \
            'Architecture: all' \
            'Maintainer: local <local@example.com>' \
            'Description: local marker package for preinstalled rg' \
            > /tmp/ripgrep-dummy/DEBIAN/control; \
        dpkg-deb --build /tmp/ripgrep-dummy /tmp/ripgrep-dummy.deb; \
        dpkg -i /tmp/ripgrep-dummy.deb; \
        rm -rf /tmp/ripgrep-dummy /tmp/ripgrep-dummy.deb; \
    fi

RUN python3 -m pip install --no-cache-dir requests numpy pyyaml || true

WORKDIR /app

COPY task_info.json submit.py submit.sh /app/
RUN chmod +x /app/submit.sh
