package network

import (
	"encoding/json"
	"fmt"
	"interleave_algo_test/algo"
	"log"
	"os"
	"time"

	"github.com/vishvananda/netlink"
)

type Server struct {
	IPAddr string `json:"ipAddr"`
}

type Servers struct {
	Servers []Server `json:"servers"`
}

var (
	LocalPhyIntf   string
	LocalPhyIntfNl netlink.Link
	servers        []Server
)

func SetLocalPhyIntf(value string) {
	LocalPhyIntf = value
	LocalPhyIntfNl, _ = netlink.LinkByName(LocalPhyIntf)
}

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
	servers = serversData.Servers
}

type NetworkManager interface {
	SetupNode(int) error
	DestroyNode(int) error
	SetupLink(int, int, int, int) error
	DestroyLink(int, int, int, int) error
	Init() error
	Delete() error
}

func NetworkSetup(nm NetworkManager, g *algo.Graph, nodeOrder []int, edgeOrder [][][4]int) error {
	var err error
	var nodeTotalTime, linkTotalTime time.Duration
	err = nm.Init()
	if err != nil {
		return err
	}
	for i, nodeId := range nodeOrder {
		startNodeTime := time.Now()
		err = nm.SetupNode(nodeId)
		if err != nil {
			return err
		}
		nodeTotalTime += time.Since(startNodeTime)
		startLinkTime := time.Now()
		for _, edge := range edgeOrder[i] {
			err = nm.SetupLink(edge[0], edge[1], edge[2], edge[3])
			if err != nil {
				return err
			}
		}
		linkTotalTime += time.Since(startLinkTime)
	}
	err = nm.Delete()
	if err != nil {
		return err
	}
	fmt.Printf("Node setup time: %.2fs\n", nodeTotalTime.Seconds())
	fmt.Printf("Link setup time: %.2fs\n", linkTotalTime.Seconds())
	return nil
}

func NetworkDestroy(nm NetworkManager, g *algo.Graph, nodeOrder []int, edgeOrder [][][4]int) error {
	var err error
	var nodeTotalTime, linkTotalTime time.Duration
	err = nm.Init()
	if err != nil {
		return err
	}
	for i, nodeId := range nodeOrder {
		startLinkTime := time.Now()
		for _, edge := range edgeOrder[i] {
			err = nm.DestroyLink(edge[0], edge[1], edge[2], edge[3])
			if err != nil {
				return err
			}
		}
		linkTotalTime += time.Since(startLinkTime)
		startNodeTime := time.Now()
		err = nm.DestroyNode(nodeId)
		if err != nil {
			return err
		}
		nodeTotalTime += time.Since(startNodeTime)
	}
	err = nm.Delete()
	if err != nil {
		return err
	}
	fmt.Printf("Node Destroy time: %.2fs\n", nodeTotalTime.Seconds())
	fmt.Printf("Link Destroy time: %.2fs\n", linkTotalTime.Seconds())
	return nil
}
