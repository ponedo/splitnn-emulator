package network

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path"
	"strconv"

	"github.com/vishvananda/netns"
)

type CctrNodeManager struct {
	nodeTmpDir    string
	nodeId2Handle map[int]netns.NsHandle
}

func (nm *CctrNodeManager) Init() error {
	nm.nodeId2Handle = make(map[int]netns.NsHandle)
	nm.nodeTmpDir = path.Join(TmpDir, "nodes")
	os.MkdirAll(nm.nodeTmpDir, os.ModePerm)
	return nil
}

func (nm *CctrNodeManager) Delete() error {
	return nil
}

func (nm *CctrNodeManager) SetupNode(nodeId int) error {
	var pid int
	var nodeNetns netns.NsHandle

	nodeName := "node" + strconv.Itoa(nodeId)
	baseDir := path.Join(nm.nodeTmpDir, nodeName)
	os.MkdirAll(baseDir, os.ModePerm)
	hostName := nodeName
	pidFilePath := path.Join(baseDir, "pid.txt")
	pidFileArg := "--pid-file=" + pidFilePath

	// Create the runlog file
	runLogFilePath := path.Join(baseDir, "run.log")
	runLogFile, err := os.Create(runLogFilePath)
	if err != nil {
		fmt.Printf("Error creating file: %s\n", err)
		return err
	}
	defer runLogFile.Close() // Ensure the file is closed after the program finishes

	// Setup command
	SetupNodeCommand := exec.Command(
		CctrPath, "run", baseDir, hostName, ImageRootfsPath, pidFileArg, "-v")
	SetupNodeCommand.Stdout = runLogFile
	SetupNodeCommand.Stderr = runLogFile
	SetupNodeCommand.Run()

	// Cache netns handle of the node
	pid, err = nm.getNodePid(nodeId)
	if err != nil {
		fmt.Printf("Failed to get pid of node #%d: %s\n", nodeId, err)
		return err
	}
	nodeNetns, err = netns.GetFromPid(pid)
	if err != nil {
		return err
	}
	nm.nodeId2Handle[nodeId] = nodeNetns

	return nil
}

func (nm *CctrNodeManager) GetNodeNetNs(nodeId int) (netns.NsHandle, error) {
	var ok bool
	var nodeNetns netns.NsHandle

	nodeNetns, ok = nm.nodeId2Handle[nodeId]
	if !ok {
		return nodeNetns, fmt.Errorf("trying to get a non-exist netns (node #%d)", nodeId)
	}
	return nodeNetns, nil
}

func (nm *CctrNodeManager) CleanNode(nodeId int) error {
	nodeName := "node" + strconv.Itoa(nodeId)
	baseDir := path.Join(nm.nodeTmpDir, nodeName)

	// Get pid
	pid, err := nm.getNodePid(nodeId)
	if err != nil {
		return err
	}

	// Create the kill log file
	killLogFilePath := path.Join(baseDir, "kill.log")

	fmt.Printf("killLogFilePath: %s\n", killLogFilePath)

	killLogFile, err := os.Create(killLogFilePath)
	if err != nil {
		fmt.Printf("Error creating file: %s\n", err)
		return err
	}
	defer killLogFile.Close() // Ensure the file is closed after the program finishes

	KillNodeCommand := exec.Command(
		CctrPath, "kill", strconv.Itoa(pid), "-v")
	KillNodeCommand.Stdout = killLogFile
	KillNodeCommand.Stderr = killLogFile
	KillNodeCommand.Run()
	return nil
}

func (nm *CctrNodeManager) getNodePid(nodeId int) (int, error) {
	pid := -1

	nodeName := "node" + strconv.Itoa(nodeId)
	baseDir := path.Join(nm.nodeTmpDir, nodeName)
	pidFilePath := path.Join(baseDir, "pid.txt")
	pidFile, err := os.Open(pidFilePath)
	if err != nil {
		fmt.Printf("Error opening file: %s\n", err)
		return -1, err
	}
	defer pidFile.Close() // Ensure the file is closed after reading

	// Create a scanner to read the file line by line
	scanner := bufio.NewScanner(pidFile)
	if scanner.Scan() {
		line := scanner.Text()
		pid, err = strconv.Atoi(line)
		if err != nil {
			fmt.Printf("Error parsing pid: %s\n", err)
			return -1, err
		}
	} else {
		fmt.Printf("Error reading pid file: %s\n", scanner.Err())
		return -1, err
	}

	return pid, nil
}
