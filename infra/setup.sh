# apt-get install -y linux-headers-$(uname -r) iproute2 bpfcc-tools bpftrace clang llvm libelf-dev iptables bpftool

# wget https://github.com/cilium/cilium/archive/refs/tags/v1.16.1.tar.gz -O cilium.tar.gz
# tar xzvfC cilium.tar.gz /usr/local/bin


CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
CLI_ARCH=amd64
if [ "$(uname -m)" = "aarch64" ]; then CLI_ARCH=arm64; fi
curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}
sha256sum --check cilium-linux-${CLI_ARCH}.tar.gz.sha256sum
sudo tar xzvfC cilium-linux-${CLI_ARCH}.tar.gz /usr/local/bin
rm cilium-linux-${CLI_ARCH}.tar.gz.sha256sum
