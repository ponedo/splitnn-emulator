package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"path"
	"runtime"
	"time"
	"topo_setup_test/algo"
	"topo_setup_test/network"
)

var args struct {
	Operation        string
	BackboneNsNum    int
	Algorithm        string
	Topofile         string
	LinkManagerType  string
	NodeManagerType  string
	DisableIpv6      int
	ServerConfigFile string
	ServerID         int
}

func parseArgs() {
	/* Parse arguments */
	// flag.StringVar(
	// 	&args.Operation, "operation", "",
	// 	"Operation [setup|clean]")
	flag.StringVar(
		&args.Operation, "o", "",
		"Operation [setup|clean]")
	// flag.IntVar(
	// 	&args.BackboneNsNum, "bb-ns-num", 1,
	// 	"# of backbone network namespaces")
	flag.IntVar(
		&args.BackboneNsNum, "b", 1,
		"# of backbone network namespaces")
	// flag.StringVar(
	// 	&args.Algorithm, "algo", "",
	// 	"Interleave algorithm [naive|degree|dynamic|weighted_dynamic|best_weighted_dynamic]")
	flag.StringVar(
		&args.Algorithm, "a", "",
		"Interleave algorithm [naive|degree|dynamic|weighted_dynamic|best_weighted_dynamic]")
	// flag.StringVar(
	// 	&args.Topofile, "topofile", "",
	// 	"Name of topology file")
	flag.StringVar(
		&args.Topofile, "t", "",
		"Name of topology file")
	// flag.StringVar(
	// 	&args.LinkManagerType, "link-manager", "",
	// 	"Type of link manager [ntlbr]")
	flag.StringVar(
		&args.LinkManagerType, "l", "",
		"Type of link manager [ntlbr]")
	// flag.StringVar(
	// 	&args.NodeManagerType, "node-mamager", "",
	// 	"Type of node manager [cctr]")
	flag.StringVar(
		&args.NodeManagerType, "N", "",
		"Type of node manager [cctr]")
	// flag.IntVar(
	// 	&args.DisableIpv6, "disable-ipv6", 0,
	// 	"Value of sysctl disable_ipv6")
	flag.IntVar(
		&args.DisableIpv6, "d", 0,
		"Value of sysctl disable_ipv6")
	// flag.StringVar(
	// 	&args.ServerConfigFile, "server-file", "",
	// 	"Name of server config file")
	flag.StringVar(
		&args.ServerConfigFile, "s", "",
		"Name of server config file")
	// flag.IntVar(
	// 	&args.ServerID, "server-id", 0,
	// 	"ID of current server in server-file")
	flag.IntVar(
		&args.ServerID, "i", 0,
		"ID of current server in server-file")
	flag.Parse()

	/* Check whether args are valid */
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
	if args.LinkManagerType == "" {
		fmt.Println("Please notify LINK_MANAGER")
		return
	}
	if args.NodeManagerType == "" {
		fmt.Println("Please notify NODE_MANAGER")
		return
	}
}

var logFile *os.File

func redirectOutput(workDir string, operation string) {
	var err error
	logPath := path.Join(workDir, "tmp", operation+"_log.txt")
	logFile, err = os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
	if err != nil {
		log.Fatalf("Failed to open file: %v", err)
	}
	os.Stdout = logFile
	os.Stderr = logFile
}

func main() {
	parseArgs()

	topofile := args.Topofile
	algorithm := args.Algorithm
	operation := args.Operation

	/* Initialize network-related global variables */
	network.ConfigServers(args.ServerConfigFile)
	redirectOutput(network.ServerList[args.ServerID].WorkDir, operation)
	network.ConfigEnvs(args.ServerID, operation, args.DisableIpv6)
	network.StartMonitor(args.ServerID, operation)

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
	if operation == "clean" {
		// Reverse the order slices along the first dimension
		left, right := 0, len(nodeOrder)-1
		for left < right {
			nodeOrder[left], nodeOrder[right] = nodeOrder[right], nodeOrder[left]
			edgeOrder[left], edgeOrder[right] = edgeOrder[right], edgeOrder[left]
			left++
			right--
		}
	}

	/* Calculate accumulation of nodes */
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
	fmt.Printf("Plan time: %.2fs\n", end.Sub(start).Seconds())
	edgeSum := 0
	for _, edgeOrderElement := range edgeOrder {
		edgeSum += len(edgeOrderElement)
	}
	fmt.Println("edgeSum:", edgeSum)

	/* Prepare link and node managers */
	var linkManager network.LinkManager
	switch args.LinkManagerType {
	case "ntlbr":
		linkManager = &network.NtlBrLinkManager{}
	default:
		fmt.Printf("Invalid link manager: %v.\n", args.LinkManagerType)
		return
	}
	var nodeManager network.NodeManager
	switch args.NodeManagerType {
	case "cctr":
		nodeManager = &network.CctrNodeManager{}
	default:
		fmt.Printf("Invalid node manager: %v.\n", args.NodeManagerType)
		return
	}

	/* Execute operation */
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	start = time.Now()
	switch operation {
	case "setup":
		err = network.NetworkSetup(
			linkManager, nodeManager,
			graph, nodeOrder, edgeOrder,
			args.BackboneNsNum)
	case "clean":
		err = network.NetworkClean(
			linkManager, nodeManager,
			graph, nodeOrder, edgeOrder,
			args.BackboneNsNum)
	}
	if err != nil {
		fmt.Printf("Error: %v.\n", err)
	}
	end = time.Now()
	fmt.Printf("Network operation time: %.2fs\n", end.Sub(start).Seconds())

	/* Archive node runtime logs */
	err = network.ArchiveCctrLog(operation,
		graph, nodeOrder, edgeOrder)
	if err != nil {
		fmt.Printf("ArchiveLog error: %v.\n", err)
	}

	/* Clean env */
	network.StopMonitor(operation)
	network.CleanEnvs(args.Operation)
	logFile.Close()
}
