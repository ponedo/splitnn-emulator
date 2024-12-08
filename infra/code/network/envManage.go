package network

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path"
	"strconv"
	"strings"
	"time"
	"topo_setup_test/algo"

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
	Operation       string
	ServerList      []Server
	LocalPhyIntf    string
	LocalPhyIntfNl  netlink.Link
	WorkDir         string
	TmpDir          string
	BinDir          string
	CctrBinPath     string
	LinkLogPath     string
	LinkLogFile     *os.File
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
	CctrBinPath = path.Join(BinDir, "cctr")
	LinkLogPath = path.Join(TmpDir, "link_log.txt")

	splitedImageName := strings.Split(dockerImageName, ":")
	ImageRepo := splitedImageName[0]
	ImageTag := splitedImageName[1]
	ImageRootfsPath = path.Join(TmpDir, "img_bundles", ImageRepo, ImageTag, "rootfs")
}

func SetDisableIpv6(disableIpv6 int) {
	DisableIpv6 = disableIpv6
}

func PrepareRootfs(dockerImageName string) {
	prepareScriptPath := path.Join(WorkDir, "scripts", "prepare_rootfs.sh")
	fmt.Printf("dockerImageName: %s\n", dockerImageName)
	prepareCommand := exec.Command(
		prepareScriptPath, dockerImageName)
	prepareCommand.Stdout = os.Stdout
	prepareCommand.Stderr = os.Stderr
	prepareCommand.Run()
}

func OpenLinkLog() {
	var err error
	LinkLogFile, err = os.OpenFile(LinkLogPath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0644)
	if err != nil {
		log.Fatalf("Failed to open link log file: %v", err)
		LinkLogFile.Close()
	}
}

func CloseLinkLog() {
	LinkLogFile.Close()
}

func ConfigEnvs(serverID int, operation string, disableIpv6 int) {
	server := ServerList[serverID]
	Operation = operation
	SetLocalPhyIntf(server.PhyIntf)
	SetEnvPaths(server.WorkDir, server.DockerImageName)
	SetDisableIpv6(disableIpv6)
	PrepareRootfs(server.DockerImageName)
	if operation == "setup" {
		OpenLinkLog()
	}
}

func CleanEnvs(operation string) {
	if operation == "setup" {
		CloseLinkLog()
	}
}

func ArchiveCctrLog(operation string,
	g *algo.Graph, nodeOrder []int, edgeOrder [][][4]int) error {
	var srcLogName string
	var err error
	archiveDirPath := path.Join(TmpDir, "cctr_log")

	if operation == "setup" {
		srcLogName = "run.log"
		err = os.RemoveAll(archiveDirPath)
		if err != nil {
			fmt.Printf("Error RemoveAll: %s\n", err)
			return err
		}
	} else if operation == "clean" {
		srcLogName = "kill.log"
	} else {
		return fmt.Errorf("invalid operation %s", operation)
	}

	/* Create node log archive dir */
	err = os.MkdirAll(archiveDirPath, os.ModePerm)
	if err != nil {
		fmt.Printf("Error MkdirAll: %s\n", err)
		return err
	}

	/* Copy all log */
	tmpTime := time.Now()
	nodeNum := g.GetNodeNum()
	reportTime := 100
	nodePerReport := nodeNum / reportTime
	for i, nodeId := range nodeOrder {
		/* Progress reporter */
		if nodePerReport > 0 && i%nodePerReport == 0 {
			progress := 100 * i / nodeNum
			curTime := time.Now()
			fmt.Printf("%d%% nodes' log are archived, time elapsed from last report: %dms\n", progress, curTime.Sub(tmpTime).Milliseconds())
			tmpTime = time.Now()
		}

		/* Copy log */
		nodeTmpDir := path.Join(TmpDir, "nodes")
		nodeBaseDirPath := "node" + strconv.Itoa(nodeId)
		dstLogName := srcLogName + "." + strconv.Itoa(i)
		srcLogPath := path.Join(nodeTmpDir, nodeBaseDirPath, srcLogName)
		dstLogPath := path.Join(archiveDirPath, dstLogName)
		err = copyFile(srcLogPath, dstLogPath)
		if err != nil {
			fmt.Printf("Error copyFile: %s\n", err)
			return err
		}
	}

	return nil
}

func copyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return fmt.Errorf("error opening source file: %w", err)
	}
	defer sourceFile.Close()

	destinationFile, err := os.Create(dst)
	if err != nil {
		return fmt.Errorf("error creating destination file: %w", err)
	}
	defer destinationFile.Close()

	_, err = io.Copy(destinationFile, sourceFile)
	if err != nil {
		return fmt.Errorf("error copying file contents: %w", err)
	}

	err = destinationFile.Sync()
	if err != nil {
		return fmt.Errorf("error syncing destination file: %w", err)
	}

	return nil
}
