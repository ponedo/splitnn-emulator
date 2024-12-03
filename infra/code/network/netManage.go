package network

import (
	"fmt"
	"interleave_algo_test/algo"
	"os"
	"time"

	"github.com/vishvananda/netns"
)

type NodeManager interface {
	Init() error
	Delete() error
	SetupNode(int) error
	GetNodeNetNs(int) (netns.NsHandle, error)
	CleanNode(int) error
}

type LinkManager interface {
	Init(NodeManager) error
	Delete() error
	SetupAndEnterBbNs() error
	CleanAllBbNs() error
	SetupLink(int, int, int, int) error
}

func NetworkSetup(
	lm LinkManager, nm NodeManager,
	g *algo.Graph, nodeOrder []int, edgeOrder [][][4]int,
	backBoneNum int) error {
	var err error
	var curLinkNum int
	var nodeTotalTime, linkTotalTime time.Duration
	var origNs netns.NsHandle

	nm.Init()
	lm.Init(nm)

	origNs, err = netns.Get()
	if err != nil {
		return err
	}

	linkPerBackBoneNs := (g.GetEdgeNum() + backBoneNum - 1) / backBoneNum
	for i, nodeId := range nodeOrder {
		startNodeTime := time.Now()
		err = nm.SetupNode(nodeId)
		if err != nil {
			return err
		}
		nodeTotalTime += time.Since(startNodeTime)
		startLinkTime := time.Now()
		for _, edge := range edgeOrder[i] {
			if curLinkNum%linkPerBackBoneNs == 0 {
				err = lm.SetupAndEnterBbNs()
				if err != nil {
					return err
				}
			}
			err = lm.SetupLink(edge[0], edge[1], edge[2], edge[3])
			if err != nil {
				return err
			}
		}
		linkTotalTime += time.Since(startLinkTime)
	}
	fmt.Printf("Node setup time: %.2fs\n", nodeTotalTime.Seconds())
	fmt.Printf("Link setup time: %.2fs\n", linkTotalTime.Seconds())

	err = netns.Set(origNs)
	if err != nil {
		return err
	}

	lm.Delete()
	nm.Delete()

	return nil
}

func NetworkClean(
	lm LinkManager, nm NodeManager,
	g *algo.Graph, nodeOrder []int, edgeOrder [][][4]int,
	backBoneNum int) error {

	nm.Init()
	lm.Init(nm)

	lm.CleanAllBbNs()
	for nodeId := range g.AdjacencyList {
		nm.CleanNode(nodeId)
	}

	lm.Delete()
	nm.Delete()

	return nil
}

func DisableIpv6ForCurNetns() error {
	// Set disable_ipv6 for the namespace
	path := "/proc/sys/net/ipv6/conf/all/disable_ipv6"
	disableIPv6 := "1"

	f, err := os.OpenFile(path, os.O_WRONLY, 0644)
	if err != nil {
		return fmt.Errorf("failed to open sysctl file: %v", err)
	}
	defer f.Close()

	_, err = f.WriteString(disableIPv6)
	if err != nil {
		return fmt.Errorf("failed to write to sysctl file: %v", err)
	}

	return nil
}
