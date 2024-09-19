package network

import (
	"fmt"
	"net"
	"os"
	"os/exec"
	"strconv"

	"github.com/vishvananda/netlink"
	"github.com/vishvananda/netns"
)

type NetlinkBridgeNetworkManager struct {
	name2handle map[string]netns.NsHandle
}

func (ntlm *NetlinkBridgeNetworkManager) Init() error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "add", "itl_test_bb")
	// fmt.Printf("SetupNodeCommand: %v\n", SetupNodeCommand)
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	ntlm.name2handle = make(map[string]netns.NsHandle)
	return nil
}

func (ntlm *NetlinkBridgeNetworkManager) Delete() error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "del", "itl_test_bb")
	// fmt.Printf("SetupNodeCommand: %v\n", SetupNodeCommand)
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	return nil
}

func (ntlm *NetlinkBridgeNetworkManager) SetupNode(nodeId int) error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "add", "itl_test"+strconv.Itoa(nodeId))
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	return nil
}

func (ntlm *NetlinkBridgeNetworkManager) DestroyNode(nodeId int) error {
	DestroyNodeCommand := exec.Command(
		"ip", "netns", "del", "itl_test"+strconv.Itoa(nodeId))
	DestroyNodeCommand.Stdout = os.Stdout
	DestroyNodeCommand.Run()
	return nil
}

func (ntlm *NetlinkBridgeNetworkManager) SetupLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	if vxlanID == -1 {
		err = ntlm.SetupInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	} else {
		err = ntlm.SetupExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	}
	return err
}

func (ntlm *NetlinkBridgeNetworkManager) DestroyLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	if vxlanID == -1 {
		err = ntlm.DestroyInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	} else {
		err = ntlm.DestroyExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	}
	return err
}

func (ntlm *NetlinkBridgeNetworkManager) SetupInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var hostNetns, backboneNs, nodeiNetNs, nodejNetNs netns.NsHandle
	var brName string

	/* Prepare network namespace handles */
	hostNetns, err = netns.Get()
	if err != nil {
		return fmt.Errorf("failed to netns.Get: %s", err)
	}
	backboneNs, err = ntlm.getNsHandle("itl_test_bb")
	if err != nil {
		return err
	}
	nodeiNetNs, err = ntlm.getNsHandle("itl_test" + strconv.Itoa(nodeIdi))
	if err != nil {
		return err
	}
	nodejNetNs, err = ntlm.getNsHandle("itl_test" + strconv.Itoa(nodeIdj))
	if err != nil {
		return err
	}

	/* Switch to backbone's NetNs */
	err = netns.Set(backboneNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}

	/* Create a bridge and two veth pairs */
	if nodeIdi < nodeIdj {
		brName = "br-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj)
	} else {
		brName = "br-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi)
	}
	br := &netlink.Bridge{
		LinkAttrs: netlink.LinkAttrs{
			Name:  brName,
			MTU:   1450,
			Flags: net.FlagUp,
		},
	}
	if err := netlink.LinkAdd(br); err != nil {
		return fmt.Errorf("failed to create bridge: %s", err)
	}
	vethi := &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{
			Name:        "eth-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj),
			MTU:         1450,
			Flags:       net.FlagUp,
			MasterIndex: br.Index,
		},
		PeerName:      "eth" + strconv.Itoa(nodeIdj),
		PeerNamespace: netlink.NsFd(nodeiNetNs),
	}
	err = netlink.LinkAdd(vethi)
	if err != nil {
		return fmt.Errorf("failed to create VethPeer in nodeiNetNs: %s", err)
	}
	vethj := &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{
			Name:        "eth-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi),
			MTU:         1450,
			Flags:       net.FlagUp,
			MasterIndex: br.Index,
		},
		PeerName:      "eth" + strconv.Itoa(nodeIdi),
		PeerNamespace: netlink.NsFd(nodejNetNs),
	}
	err = netlink.LinkAdd(vethj)
	if err != nil {
		return fmt.Errorf("failed to create VethPeer in nodejNetNs: %s", err)
	}

	/* Set the other sides of veths up */
	var vethIni, vethInj netlink.Link
	err = netns.Set(nodeiNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	vethIni, err = netlink.LinkByName(
		"eth" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", vethIni, err)
	}
	err = netlink.LinkSetUp(vethIni)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}
	err = netns.Set(nodejNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	vethInj, err = netlink.LinkByName(
		"eth" + strconv.Itoa(nodeIdi))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", vethInj, err)
	}
	err = netlink.LinkSetUp(vethInj)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}

	/* Set NetNs Back */
	err = netns.Set(hostNetns)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	return err
}

func (ntlm *NetlinkBridgeNetworkManager) DestroyInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var hostNetns, backboneNs netns.NsHandle
	var brName string

	/* Prepare network namespace handles */
	hostNetns, err = netns.Get()
	if err != nil {
		return fmt.Errorf("failed to netns.Get: %s", err)
	}
	backboneNs, err = ntlm.getNsHandle("itl_test_bb")
	if err != nil {
		return err
	}

	/* Switch to backbone's NetNs */
	err = netns.Set(backboneNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}

	/* Remove two veth pairs and the bridge */
	vethi, err := netlink.LinkByName(
		"eth-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", vethi, err)
	}
	err = netlink.LinkDel(vethi)
	if err != nil {
		return fmt.Errorf("failed to delete vethi: %s", err)
	}
	vethj, err := netlink.LinkByName(
		"eth-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", vethj, err)
	}
	err = netlink.LinkDel(vethj)
	if err != nil {
		return fmt.Errorf("failed to delete vethj: %s", err)
	}
	if nodeIdi < nodeIdj {
		brName = "br-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj)
	} else {
		brName = "br-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi)
	}
	br, err := netlink.LinkByName(brName)
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", br, err)
	}
	err = netlink.LinkDel(br)
	if err != nil {
		return fmt.Errorf("failed to delete br: %s", err)
	}

	/* Set NetNs Back */
	err = netns.Set(hostNetns)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	return err
}

