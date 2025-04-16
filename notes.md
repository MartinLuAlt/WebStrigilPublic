- Use older Twisted version to prevent scrapy bug  `pip install Twisted==22.10.0`

pip install pydantic

Ubuntu installation:

#! /bin/sh
sudo apt update
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install python3-pip -y
sudo apt install python3.12-venv -y

python3 -m venv .venv
source .venv/bin/activate

git clone https://github.com/MartinLuAlt/WebStrigilPublic
cd WebStrigilPublic/
pip install -r requirements.txt

playwright install-deps  
playwright install

#Todo: remove the plaintext secret
export OPEN_ROUTER_KEY=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
uvicorn api.main:app --host 0.0.0.0 --port 8000