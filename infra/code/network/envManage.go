package network

import (
	"encoding/json"
	"log"
	"os"
	"path"
	"strings"

	"github.com/vishvananda/netlink"
)

type Server struct {
	IPAddr          string `json:"ipAddr"`
	WorkDir         string `json:"infraWorkDir"`
	PhyIntf         string `json:"phyIntf"`
	DockerImageName string `json:"dockerImageName"`
}

type Servers struct {
	Servers []Server `json:"servers"`
}

var (
	ServerList      []Server
	LocalPhyIntf    string
	LocalPhyIntfNl  netlink.Link
	WorkDir         string
	TmpDir          string
	BinDir          string
	CctrPath        string
	ImageRootfsPath string
	DisableIpv6     int
)

func ConfigServers(confFileName string) {
	// Read the JSON file
	jsonFile, err := os.ReadFile(confFileName)
	if err != nil {
		log.Fatalf("Error reading the JSON file: %v", err)
	}

	var serversData Servers

	// Parse JSON into the struct
	err = json.Unmarshal(jsonFile, &serversData)
	if err != nil {
		log.Fatalf("Error parsing JSON: %v", err)
	}

	// Assign the parsed data to the global slice
	ServerList = serversData.Servers
}

func SetLocalPhyIntf(value string) {
	LocalPhyIntf = value
	LocalPhyIntfNl, _ = netlink.LinkByName(LocalPhyIntf)
}

func SetEnvPaths(workDir string, dockerImageName string) {
	WorkDir = workDir
	TmpDir = path.Join(workDir, "tmp")
	BinDir = path.Join(workDir, "bin")
	CctrPath = path.Join(BinDir, "cctr")

	splitedImageName := strings.Split(dockerImageName, ":")
	ImageRepo := splitedImageName[0]
	ImageTag := splitedImageName[1]
	ImageRootfsPath = path.Join(TmpDir, "img_bundles", ImageRepo, ImageTag, "rootfs")
}

func SetDisableIpv6(disableIpv6 int) {
	DisableIpv6 = 1
}

func ConfigEnvs(serverID int, disableIpv6 int) {
	server := ServerList[serverID]
	SetLocalPhyIntf(server.PhyIntf)
	SetEnvPaths(server.WorkDir, server.DockerImageName)
	SetDisableIpv6(disableIpv6)
}
