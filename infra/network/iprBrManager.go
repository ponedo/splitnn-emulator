package network

import (
	"os"
	"os/exec"
	"strconv"
)

type IprouteBridgeNetworkManager struct {
}

func (iprm *IprouteBridgeNetworkManager) Init() error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "add", "itl_test_bb")
	// fmt.Printf("SetupNodeCommand: %v\n", SetupNodeCommand)
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	return nil
}

func (iprm *IprouteBridgeNetworkManager) Delete() error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "del", "itl_test_bb")
	// fmt.Printf("SetupNodeCommand: %v\n", SetupNodeCommand)
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	return nil
}

func (iprm *IprouteBridgeNetworkManager) SetupNode(nodeId int) error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "add", "itl_test"+strconv.Itoa(nodeId))
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	return nil
}

func (iprm *IprouteBridgeNetworkManager) DestroyNode(nodeId int) error {
	DestroyNodeCommand := exec.Command(
		"ip", "netns", "del", "itl_test"+strconv.Itoa(nodeId))
	DestroyNodeCommand.Stdout = os.Stdout
	DestroyNodeCommand.Run()
	return nil
}

func (iprm *IprouteBridgeNetworkManager) SetupLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	if vxlanID == -1 {
		err = iprm.SetupInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	} else {
		err = iprm.SetupExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	}
	return err
}

func (iprm *IprouteBridgeNetworkManager) DestroyLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	if vxlanID == -1 {
		err = iprm.DestroyInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	} else {
		err = iprm.DestroyExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	}
	return err
}

func (iprm *IprouteBridgeNetworkManager) SetupInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var brName string
	if nodeIdi < nodeIdj {
		brName = "br-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj)
	} else {
		brName = "br-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi)
	}

	ConnectVethCommand := exec.Command(
		"ip", "netns", "exec", "itl_test_bb", "bash", "-c",
		"ip link add "+brName+" type bridge"+
			"; "+
			"ip link add eth-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+" type veth peer name eth"+strconv.Itoa(nodeIdj)+" netns "+"itl_test"+strconv.Itoa(nodeIdi)+
			"; "+
			"ip link add eth-"+strconv.Itoa(nodeIdj)+"-"+strconv.Itoa(nodeIdi)+" type veth peer name eth"+strconv.Itoa(nodeIdi)+" netns "+"itl_test"+strconv.Itoa(nodeIdj)+
			"; "+
			"ip link set eth-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+" master "+brName+
			"; "+
			"ip link set eth-"+strconv.Itoa(nodeIdj)+"-"+strconv.Itoa(nodeIdi)+" master "+brName+
			"; "+
			"ip link set "+brName+" up"+
			"; "+
			"ip link set eth-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+" up"+
			"; "+
			"ip link set eth-"+strconv.Itoa(nodeIdj)+"-"+strconv.Itoa(nodeIdi)+" up"+
			"; ",
	)
	// fmt.Printf("SetupLinkCommand: %v\n", ConnectVethCommand)
	ConnectVethCommand.Stdout = os.Stdout
	ConnectVethCommand.Run()

	SetupVethiCommand := exec.Command(
		"ip", "netns", "exec", "itl_test"+strconv.Itoa(nodeIdi),
		"ip", "link", "set", "eth"+strconv.Itoa(nodeIdj), "up",
	)
	SetupVethiCommand.Stdout = os.Stdout
	SetupVethiCommand.Run()

	SetupVethjCommand := exec.Command(
		"ip", "netns", "exec", "itl_test"+strconv.Itoa(nodeIdj),
		"ip", "link", "set", "eth"+strconv.Itoa(nodeIdi), "up",
	)
	SetupVethjCommand.Stdout = os.Stdout
	SetupVethjCommand.Run()
	return nil
}

func (iprm *IprouteBridgeNetworkManager) DestroyInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var brName string
	if nodeIdi < nodeIdj {
		brName = "br-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj)
	} else {
		brName = "br-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi)
	}
	DestroyLinkCommand := exec.Command(
		"ip", "netns", "exec", "itl_test_bb", "bash", "-c",
		"ip link del "+brName+" type bridge"+
			"; "+
			"ip link del eth-"+strconv.Itoa(nodeIdj)+"-"+strconv.Itoa(nodeIdi)+
			"; "+
			"ip link del eth-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+
			"; ",
	)
	DestroyLinkCommand.Stdout = os.Stdout
	DestroyLinkCommand.Run()
	return nil
}

func (iprm *IprouteBridgeNetworkManager) SetupExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var brName string
	if nodeIdi < nodeIdj {
		brName = "br-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj)
	} else {
		brName = "br-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi)
	}

	AddVxlanCommand := exec.Command(
		"ip", "link", "add", "vxl-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj),
		"type", "vxlan", "id", strconv.Itoa(vxlanID),
		"dev", LocalPhyIntf, "dstport", strconv.Itoa(4789),
		"remote", servers[serverID].IPAddr,
	)
	AddVxlanCommand.Stdout = os.Stdout
	AddVxlanCommand.Run()

	MoveVxlanCommand := exec.Command(
		"ip", "link", "set", "vxl-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj),
		"netns", "itl_test_bb",
	)
	MoveVxlanCommand.Stdout = os.Stdout
	MoveVxlanCommand.Run()

	ConnectVethCommand := exec.Command(
		"ip", "netns", "exec", "itl_test_bb", "bash", "-c",
		"ip link add "+brName+" type bridge"+
			"; "+
			"ip link add eth-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+" type veth peer name eth"+strconv.Itoa(nodeIdj)+" netns "+"itl_test"+strconv.Itoa(nodeIdi)+
			"; "+
			"ip link set eth-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+" master "+brName+
			"; "+
			"ip link set vxl-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+" master "+brName+
			"; "+
			"ip link set "+brName+" up"+
			"; "+
			"ip link set eth-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+" up"+
			"; "+
			"ip link set vxl-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+" up"+
			"; ",
	)
	// fmt.Printf("ConnectVethCommand: %v\n", ConnectVethCommand)
	ConnectVethCommand.Stdout = os.Stdout
	ConnectVethCommand.Run()

	SetupVethiCommand := exec.Command(
		"ip", "netns", "exec", "itl_test"+strconv.Itoa(nodeIdi),
		"ip", "link", "set", "eth"+strconv.Itoa(nodeIdj), "up",
	)
	SetupVethiCommand.Stdout = os.Stdout
	SetupVethiCommand.Run()

	return nil
}

func (iprm *IprouteBridgeNetworkManager) DestroyExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var brName string
	if nodeIdi < nodeIdj {
		brName = "br-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj)
	} else {
		brName = "br-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi)
	}
	DestroyLinkCommand := exec.Command(
		"ip", "netns", "exec", "itl_test_bb", "bash", "-c",
		"ip link del "+brName+" type bridge"+
			"; "+
			"ip link del eth-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+
			"; "+
			"ip link del vxl-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj)+
			"; ",
	)
	DestroyLinkCommand.Stdout = os.Stdout
	DestroyLinkCommand.Run()
	return nil
}
