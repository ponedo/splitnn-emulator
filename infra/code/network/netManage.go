package network

import (
	"fmt"
	"os"
	"time"
	"topo_setup_test/algo"

	"github.com/vishvananda/netns"
)

type NodeManager interface {
	Init() error
	Delete() error
	SetupNode(int) (time.Duration, error)
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
	var ctrTime, ctrTotalTime, nodeTotalTime, linkTotalTime time.Duration
	var hostNs netns.NsHandle
	// var hostNs, origNs netns.NsHandle

	nm.Init()
	lm.Init(nm)

	hostNs, err = netns.Get()
	if err != nil {
		return err
	}
	defer hostNs.Close()

	tmpTime := time.Now()
	nodeNum := g.GetNodeNum()
	reportTime := 100
	nodePerReport := nodeNum / reportTime
	linkPerBackBoneNs := (g.GetEdgeNum() + backBoneNum - 1) / backBoneNum
	for i, nodeId := range nodeOrder {
		/* Progress reporter */
		if nodePerReport > 0 && i%nodePerReport == 0 {
			progress := 100 * i / nodeNum
			curTime := time.Now()
			fmt.Printf("%d%% nodes are added, time elapsed from last report: %dms\n", progress, curTime.Sub(tmpTime).Milliseconds())
			tmpTime = time.Now()
		}

		/* Setup next node and connectable links */
		startNodeTime := time.Now()
		ctrTime, err = nm.SetupNode(nodeId)
		if err != nil {
			return err
		}
		ctrTotalTime += ctrTime
		nodeTotalTime += time.Since(startNodeTime)

		_, err = LinkLogFile.WriteString(
			fmt.Sprintf("Node %d\n", nodeId))
		if err != nil {
			return err
		}

		startLinkTime := time.Now()
		for _, edge := range edgeOrder[i] {
			curLinkStartTime := time.Now()
			/* Create new backbone network namespace on demand */
			if curLinkNum%linkPerBackBoneNs == 0 {
				err = lm.SetupAndEnterBbNs()
				if err != nil {
					return err
				}
			}
			/* Setup connectable links */
			err = lm.SetupLink(edge[0], edge[1], edge[2], edge[3])
			if err != nil {
				return err
			}

			curLinkTime := time.Since(curLinkStartTime)
			curLinkTimeInNs := curLinkTime.Nanoseconds()
			_, err = LinkLogFile.WriteString(
				fmt.Sprintf("Link no.%d %dns\n", curLinkNum, curLinkTimeInNs))
			if err != nil {
				return err
			}

			curLinkNum += 1
		}
		linkTotalTime += time.Since(startLinkTime)
	}
	fmt.Printf("Ctr setup time: %.2fs\n", ctrTotalTime.Seconds())
	fmt.Printf("Node setup time: %.2fs\n", nodeTotalTime.Seconds())
	fmt.Printf("Link setup time: %.2fs\n", linkTotalTime.Seconds())

	err = netns.Set(hostNs)
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
