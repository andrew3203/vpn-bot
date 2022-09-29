sudo apt update -y
sudo apt upgrade -y
sudo apt install wireguard -y

# WGRest server install
curl -L https://github.com/suquant/wgrest/releases/latest/download/wgrest_amd64.deb -o wgrest_amd64.deb
dpkg -i wgrest_amd64.deb

# WGRest Web App install
curl -L https://github.com/suquant/wgrest-webapp/releases/latest/download/wgrest-webapp_amd64.deb -o wgrest-webapp_amd64.deb
dpkg -i wgrest-webapp_amd64.deb

# Web UI install
curl -L https://github.com/suquant/wgrest/releases/latest/download/wgrest-linux-amd64 -o wgrest
chmod +x wgrest

# Web UI support  install
curl -L https://github.com/suquant/wgrest-webapp/releases/latest/download/webapp.tar.gz -o webapp.tar.gz
sudo mkdir -p /var/lib/wgrest/
sudo chown `whoami` /var/lib/wgrest/
tar -xzvf webapp.tar.gz -C /var/lib/wgrest/
rm webapp.tar.gz

# Create wg0
curl -O https://raw.githubusercontent.com/angristan/wireguard-install/master/wireguard-install.sh
chmod +x wireguard-install.sh
./wireguard-install.sh

# wgrest --static-auth-token "SUPER_SECRET_TOCKEN" --listen "IP:PORT"  &