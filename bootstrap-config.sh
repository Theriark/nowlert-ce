#!/bin/sh

set -eu

CONFIG_DIR="${1:-/nowlert/config}"
CONFIG_TEMPLATE="${2:-/usr/local/share/nowlert/config.example.yaml}"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"

mkdir -p "${CONFIG_DIR}"

if [ -e "${CONFIG_FILE}" ]; then
    exit 0
fi

CONFIG_TEMP=$(mktemp "${CONFIG_DIR}/.config.yaml.XXXXXX")
trap 'rm -f "${CONFIG_TEMP}"' 0 HUP INT TERM

cp "${CONFIG_TEMPLATE}" "${CONFIG_TEMP}"
chmod 600 "${CONFIG_TEMP}"
mv "${CONFIG_TEMP}" "${CONFIG_FILE}"

trap - 0 HUP INT TERM
echo "Initialized ${CONFIG_FILE} from the packaged default configuration."
