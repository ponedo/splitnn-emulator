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

type NtlBrLinkManager struct {
	curBackBoneNum int
	curlinkNum     int
	curBackBoneNs  netns.NsHandle
	hostNetns      netns.NsHandle
	nm             NodeManager
}

func (lm *NtlBrLinkManager) Init(nm NodeManager) error {
	var err error

	lm.curBackBoneNum = 0
	lm.curlinkNum = 0
	lm.nm = nm
	lm.curBackBoneNs = -1
	lm.hostNetns, err = netns.Get()
	if err != nil {
		return err
	}
	return nil
}

func (lm *NtlBrLinkManager) Delete() error {
	lm.hostNetns.Close()
	return nil
}

func (lm *NtlBrLinkManager) SetupAndEnterBbNs() error {
	bbnsName := "bbns" + strconv.Itoa(lm.curBackBoneNum)
	backboneNsHandle, err := netns.NewNamed(bbnsName)
	if err != nil {
		fmt.Printf("failed to netns.NewNamed %s: %s\n", bbnsName, err)
		return err
	}
	lm.curBackBoneNum += 1

	err = netns.Set(backboneNsHandle)
	if err != nil {
		fmt.Printf("failed to netns.Set for bbns: %s\n", err)
		return err
	}

	if DisableIpv6 == 1 {
		err = DisableIpv6ForCurNetns()
		if err != nil {
			fmt.Printf("failed to DisableIpv6 for current Netns: %s\n", err)
			return err
		}
	}

	if lm.curBackBoneNs != -1 {
		lm.curBackBoneNs.Close()
	}
	lm.curBackBoneNs = backboneNsHandle
	return nil
}

func (lm *NtlBrLinkManager) CleanAllBbNs() error {
	var err error
	var start, end time.Time

	start = time.Now()

	/* Destroy all netns */
	destroyCommand := exec.Command(
		"ip", "-all", "netns", "del")
	destroyCommand.Stdout = os.Stdout
	destroyCommand.Run()

	/* Use multiple "ip link add test-link" to probe whether rtnl_lock is released by netns deletion */
	testTime := 50
	probeLink := &netlink.Dummy{
		LinkAttrs: netlink.LinkAttrs{
			Name: "probe-dummy",
		},
	}
	time.Sleep(2 * time.Second)
	for i := 0; i < testTime; i += 1 {
		err = netlink.LinkAdd(probeLink)
		if err != nil {
			fmt.Printf("failed to LinkAdd at : %s", err)
			return err
		}
		err = netlink.LinkDel(probeLink)
		if err != nil {
			fmt.Printf("failed to LinkDel: %s", err)
			return err
		}
		end = time.Now()
		fmt.Printf("Probe %d time: %dms\n", i, end.Sub(start).Milliseconds())
	}
	end = time.Now()
	fmt.Printf("Clean link time: %dms\n", end.Sub(start).Milliseconds())

	return nil
}

/* Before calling SetupLink, current network namespace must be backbone namespace */
func (lm *NtlBrLinkManager) SetupLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	if vxlanID == -1 {
		err = lm.SetupInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	} else {
		err = lm.SetupExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	}
	lm.curlinkNum += 1
	return err
}

/* Before calling SetupInternalLink, current network namespace must be backbone namespace */
func (lm *NtlBrLinkManager) SetupInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var backboneNs, nodeiNetNs, nodejNetNs netns.NsHandle
	var brName string

	/* Prepare network namespace handles */
	backboneNs = lm.curBackBoneNs
	nodeiNetNs, err = lm.nm.GetNodeNetNs(nodeIdi)
	if err != nil {
		return fmt.Errorf("failed to GetNodeNetNs: %s", err)
	}
	defer nodeiNetNs.Close()
	nodejNetNs, err = lm.nm.GetNodeNetNs(nodeIdj)
	if err != nil {
		return fmt.Errorf("failed to GetNodeNetNs: %s", err)
	}
	defer nodejNetNs.Close()

	/* Prepare other data structure */
	brName = "br-" + strconv.Itoa(lm.curlinkNum)
	vethNamei := "eth-" + strconv.Itoa(lm.curlinkNum) + "-i"
	vethNamej := "eth-" + strconv.Itoa(lm.curlinkNum) + "-j"
	br := &netlink.Bridge{
		LinkAttrs: netlink.LinkAttrs{
			Name:  brName,
			MTU:   1450,
			Flags: net.FlagUp,
		},
	}
	vethOuti := &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{
			Name:  vethNamei,
			MTU:   1450,
			Flags: net.FlagUp,
			// MasterIndex: br.Index,
		},
		PeerName:      vethNamei,
		PeerNamespace: netlink.NsFd(nodeiNetNs),
	}
	vethOutj := &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{
			Name:  vethNamej,
			MTU:   1450,
			Flags: net.FlagUp,
			// MasterIndex: br.Index,
		},
		PeerName:      vethNamej,
		PeerNamespace: netlink.NsFd(nodejNetNs),
	}
	vethIni := &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{
			Name: vethNamei,
		},
	}
	vethInj := &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{
			Name: vethNamej,
		},
	}

	/* Create a bridge and two veth pairs */
	if err := netlink.LinkAdd(br); err != nil {
		return fmt.Errorf("failed to create bridge: %s", err)
	}
	vethOuti.Attrs().MasterIndex = br.Index
	err = netlink.LinkAdd(vethOuti)
	if err != nil {
		return fmt.Errorf("failed to create veth: %s", err)
	}
	vethOutj.Attrs().MasterIndex = br.Index
	err = netlink.LinkAdd(vethOutj)
	if err != nil {
		return fmt.Errorf("failed to create veth: %s", err)
	}

	/* Set the other sides of veths up */
	err = netns.Set(nodeiNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	err = netlink.LinkSetUp(vethIni)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}
	err = netns.Set(nodejNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	err = netlink.LinkSetUp(vethInj)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}

	/* Set NetNs Back */
	err = netns.Set(backboneNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	return err
}

