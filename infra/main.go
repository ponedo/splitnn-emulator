package main

import (
	"flag"
	"fmt"
	"interleave_algo_test/algo"
	"interleave_algo_test/network"
	"runtime"
	"time"
)

var args struct {
	Operation          string
	Algorithm          string
	Topofile           string
	LocalPhyIntf       string
	ServerConfigFile   string
	NetworkManagerType string
}

func parseArgs() {
	/* Parse arguments */
	flag.StringVar(
		&args.Operation, "operation", "",
		"Operation [setup|destroy]")
	flag.StringVar(
		&args.Operation, "o", "",
		"Operation [setup|destroy]")
	flag.StringVar(
		&args.Algorithm, "algo", "",
		"Interleave algorithm [naive|degree|dynamic|weighted_dynamic|best_weighted_dynamic]")
	flag.StringVar(
		&args.Algorithm, "a", "",
		"Interleave algorithm [naive|degree|dynamic|weighted_dynamic|best_weighted_dynamic]")
	flag.StringVar(
		&args.Topofile, "topofile", "",
		"Name of topology file")
	flag.StringVar(
		&args.Topofile, "t", "",
		"Name of topology file")
	flag.StringVar(
		&args.NetworkManagerType, "manager", "",
		"Type of network manager [iprpt|iprbr|ntlpt|ntlbr]")
	flag.StringVar(
		&args.NetworkManagerType, "m", "",
		"Type of network manager [iprpt|iprbr|ntlpt|ntlbr]")
	flag.StringVar(
		&args.LocalPhyIntf, "phyintf", "",
		"Name of physical interface")
	flag.StringVar(
		&args.LocalPhyIntf, "p", "",
		"Name of physical interface")
	flag.StringVar(
		&args.ServerConfigFile, "serverfile", "",
		"Name of server config file")
	flag.StringVar(
		&args.ServerConfigFile, "s", "",
		"Name of server config file")
	flag.Parse()

	if args.Operation == "" {
		fmt.Println("Please notify OPERATION")
		return
	}
	if args.Algorithm == "" {
		fmt.Println("Please notify ALGORITHM")
		return
	}
	if args.Topofile == "" {
		fmt.Println("Please notify TOPOFILE")
		return
	}
	if args.NetworkManagerType == "" {
		fmt.Println("Please notify NETWORK_MANAGER")
		return
	}
}

func main() {
	parseArgs()

	topofile := args.Topofile
	algorithm := args.Algorithm
	operation := args.Operation

	/* Initialize global variables */
	network.SetLocalPhyIntf(args.LocalPhyIntf)
	network.ConfigServers(args.ServerConfigFile)

	/* Initialize graph file */
	graph, err := algo.ReadGraphFromFile(topofile)
	if err != nil {
		fmt.Printf("Error reading graph: %v\n", err)
		return
	}

	/* Compute interleaving node/link setup order */
	var nodeOrder, curEdgeNumSeq []int
	var edgeOrder [][][4]int
	start := time.Now()
	switch algorithm {
	case "naive":
		nodeOrder, edgeOrder, curEdgeNumSeq = graph.NaiveOrder()
	case "degree":
		nodeOrder, edgeOrder, curEdgeNumSeq = graph.MaximizeEdgesOrderDegree()
	case "dynamic":
		nodeOrder, edgeOrder, curEdgeNumSeq = graph.MaximizeEdgesOrderDynamic()
	case "weighted_dynamic":
		nodeOrder, edgeOrder, curEdgeNumSeq = graph.MaximizeEdgesOrderWeightedDynamic()
	case "best_weighted_dynamic":
		nodeOrder, edgeOrder, curEdgeNumSeq = graph.MaximizeEdgesOrderBestWeightedDynamic()
	default:
		fmt.Printf("Invalid network algorithm: %v.\n", algorithm)
		return
	}
	if operation == "destroy" {
		// Reverse the order slices along the first dimension
		left, right := 0, len(nodeOrder)-1
		for left < right {
			nodeOrder[left], nodeOrder[right] = nodeOrder[right], nodeOrder[left]
			edgeOrder[left], edgeOrder[right] = edgeOrder[right], edgeOrder[left]
			left++
			right--
		}
	}
	/* Calculate acculation of nodes */
	accNodeNum := 0
	for nodeNum := range curEdgeNumSeq {
		if nodeNum == 0 {
			continue
		}
		accNodeNum += nodeNum * (curEdgeNumSeq[nodeNum] - curEdgeNumSeq[nodeNum-1])
	}
	fmt.Println("Node Order:", nodeOrder)
	fmt.Println("Edge Order:", edgeOrder)
	fmt.Println("curEdgeNumSeq:", curEdgeNumSeq)
	fmt.Println("accNodeNum:", accNodeNum)
	end := time.Now()
	fmt.Printf("Plan time: %vs\n", end.Sub(start).Seconds())

	/* Compute interleaving order of node/link setup */
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	var networkManager network.NetworkManager
	switch args.NetworkManagerType {
	case "iprpt":
		networkManager = &network.IproutePassthroughNetworkManager{}
	case "iprbr":
		networkManager = &network.IprouteBridgeNetworkManager{}
	case "ntlpt":
		networkManager = &network.NetlinkPassthroughNetworkManager{}
	case "ntlbr":
		networkManager = &network.NetlinkBridgeNetworkManager{}
	case "ntlptlu":
		networkManager = &network.NetlinkPassthroughLookupNetworkManager{}
	case "ntlbrlu":
		networkManager = &network.NetlinkBridgeLookupNetworkManager{}
	default:
		fmt.Printf("Invalid network manager: %v.\n", args.NetworkManagerType)
		return
	}

	/* Execute operation */
	start = time.Now()
	switch operation {
	case "setup":
		err = network.NetworkSetup(
			networkManager, graph, nodeOrder, edgeOrder)
	case "destroy":
		err = network.NetworkDestroy(
			networkManager, graph, nodeOrder, edgeOrder)
	}
	if err != nil {
		fmt.Printf("Error: %v.\n", err)
	}
	end = time.Now()
	fmt.Printf("Network operation time: %vs\n", end.Sub(start).Seconds())
}
