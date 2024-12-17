package network

/*
#cgo CFLAGS: -g -O2
#include <stdlib.h>

int goctr_run(int argc, char *argv[]);
int goctr_exec(int argc, char *argv[]);
int goctr_kill(int argc, char *argv[]);
*/
import "C"

import (
	"bufio"
	"fmt"
	"os"
	"path"
	"strconv"
	"unsafe"

	"github.com/vishvananda/netns"
)

type GoctrNodeManager struct {
	nodeTmpDir    string
	nodeId2Handle map[int]netns.NsHandle
}

func (nm *GoctrNodeManager) Init() error {
	nm.nodeId2Handle = make(map[int]netns.NsHandle)
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

func (nm *GoctrNodeManager) Delete() error {
	return nil
}

func (nm *GoctrNodeManager) SetupNode(nodeId int) error {
	var pid int
	var nodeNetns netns.NsHandle

	nodeName := "node" + strconv.Itoa(nodeId)
	baseDir := path.Join(nm.nodeTmpDir, nodeName)
	err := os.MkdirAll(baseDir, os.ModePerm)
	if err != nil {
		fmt.Printf("Error MkdirAll: %s\n", err)
		return err
	}
	hostName := nodeName
	pidFilePath := path.Join(baseDir, "pid.txt")
	pidFileArg := "--pid-file=" + pidFilePath
	runLogFilePath := path.Join(baseDir, "run.log")
	logFileArg := "--log-file=" + runLogFilePath

	/* Make c function arguments */
	args := []string{baseDir, hostName, ImageRootfsPath, pidFileArg, "-v", logFileArg}
	cArgs := make([]*C.char, len(args))
	for i, arg := range args {
		cArgs[i] = C.CString(arg)
		defer C.free(unsafe.Pointer(cArgs[i])) // Free memory after usage
	}
	argc := C.int(len(cArgs))

	// Setup operation
	cPid := C.goctr_run(argc, &cArgs[0])
	pid = int(cPid)
	if pid < 0 {
		return fmt.Errorf("goctr_run for node %d failed", nodeId)
	}

	// // Cache netns handle of the node
	// pid, err = nm.getNodePid(nodeId)
	// if err != nil {
	// 	fmt.Printf("Failed to get pid of node #%d: %s\n", nodeId, err)
	// 	return err
	// }
	nodeNetns, err = netns.GetFromPid(pid)
	if err != nil {
		return err
	}
	nm.nodeId2Handle[nodeId] = nodeNetns

	return nil
}

func (nm *GoctrNodeManager) GetNodeNetNs(nodeId int) (netns.NsHandle, error) {
	var ok bool
	var nodeNetns netns.NsHandle

	nodeNetns, ok = nm.nodeId2Handle[nodeId]
	if !ok {
		return nodeNetns, fmt.Errorf("trying to get a non-exist netns (node #%d)", nodeId)
	}
	return nodeNetns, nil
}

func (nm *GoctrNodeManager) CleanNode(nodeId int) error {
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

	/* Make c function arguments */
	args := []string{strconv.Itoa(pid), "-v", logFileArg}
	cArgs := make([]*C.char, len(args))
	for i, arg := range args {
		cArgs[i] = C.CString(arg)
		defer C.free(unsafe.Pointer(cArgs[i])) // Free memory after usage
	}
	argc := C.int(len(cArgs))

	// Kill operation
	cRet := C.goctr_kill(argc, &cArgs[0])
	ret := int(cRet)
	if ret < 0 {
		return fmt.Errorf("goctr_kill for node %d failed", nodeId)
	}

	return nil
}

func (nm *GoctrNodeManager) getNodePid(nodeId int) (int, error) {
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
