package network

import (
	"os"
	"os/exec"
	"strconv"
)

type IproutePassthroughNetworkManager struct{}

func (iprm *IproutePassthroughNetworkManager) SetupBackboneNetns() error {
	return nil
}

func (iprm *IproutePassthroughNetworkManager) DestroyBackboneNetns() error {
	return nil
}

func (iprm *IproutePassthroughNetworkManager) Init() error {
	return nil
}

func (iprm *IproutePassthroughNetworkManager) Delete() error {
	return nil
}

func (iprm *IproutePassthroughNetworkManager) SetupNode(nodeId int) error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "add", "itl_test"+strconv.Itoa(nodeId))
	// fmt.Printf("SetupNodeCommand: %v\n", SetupNodeCommand)
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	return nil
}

func (iprm *IproutePassthroughNetworkManager) DestroyNode(nodeId int) error {
	DestroyNodeCommand := exec.Command(
		"ip", "netns", "del", "itl_test"+strconv.Itoa(nodeId))
	// fmt.Printf("DestroyNodeCommand: %v\n", DestroyNodeCommand)
	DestroyNodeCommand.Stdout = os.Stdout
	DestroyNodeCommand.Run()
	return nil
}

func (iprm *IproutePassthroughNetworkManager) SetupLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	if vxlanID == -1 {
		err = iprm.SetupInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	} else {
		err = iprm.SetupExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	}
	return err
}

func (iprm *IproutePassthroughNetworkManager) DestroyLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	if vxlanID == -1 {
		err = iprm.DestroyInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	} else {
		err = iprm.DestroyExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	}
	return err
}

func (iprm *IproutePassthroughNetworkManager) SetupInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	AddLinkCommand := exec.Command(
		"ip", "netns", "exec", "itl_test"+strconv.Itoa(nodeIdi),
		"ip", "link", "add", "eth"+strconv.Itoa(nodeIdj),
		"type", "veth", "peer",
		"name", "eth"+strconv.Itoa(nodeIdi),
		"netns", "itl_test"+strconv.Itoa(nodeIdj),
	)
	// fmt.Printf("AddLinkCommand: %v\n", AddLinkCommand)
	AddLinkCommand.Stdout = os.Stdout
	AddLinkCommand.Run()

	SetupLinkiCommand := exec.Command(
		"ip", "netns", "exec", "itl_test"+strconv.Itoa(nodeIdi),
		"ip", "link", "set", "eth"+strconv.Itoa(nodeIdj), "up",
	)
	// fmt.Printf("SetupLinkCommand: %v\n", SetupLinkiCommand)
	SetupLinkiCommand.Stdout = os.Stdout
	SetupLinkiCommand.Run()

	SetupLinkjCommand := exec.Command(
		"ip", "netns", "exec", "itl_test"+strconv.Itoa(nodeIdj),
		"ip", "link", "set", "eth"+strconv.Itoa(nodeIdi), "up",
	)
	// fmt.Printf("SetupLinkCommand: %v\n", SetupLinkjCommand)
	SetupLinkjCommand.Stdout = os.Stdout
	SetupLinkjCommand.Run()
	return nil
}

func (iprm *IproutePassthroughNetworkManager) DestroyInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	// DestroyLinkCommand := exec.Command(
	// 	"ip", "netns", "exec", "itl_test"+strconv.Itoa(nodeIdi),
	// 	"ip", "link", "del", "eth"+strconv.Itoa(nodeIdj),
	// )
	// // fmt.Printf("DestroyLinkCommand: %v\n", DestroyLinkCommand)
	// DestroyLinkCommand.Stdout = os.Stdout
	// DestroyLinkCommand.Run()
	return nil
}

func (iprm *IproutePassthroughNetworkManager) SetupExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	AddVxlanCommand := exec.Command(
		"ip", "link", "add", "eth"+strconv.Itoa(nodeIdj),
		"type", "vxlan", "id", strconv.Itoa(vxlanID),
		"dev", LocalPhyIntf, "dstport", strconv.Itoa(4789),
		"remote", servers[serverID].IPAddr,
	)
	AddVxlanCommand.Stdout = os.Stdout
	AddVxlanCommand.Run()

	MoveVxlanCommand := exec.Command(
		"ip", "link", "set", "eth"+strconv.Itoa(nodeIdj),
		"netns", "itl_test"+strconv.Itoa(nodeIdi),
	)
	MoveVxlanCommand.Stdout = os.Stdout
	MoveVxlanCommand.Run()

	SetupVxlanCommand := exec.Command(
		"ip", "netns", "exec", "itl_test"+strconv.Itoa(nodeIdi),
		"ip", "link", "set", "eth"+strconv.Itoa(nodeIdj), "up",
	)
	// fmt.Printf("SetupLinkCommand: %v\n", SetupLinkiCommand)
	SetupVxlanCommand.Stdout = os.Stdout
	SetupVxlanCommand.Run()

	return nil
}

func (iprm *IproutePassthroughNetworkManager) DestroyExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	DestroyLinkCommand := exec.Command(
		"ip", "netns", "exec", "itl_test"+strconv.Itoa(nodeIdi),
		"ip", "link", "del", "eth"+strconv.Itoa(nodeIdj),
	)
	// fmt.Printf("DestroyLinkCommand: %v\n", DestroyLinkCommand)
	DestroyLinkCommand.Stdout = os.Stdout
	DestroyLinkCommand.Run()
	return nil
}
