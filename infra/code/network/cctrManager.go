package network

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path"
	"strconv"
	"time"

	"github.com/vishvananda/netns"
)

type CctrNodeManager struct {
	nodeTmpDir string
	// nodeId2Handle map[int]netns.NsHandle
	nodeId2Pid map[int]int
}

func (nm *CctrNodeManager) Init() error {
	// nm.nodeId2Handle = make(map[int]netns.NsHandle)
	nm.nodeId2Pid = make(map[int]int)
	var err error
	nm.nodeTmpDir = path.Join(TmpDir, "nodes")
	if Operation == "setup" {
		err = os.RemoveAll(nm.nodeTmpDir)
		if err != nil {
			fmt.Printf("Error RemoveAll: %s\n", err)
			return err
		}
	}
	err = os.MkdirAll(nm.nodeTmpDir, os.ModePerm)
	if err != nil {
		fmt.Printf("Error MkdirAll: %s\n", err)
		return err
	}
	return nil
}

func (nm *CctrNodeManager) Delete() error {
	return nil
}

func (nm *CctrNodeManager) SetupNode(nodeId int) (time.Duration, error) {
	var pid int
	// var nodeNetns netns.NsHandle

	nodeName := "node" + strconv.Itoa(nodeId)
	baseDir := path.Join(nm.nodeTmpDir, nodeName)
	err := os.MkdirAll(baseDir, os.ModePerm)
	if err != nil {
		fmt.Printf("Error MkdirAll: %s\n", err)
		return -1, err
	}
	hostName := nodeName
	pidFilePath := path.Join(baseDir, "pid.txt")
	// runLogFilePath := path.Join(baseDir, "run.log")
	pidFileArg := "--pid-file=" + pidFilePath
	// logFileArg := "--log-file=" + runLogFilePath

	// Setup command
	startCtrTime := time.Now()
	// SetupNodeCommand := exec.Command(
	// 	CctrBinPath, "run", baseDir, hostName, ImageRootfsPath, pidFileArg, "-v", logFileArg)
	SetupNodeCommand := exec.Command(
		CctrBinPath, "run", baseDir, hostName, ImageRootfsPath, pidFileArg)
	SetupNodeCommand.Run()
	ctrTime := time.Since(startCtrTime)

	// Cache netns handle of the node
	pid, err = nm.getNodePid(nodeId)
	if err != nil {
		fmt.Printf("Failed to get pid of node #%d: %s\n", nodeId, err)
		return -1, err
	}
	// nodeNetns, err = netns.GetFromPid(pid)
	// if err != nil {
	// 	return -1, err
	// }
	// nm.nodeId2Handle[nodeId] = nodeNetns
	nm.nodeId2Pid[nodeId] = pid

	return ctrTime, nil
}

func (nm *CctrNodeManager) GetNodeNetNs(nodeId int) (netns.NsHandle, error) {
	var ok bool
	var pid int
	var err error
	var nodeNetns netns.NsHandle

	// nodeNetns, ok = nm.nodeId2Handle[nodeId]
	// if !ok {
	// 	return nodeNetns, fmt.Errorf("trying to get a non-exist netns (node #%d)", nodeId)
	// }
	pid, ok = nm.nodeId2Pid[nodeId]
	if !ok {
		return nodeNetns, fmt.Errorf("trying to get a non-exist netns (node #%d)", nodeId)
	}
	nodeNetns, err = netns.GetFromPid(pid)
	if err != nil {
		return -1, err
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
	logFileArg := "--log-file=" + killLogFilePath

	KillNodeCommand := exec.Command(
		CctrBinPath, "kill", strconv.Itoa(pid), "-v", logFileArg)
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