/* Before calling SetupExternalLink, current network namespace must be backbone namespace */
func (lm *NtlBrLinkManager) SetupExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var backboneNs, nodeiNetNs netns.NsHandle

	/* Prepare network namespace handles */
	backboneNs = lm.curBackBoneNs
	nodeiNetNs, err = lm.nm.GetNodeNetNs(nodeIdi)
	if err != nil {
		return fmt.Errorf("failed to GetNodeNetNs: %s", err)
	}
	defer nodeiNetNs.Close()

	/* Create Vxlan */
	brName := "br-" + strconv.Itoa(lm.curlinkNum)
	vxlanName := "eth-" + strconv.Itoa(lm.curlinkNum) + "-v"
	vethNamei := "vxl-" + strconv.Itoa(lm.curlinkNum)
	br := &netlink.Bridge{
		LinkAttrs: netlink.LinkAttrs{
			Name:  brName,
			MTU:   1450,
			Flags: net.FlagUp,
		},
	}
	vxlanOut := &netlink.Vxlan{
		LinkAttrs: netlink.LinkAttrs{
			Name: vxlanName,
		},
		VxlanId:      vxlanID,
		VtepDevIndex: LocalPhyIntfNl.Attrs().Index,
		Port:         4789,
		Group:        net.ParseIP(ServerList[serverID].IPAddr),
		Learning:     true,
	}
	vxlanIn := &netlink.Vxlan{
		LinkAttrs: netlink.LinkAttrs{
			Name: vxlanName,
		},
	}
	vethOuti := &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{
			Name:  vethNamei,
			MTU:   1450,
			Flags: net.FlagUp,
			// MasterIndex: br.Index,
		},
		PeerName:      vethNamei,
		PeerNamespace: netlink.NsFd(nodeiNetNs),
	}
	vethIni := &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{
			Name: vethNamei,
		},
	}

	/* Create network devices */
	err = netns.Set(lm.hostNetns)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	if err = netlink.LinkAdd(vxlanOut); err != nil {
		return fmt.Errorf("failed to create vxlan interface: %s", err)
	}
	err = netlink.LinkSetNsFd(vxlanOut, int(backboneNs))
	if err != nil {
		return fmt.Errorf("failed to link set nsfd: %s", err)
	}
	err = netns.Set(backboneNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	if err := netlink.LinkAdd(br); err != nil {
		return fmt.Errorf("failed to create bridge: %s", err)
	}
	vethOuti.Attrs().MasterIndex = br.Index
	err = netlink.LinkAdd(vethOuti)
	if err != nil {
		return fmt.Errorf("failed to create VethPeer in nodeiNetNs: %s", err)
	}

	/* Set Vxlan master and set Vxlan up */
	var newVxlan netlink.Link
	err = netlink.LinkSetMaster(vxlanIn, br)
	if err != nil {
		return fmt.Errorf("failed to LinkSetMaster (%d, %d, %d, %s, %v): %s", nodeIdi, nodeIdj, vxlanID, brName, br, err)
	}
	err = netlink.LinkSetUp(newVxlan)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}
	err = netns.Set(nodeiNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	err = netlink.LinkSetUp(vethIni)
	if err != nil {
		return fmt.Errorf("failed to LinkSetUp: %s", err)
	}

	/* Set NetNs Back */
	err = netns.Set(backboneNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	return err
}
