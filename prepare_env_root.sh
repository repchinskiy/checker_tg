#!/bin/bash

function src_git_repo {
  #check if directory exists
  if [ -d "/root/root/checker_tg" ]; then
    echo "checker_tg exists, pulling latest changes"
    cd /root/checker_tg/checker_tg
    sudo -u root git pull
  else
    echo "checker_tg does not exist, cloning repo"
    sudo -u root mkdir -p /root/checker_tg/checker_tg
#    sudo -u root git clone https://github.com/DOUBLE-TOP/checker_tg/ /root/checker_tg/checker_tg
    sudo -u root git clone https://github.com/repchinskiy/checker_tg /root/checker_tg/checker_tg
    cd /root/checker_tg/checker_tg
  fi
}

function prepare_python_env {
  if [ -d "/root/checker_tg/venv" ]; then
    echo "venv exists, it's ok"
    sudo -u root bash << EOF
    source /root/checker_tg/venv/bin/activate
    pip install -r /root/checker_tg/checker_tg/requirements.txt
EOF
    return
  else
    cd /root/checker_tg
    
    # Проверяем наличие виртуального окружения
    if [ ! -d "venv" ]; then
        echo "venv does not exist, installing requirements"
        
        # Устанавливаем python3-venv
        sudo apt-get install python3-venv -y
        
        # Создаем виртуальное окружение от пользователя root
        sudo -u root python3 -m venv venv
    fi
    
    # Активируем виртуальное окружение и устанавливаем зависимости от пользователя root
    sudo -u root bash << EOF
    source /root/checker_tg/venv/bin/activate
    pip install -r /root/checker_tg/checker_tg/requirements.txt
EOF
  fi

}

function create_systemd {
  sudo tee <<EOF >/dev/null /etc/systemd/system/checker_tg.service
[Unit]
Description=Checker_tg
After=network-online.target
StartLimitIntervalSec=0
[Service]
User=root
Restart=always
RestartSec=3
LimitNOFILE=65535
ExecStart=/root/checker_tg/venv/bin/python3 /root/checker_tg/checker_tg/checker_tg.py
#ExecStart=/root/.pyenv/versions/3.11.10/bin/python3.11 /root/checker_tg/checker_tg/checker_tg.py
[Install]
WantedBy=multi-user.target
EOF

  sudo systemctl daemon-reload
  sudo systemctl enable checker_tg
  sudo systemctl restart checker_tg
}

function main {
  src_git_repo
  prepare_python_env
  create_systemd
}

main