func (ntlm *NetlinkBridgeNetworkManager) SetupExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var hostNetns, backboneNs, nodeiNetNs netns.NsHandle
	var brName string

	/* Prepare network namespace handles */
	hostNetns, err = netns.Get()
	if err != nil {
		return fmt.Errorf("failed to netns.Get: %s", err)
	}
	backboneNs, err = ntlm.getNsHandle("itl_test_bb")
	if err != nil {
		return err
	}
	nodeiNetNs, err = ntlm.getNsHandle("itl_test" + strconv.Itoa(nodeIdi))
	if err != nil {
		return err
	}

	/* Create Vxlan */
	vxlan := &netlink.Vxlan{
		LinkAttrs: netlink.LinkAttrs{
			Name: "vxl-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj),
		},
		VxlanId:      vxlanID,
		VtepDevIndex: LocalPhyIntfNl.Attrs().Index,
		Port:         4789,
		Group:        net.ParseIP(servers[serverID].IPAddr),
		Learning:     true,
	}
	if err = netlink.LinkAdd(vxlan); err != nil {
		return fmt.Errorf("failed to create vxlan interface: %s", err)
	}
	err = netlink.LinkSetNsFd(vxlan, int(backboneNs))
	if err != nil {
		return fmt.Errorf("failed to link set nsfd: %s", err)
	}

	/* Switch to backbone's NetNs */
	err = netns.Set(backboneNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}

	/* Create bridge and a veth pair */
	if nodeIdi < nodeIdj {
		brName = "br-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj)
	} else {
		brName = "br-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi)
	}
	br := &netlink.Bridge{
		LinkAttrs: netlink.LinkAttrs{
			Name:  brName,
			MTU:   1450,
			Flags: net.FlagUp,
		},
	}
	if err := netlink.LinkAdd(br); err != nil {
		return fmt.Errorf("failed to create bridge: %s", err)
	}
	vethi := &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{
			Name:        "eth-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj),
			MTU:         1450,
			Flags:       net.FlagUp,
			MasterIndex: br.Index,
		},
		PeerName:      "eth" + strconv.Itoa(nodeIdj),
		PeerNamespace: netlink.NsFd(nodeiNetNs),
	}
	err = netlink.LinkAdd(vethi)
	if err != nil {
		return fmt.Errorf("failed to create VethPeer in nodeiNetNs: %s", err)
	}

	/* Set the other side of veth up */
	var vethIni netlink.Link
	err = netns.Set(nodeiNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	vethIni, err = netlink.LinkByName(
		"eth" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", vethIni, err)
	}
	err = netlink.LinkSetUp(vethIni)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}

	/* Set Vxlan master and set Vxlan up */
	err = netlink.LinkSetMaster(vxlan, br)
	if err != nil {
		return fmt.Errorf("failed to LinkSetMaster: %s", err)
	}
	err = netlink.LinkSetUp(vxlan)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}

	/* Set NetNs Back */
	err = netns.Set(hostNetns)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	return err
}

func (ntlm *NetlinkBridgeNetworkManager) DestroyExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var hostNetns, backboneNs netns.NsHandle
	var brName string

	/* Prepare network namespace handles */
	hostNetns, err = netns.Get()
	if err != nil {
		return fmt.Errorf("failed to netns.Get: %s", err)
	}
	backboneNs, err = ntlm.getNsHandle("itl_test_bb")
	if err != nil {
		return err
	}

	/* Switch to backbone's NetNs */
	err = netns.Set(backboneNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}

	/* Remove the veth pair, the vxlan and the bridge */
	vethi, err := netlink.LinkByName(
		"eth-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", vethi, err)
	}
	err = netlink.LinkDel(vethi)
	if err != nil {
		return fmt.Errorf("failed to delete vethi: %s", err)
	}
	vxlan, err := netlink.LinkByName(
		"vxl-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", vxlan, err)
	}
	err = netlink.LinkDel(vxlan)
	if err != nil {
		return fmt.Errorf("failed to delete vethj: %s", err)
	}
	if nodeIdi < nodeIdj {
		brName = "br-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj)
	} else {
		brName = "br-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi)
	}
	br, err := netlink.LinkByName(brName)
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", br, err)
	}
	err = netlink.LinkDel(br)
	if err != nil {
		return fmt.Errorf("failed to delete br: %s", err)
	}

	/* Set NetNs Back */
	err = netns.Set(hostNetns)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	return err
}

func (ntlm *NetlinkBridgeNetworkManager) getNsHandle(nsName string) (netns.NsHandle, error) {
	var err error
	nsHandle, ok := ntlm.name2handle[nsName]
	if !ok {
		nsHandle, err = netns.GetFromName(nsName)
		if err != nil {
			return 0, fmt.Errorf("failed to netns.GetFromName %s: %s", nsHandle, err)
		}
		ntlm.name2handle[nsName] = nsHandle
	}
	return nsHandle, nil
}
