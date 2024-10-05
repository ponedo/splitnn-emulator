package network

import (
	"fmt"
	"net"
	"os"
	"os/exec"
	"strconv"
	"time"

	"github.com/vishvananda/netlink"
	"github.com/vishvananda/netns"
)

type NetlinkBridgeNsIndexNetworkManager struct {
	name2id             map[string]int
	backboneNsHandle    netns.NsHandle
	backboneNsHandleOk  int
	id2handle           []netns.NsHandle
	id2handleOk         []int
	setupInternalTime   time.Duration
	setupExternalTime   time.Duration
	setupBrTime         time.Duration
	setupVethTime       time.Duration
	setupVxlanTime      time.Duration
	destroyInternalTime time.Duration
	destroyExternalTime time.Duration
	destroyBrTime       time.Duration
	destroyVethTime     time.Duration
	destroyVxlanTime    time.Duration
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) SetupBackboneNetns() error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "add", "itl_test_bb")
	// fmt.Printf("SetupNodeCommand: %v\n", SetupNodeCommand)
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	return nil
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) DestroyBackboneNetns() error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "del", "itl_test_bb")
	// fmt.Printf("SetupNodeCommand: %v\n", SetupNodeCommand)
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	return nil
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) Init() error {
	ntlm.name2id = make(map[string]int)
	ntlm.id2handle = make([]netns.NsHandle, 65536)
	ntlm.id2handleOk = make([]int, 65536)
	return nil
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) Delete() error {
	fmt.Printf("Setup Internal link time: %.2fs\n", ntlm.setupInternalTime.Seconds())
	fmt.Printf("Setup External link time: %.2fs\n", ntlm.setupExternalTime.Seconds())
	fmt.Printf("Setup Br time: %.2fs\n", ntlm.setupBrTime.Seconds())
	fmt.Printf("Setup Veth time: %.2fs\n", ntlm.setupVethTime.Seconds())
	fmt.Printf("Setup Vxlan time: %.2fs\n", ntlm.setupVxlanTime.Seconds())
	fmt.Printf("Destroy Internal link time: %.2fs\n", ntlm.destroyInternalTime.Seconds())
	fmt.Printf("Destroy External link time: %.2fs\n", ntlm.destroyExternalTime.Seconds())
	fmt.Printf("Destroy Br time: %.2fs\n", ntlm.destroyBrTime.Seconds())
	fmt.Printf("Destroy Veth time: %.2fs\n", ntlm.destroyVethTime.Seconds())
	fmt.Printf("Destroy Vxlan time: %.2fs\n", ntlm.destroyVxlanTime.Seconds())
	return nil
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) SetupNode(nodeId int) error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "add", "itl_test"+strconv.Itoa(nodeId))
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	return nil
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) DestroyNode(nodeId int) error {
	DestroyNodeCommand := exec.Command(
		"ip", "netns", "del", "itl_test"+strconv.Itoa(nodeId))
	DestroyNodeCommand.Stdout = os.Stdout
	DestroyNodeCommand.Run()
	return nil
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) SetupLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	startTime := time.Now()
	if vxlanID == -1 {
		err = ntlm.SetupInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
		setupTime := time.Since(startTime)
		ntlm.setupInternalTime += setupTime
	} else {
		err = ntlm.SetupExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
		setupTime := time.Since(startTime)
		ntlm.setupExternalTime += setupTime
	}
	return err
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) DestroyLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	startTime := time.Now()
	if vxlanID == -1 {
		err = ntlm.DestroyInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
		destroyTime := time.Since(startTime)
		ntlm.destroyInternalTime += destroyTime
	} else {
		err = ntlm.DestroyExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
		destroyTime := time.Since(startTime)
		ntlm.destroyExternalTime += destroyTime
	}
	return err
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) SetupInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var hostNetns, backboneNs, nodeiNetNs, nodejNetNs netns.NsHandle
	var brName string
	var startTime time.Time
	var setupTime time.Duration

	/* Prepare network namespace handles */
	hostNetns, err = netns.Get()
	if err != nil {
		return fmt.Errorf("failed to netns.Get: %s", err)
	}
	backboneNs, err = ntlm.getBackBoneNsHandle()
	if err != nil {
		return err
	}
	nodeiNetNs, err = ntlm.getNsHandle(nodeIdi)
	if err != nil {
		return err
	}
	nodejNetNs, err = ntlm.getNsHandle(nodeIdj)
	if err != nil {
		return err
	}

	/* Switch to backbone's NetNs */
	err = netns.Set(backboneNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set 1: %s", err)
	}

	/* Create a bridge and two veth pairs */
	startTime = time.Now()
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
	setupTime = time.Since(startTime)
	ntlm.setupBrTime += setupTime
	startTime = time.Now()
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
	setupTime = time.Since(startTime)
	ntlm.setupVethTime += setupTime

	/* Set the other sides of veths up */
	startTime = time.Now()
	var vethIni, vethInj netlink.Link
	err = netns.Set(nodeiNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set 2: %s", err)
	}
	vethIni, err = netlink.LinkByName(
		"eth" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", "eth"+strconv.Itoa(nodeIdj), err)
	}
	err = netlink.LinkSetUp(vethIni)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}
	err = netns.Set(nodejNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set 3: %s", err)
	}
	vethInj, err = netlink.LinkByName(
		"eth" + strconv.Itoa(nodeIdi))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", "eth"+strconv.Itoa(nodeIdi), err)
	}
	err = netlink.LinkSetUp(vethInj)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}
	setupTime = time.Since(startTime)
	ntlm.setupVethTime += setupTime

	/* Set NetNs Back */
	err = netns.Set(hostNetns)
	if err != nil {
		return fmt.Errorf("failed to netns.Set 4: %s", err)
	}
	return err
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) DestroyInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var hostNetns, backboneNs netns.NsHandle
	var brName string
	var startTime time.Time
	var destroyTime time.Duration

	/* Prepare network namespace handles */
	hostNetns, err = netns.Get()
	if err != nil {
		return fmt.Errorf("failed to netns.Get: %s", err)
	}
	backboneNs, err = ntlm.getBackBoneNsHandle()
	if err != nil {
		return err
	}

	/* Switch to backbone's NetNs */
	err = netns.Set(backboneNs)
	if err != nil {
		fmt.Printf("%v\n", backboneNs)
		return fmt.Errorf("failed to netns.Set 5: %s", err)
	}

	/* Remove the bridge */
	startTime = time.Now()
	if nodeIdi < nodeIdj {
		brName = "br-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj)
	} else {
		brName = "br-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi)
	}
	br, err := netlink.LinkByName(brName)
	if err != nil {
		return fmt.Errorf("failed to LinkByName br: %s: %s", brName, err)
	}
	err = netlink.LinkDel(br)
	if err != nil {
		return fmt.Errorf("failed to delete br: %s", err)
	}
	destroyTime = time.Since(startTime)
	ntlm.destroyBrTime += destroyTime

	/* Remove two veth pairs */
	startTime = time.Now()
	vethi, err := netlink.LinkByName(
		"eth-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName vethi: %s: %s",
			"eth-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj), err)
	}
	err = netlink.LinkDel(vethi)
	if err != nil {
		return fmt.Errorf("failed to delete vethi: %s", err)
	}
	vethj, err := netlink.LinkByName(
		"eth-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi))
	if err != nil {
		return fmt.Errorf("failed to LinkByName vethj: %s: %s",
			"eth-"+strconv.Itoa(nodeIdj)+"-"+strconv.Itoa(nodeIdi), err)
	}
	err = netlink.LinkDel(vethj)
	if err != nil {
		return fmt.Errorf("failed to delete vethj: %s", err)
	}
	destroyTime = time.Since(startTime)
	ntlm.destroyVethTime += destroyTime

	/* Set NetNs Back */
	err = netns.Set(hostNetns)
	if err != nil {
		return fmt.Errorf("failed to netns.Set 6: %s", err)
	}
	return err
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) SetupExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var hostNetns, backboneNs, nodeiNetNs netns.NsHandle
	var brName string
	var startTime time.Time
	var setupTime time.Duration

	/* Prepare network namespace handles */
	hostNetns, err = netns.Get()
	if err != nil {
		return fmt.Errorf("failed to netns.Get: %s", err)
	}
	backboneNs, err = ntlm.getBackBoneNsHandle()
	if err != nil {
		return err
	}
	nodeiNetNs, err = ntlm.getNsHandle(nodeIdi)
	if err != nil {
		return err
	}

	/* Create Vxlan */
	startTime = time.Now()
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
	setupTime = time.Since(startTime)
	ntlm.setupVxlanTime += setupTime

	/* Switch to backbone's NetNs */
	err = netns.Set(backboneNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set 7: %s", err)
	}

	/* Create bridge and a veth pair */
	startTime = time.Now()
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
	setupTime = time.Since(startTime)
	ntlm.setupBrTime += setupTime
	startTime = time.Now()
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
	setupTime = time.Since(startTime)
	ntlm.setupVethTime += setupTime

	/* Set Vxlan master and set Vxlan up */
	startTime = time.Now()
	var newVxlan netlink.Link
	newVxlan, err = netlink.LinkByName("vxl-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName newVxlan: %s", err)
	}
	err = netlink.LinkSetMaster(newVxlan, br)
	if err != nil {
		return fmt.Errorf("failed to LinkSetMaster (%d, %d, %d, %s, %v): %s", nodeIdi, nodeIdj, vxlanID, brName, br, err)
	}
	err = netlink.LinkSetUp(newVxlan)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}
	setupTime = time.Since(startTime)
	ntlm.setupVxlanTime += setupTime

	/* Set the other side of veth up */
	startTime = time.Now()
	var vethIni netlink.Link
	err = netns.Set(nodeiNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set 8: %s", err)
	}
	vethIni, err = netlink.LinkByName(
		"eth" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", "eth"+strconv.Itoa(nodeIdj), err)
	}
	err = netlink.LinkSetUp(vethIni)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}
	setupTime = time.Since(startTime)
	ntlm.setupVethTime += setupTime

	/* Set NetNs Back */
	err = netns.Set(hostNetns)
	if err != nil {
		return fmt.Errorf("failed to netns.Set 9: %s", err)
	}
	return err
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) DestroyExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var hostNetns, backboneNs netns.NsHandle
	var brName string
	var startTime time.Time
	var destroyTime time.Duration

	/* Prepare network namespace handles */
	hostNetns, err = netns.Get()
	if err != nil {
		return fmt.Errorf("failed to netns.Get: %s", err)
	}
	backboneNs, err = ntlm.getBackBoneNsHandle()
	if err != nil {
		return err
	}

	/* Switch to backbone's NetNs */
	err = netns.Set(backboneNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set 10: %s", err)
	}

	/* Remove the bridge */
	startTime = time.Now()
	if nodeIdi < nodeIdj {
		brName = "br-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj)
	} else {
		brName = "br-" + strconv.Itoa(nodeIdj) + "-" + strconv.Itoa(nodeIdi)
	}
	br, err := netlink.LinkByName(brName)
	if err != nil {
		return fmt.Errorf("failed to LinkByName br: %s: %s", brName, err)
	}
	err = netlink.LinkDel(br)
	if err != nil {
		return fmt.Errorf("failed to delete br: %s", err)
	}
	destroyTime = time.Since(startTime)
	ntlm.destroyBrTime += destroyTime

	/* Remove the veth pair */
	startTime = time.Now()
	vethi, err := netlink.LinkByName(
		"eth-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName vethi: %s: %s",
			"eth-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj), err)
	}
	err = netlink.LinkDel(vethi)
	if err != nil {
		return fmt.Errorf("failed to delete vethi: %s", err)
	}
	destroyTime = time.Since(startTime)
	ntlm.destroyVethTime += destroyTime

	/* Remove the vxlan */
	startTime = time.Now()
	vxlan, err := netlink.LinkByName(
		"vxl-" + strconv.Itoa(nodeIdi) + "-" + strconv.Itoa(nodeIdj))
	if err != nil {
		return fmt.Errorf("failed to LinkByName vxlan: %s: %s",
			"vxl-"+strconv.Itoa(nodeIdi)+"-"+strconv.Itoa(nodeIdj), err)
	}
	err = netlink.LinkDel(vxlan)
	if err != nil {
		return fmt.Errorf("failed to delete vxlan: %s", err)
	}
	destroyTime = time.Since(startTime)
	ntlm.destroyVxlanTime += destroyTime

	/* Set NetNs Back */
	err = netns.Set(hostNetns)
	if err != nil {
		return fmt.Errorf("failed to netns.Set 11: %s", err)
	}
	return err
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) getNsHandle(nsIndex int) (netns.NsHandle, error) {
	var err error
	nsHandle := ntlm.id2handle[nsIndex]
	nsHandleOk := ntlm.id2handleOk[nsIndex]
	if nsHandleOk == 0 {
		nsHandle, err = netns.GetFromName("itl_test" + strconv.Itoa(nsIndex))
		if err != nil {
			return 0, fmt.Errorf("failed to netns.GetFromName %s: %s", nsHandle, err)
		}
		ntlm.id2handle[nsIndex] = nsHandle
		ntlm.id2handleOk[nsIndex] = 1
	}
	return nsHandle, nil
}

func (ntlm *NetlinkBridgeNsIndexNetworkManager) getBackBoneNsHandle() (netns.NsHandle, error) {
	var err error
	if ntlm.backboneNsHandleOk == 0 {
		ntlm.backboneNsHandle, err = netns.GetFromName("itl_test_bb")
		if err != nil {
			return 0, fmt.Errorf("failed to GetFromName for backbone ns: %s", err)
		}
		ntlm.backboneNsHandleOk = 1
	}
	return ntlm.backboneNsHandle, nil
}
