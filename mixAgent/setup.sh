set -e 

echo "Tworzę środowisko wirtualne..."
python3 -m venv venv

echo "Aktywuję środowisko..."
source venv/bin/activate

echo "Instaluję zależności z requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Gotowe. Aktywuj środowisko poleceniem: source venv/bin/activate"