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

type NetlinkPassthroughNetworkManager struct {
	name2handle map[string]netns.NsHandle
}

func (ntlm *NetlinkPassthroughNetworkManager) Init() error {
	ntlm.name2handle = make(map[string]netns.NsHandle)
	return nil
}

func (ntlm *NetlinkPassthroughNetworkManager) Delete() error {
	return nil
}

func (ntlm *NetlinkPassthroughNetworkManager) SetupNode(nodeId int) error {
	SetupNodeCommand := exec.Command(
		"ip", "netns", "add", "itl_test"+strconv.Itoa(nodeId))
	// fmt.Printf("SetupNodeCommand: %v\n", SetupNodeCommand)
	SetupNodeCommand.Stdout = os.Stdout
	SetupNodeCommand.Run()
	return nil
}

func (ntlm *NetlinkPassthroughNetworkManager) DestroyNode(nodeId int) error {
	DestroyNodeCommand := exec.Command(
		"ip", "netns", "del", "itl_test"+strconv.Itoa(nodeId))
	// fmt.Printf("DestroyNodeCommand: %v\n", DestroyNodeCommand)
	DestroyNodeCommand.Stdout = os.Stdout
	DestroyNodeCommand.Run()
	return nil
}

func (ntlm *NetlinkPassthroughNetworkManager) SetupLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	if vxlanID == -1 {
		err = ntlm.SetupInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	} else {
		err = ntlm.SetupExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	}
	return err
}

func (ntlm *NetlinkPassthroughNetworkManager) DestroyLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	if vxlanID == -1 {
		err = ntlm.DestroyInternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	} else {
		err = ntlm.DestroyExternalLink(nodeIdi, nodeIdj, serverID, vxlanID)
	}
	return err
}

func (ntlm *NetlinkPassthroughNetworkManager) SetupInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var hostNetns, nodeiNetNs, nodejNetNs netns.NsHandle

	hostNetns, err = netns.Get()
	if err != nil {
		return fmt.Errorf("failed to netns.Get: %s", err)
	}

	/* Switch to the node's NetNs */
	nodeiNetNs, err = ntlm.getNsHandle("itl_test" + strconv.Itoa(nodeIdi))
	if err != nil {
		return err
	}
	err = netns.Set(nodeiNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	nodejNetNs, err = ntlm.getNsHandle("itl_test" + strconv.Itoa(nodeIdj))
	if err != nil {
		return err
	}

	/* Create Veth Peer */
	vethi := &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{
			Name:  "eth" + strconv.Itoa(nodeIdj),
			MTU:   1450,
			Flags: net.FlagUp,
		},
		PeerName:      "eth" + strconv.Itoa(nodeIdi),
		PeerNamespace: netlink.NsFd(nodejNetNs),
	}
	err = netlink.LinkAdd(vethi)
	if err != nil {
		return fmt.Errorf("failed to create VethPeer: %s", err)
	}

	/* Set the other side of veth up */
	err = netns.Set(nodejNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
	}
	var vethj netlink.Link
	vethj, err = netlink.LinkByName(
		"eth" + strconv.Itoa(nodeIdi))
	if err != nil {
		return fmt.Errorf("failed to LinkByName: %s: %s", vethj, err)
	}
	err = netlink.LinkSetUp(vethj)
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

func (ntlm *NetlinkPassthroughNetworkManager) DestroyInternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	// var hostNetns, nodeiNetNs netns.NsHandle

	// hostNetns, err = netns.Get()
	// if err != nil {
	// 	return fmt.Errorf("failed to netns.Get: %s", err)
	// }

	// /* Switch to Node's NetNs and destroy veth */
	// nodeiNetNs, err = ntlm.getNsHandle("itl_test" + strconv.Itoa(nodeIdi))
	// if err != nil {
	// 	return err
	// }
	// if !ok {
	// 	return fmt.Errorf("failed to netns.GetFromName %s: %s", nodeiNetNs, err)
	// }
	// err = netns.Set(nodeiNetNs)
	// if err != nil {
	// 	return fmt.Errorf("failed to netns.Set: %s", err)
	// }
	// veth, err := netlink.LinkByName("eth" + strconv.Itoa(nodeIdj))
	// if err != nil {
	// 	return fmt.Errorf("failed to LinkByName: %s: %s", veth, err)
	// }
	// err = netlink.LinkDel(veth)
	// if err != nil {
	// 	return fmt.Errorf("failed to delete veth: %s", err)
	// }

	// /* Set NetNs Back */
	// err = netns.Set(hostNetns)
	// if err != nil {
	// 	return fmt.Errorf("failed to netns.Set: %s", err)
	// }
	return err
}

func (ntlm *NetlinkPassthroughNetworkManager) SetupExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	var hostNetns, nodeiNetNs netns.NsHandle

	hostNetns, err = netns.Get()
	if err != nil {
		return fmt.Errorf("failed to netns.Get: %s", err)
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
	nodeiNetNs, err = ntlm.getNsHandle("itl_test" + strconv.Itoa(nodeIdi))
	if err != nil {
		return err
	}
	err = netlink.LinkSetNsFd(vxlan, int(nodeiNetNs))
	if err != nil {
		return fmt.Errorf("failed to link set nsfd: %s", err)
	}

	/* Switch to Node's NetNs and set Vxlan up */
	err = netns.Set(nodeiNetNs)
	if err != nil {
		return fmt.Errorf("failed to netns.Set: %s", err)
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

func (ntlm *NetlinkPassthroughNetworkManager) DestroyExternalLink(nodeIdi int, nodeIdj int, serverID int, vxlanID int) error {
	var err error
	// var hostNetns, nodeiNetNs netns.NsHandle

	// hostNetns, err = netns.Get()
	// if err != nil {
	// 	return fmt.Errorf("failed to netns.Get: %s", err)
	// }

	// /* Switch to Node's NetNs and destroy veth */
	// nodeiNetNs, err = ntlm.getNsHandle("itl_test" + strconv.Itoa(nodeIdi))
	// if err != nil {
	// 	return err
	// }
	// err = netns.Set(nodeiNetNs)
	// if err != nil {
	// 	return fmt.Errorf("failed to netns.Set: %s", err)
	// }
	// vxlan, err := netlink.LinkByName("eth" + strconv.Itoa(nodeIdj))
	// if err != nil {
	// 	return fmt.Errorf("failed to LinkByName: %s: %s", vxlan, err)
	// }
	// err = netlink.LinkDel(vxlan)
	// if err != nil {
	// 	return fmt.Errorf("failed to delete vxlan: %s", err)
	// }

	// /* Set NetNs Back */
	// err = netns.Set(hostNetns)
	// if err != nil {
	// 	return fmt.Errorf("failed to netns.Set: %s", err)
	// }
	return err
}

func (ntlm *NetlinkPassthroughNetworkManager) getNsHandle(nsName string) (netns.NsHandle, error) {
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
