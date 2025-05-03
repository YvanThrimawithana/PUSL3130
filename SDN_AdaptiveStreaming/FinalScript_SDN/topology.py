#!/usr/bin/env python

from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch, Host
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import sys
import os
import time
import requests
import threading
from datetime import datetime
from tabulate import tabulate

def query_opendaylight_stats(switch_id='openflow:1', controller_ip='127.0.0.1', controller_port=8181):
    """
    Query OpenDaylight REST API for switch port statistics.
    Returns a list of port statistics or None if the query fails.
    """
    url = f'http://{controller_ip}:{controller_port}/restconf/operational/opendaylight-inventory:nodes/node/{switch_id}'
    headers = {'Accept': 'application/json'}
    try:
        response = requests.get(url, headers=headers, auth=('admin', 'admin'), timeout=5)
        if response.status_code == 200:
            data = response.json()
            ports = data.get('node', [{}])[0].get('node-connector', [])
            stats = []
            for port in ports:
                port_id = port.get('id', 'Unknown')
                port_stats = port.get('opendaylight-port-statistics:flow-capable-node-connector-statistics', {})
                packets_sent = port_stats.get('packets', {}).get('transmitted', 0)
                packets_received = port_stats.get('packets', {}).get('received', 0)
                # Calculate apparent packet loss percentage
                packet_loss_pct = 0.0
                if packets_sent > 0:
                    packet_loss_pct = (packets_sent - packets_received) / packets_sent * 100
                stats.append({
                    'port_id': port_id,
                    'bytes_sent': port_stats.get('bytes', {}).get('transmitted', 0),
                    'bytes_received': port_stats.get('bytes', {}).get('received', 0),
                    'packets_sent': packets_sent,
                    'packets_received': packets_received,
                    'packet_loss_pct': packet_loss_pct,
                    'duration_sec': port_stats.get('duration', {}).get('second', 0)
                })
            return stats
        else:
            info(f'*** Failed to query OpenDaylight: {response.status_code}\n')
            return None
    except requests.RequestException as e:
        info(f'*** Error querying OpenDaylight: {e}\n')
        return None

def save_sdn_stats(stats, output_dir, bandwidth, packet_loss, stats_file=None):
    """
    Save SDN port statistics as a formatted table to a file.
    If stats_file is provided, append to it; otherwise, create a new file.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    if not stats_file:
        stats_file = os.path.join(output_dir, f'sdn_stats_bw_{bandwidth}_loss_{packet_loss}_{timestamp}.txt')
    
    if not stats:
        with open(stats_file, 'a') as f:
            f.write(f'\n[{timestamp}] No SDN statistics available.\n')
        return stats_file
    
    headers = ['Port ID', 'Bytes Sent', 'Bytes Received', 'Packets Sent', 'Packets Received', 'Packet Loss (%)', 'Duration (s)']
    table_data = [
        [s['port_id'], s['bytes_sent'], s['bytes_received'], s['packets_sent'], s['packets_received'], f"{s['packet_loss_pct']:.2f}", s['duration_sec']]
        for s in stats
    ]
    table = tabulate(table_data, headers=headers, tablefmt='grid')
    
    with open(stats_file, 'a') as f:
        f.write(f'\n[{timestamp}] SDN Port Statistics (Bandwidth: {bandwidth} Mbps, Packet Loss: {packet_loss}%)\n')
        f.write(table)
        f.write('\n')
    
    info(f'*** SDN statistics appended to {stats_file} at {timestamp}\n')
    return stats_file

def monitor_sdn_stats(output_dir, bandwidth, packet_loss, interval=5, stop_event=None):
    """
    Periodically query and save SDN statistics until stop_event is set.
    """
    stats_file = None
    while not (stop_event and stop_event.is_set()):
        stats = query_opendaylight_stats()
        stats_file = save_sdn_stats(stats, output_dir, bandwidth, packet_loss, stats_file)
        time.sleep(interval)

def save_video_stats(bandwidth, packet_loss, output_dir):
    """
    Simulate and save DASH.js video streaming statistics (placeholder).
    In a real setup, these would be collected from the DASH.js player logs.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    stats_file = os.path.join(output_dir, f'video_stats_bw_{bandwidth}_loss_{packet_loss}_{timestamp}.txt')
    
    initial_buffering = 1.5 + packet_loss * 0.5
    buffering_events = int(packet_loss * 2)
    avg_buffering_time = 0.8 + packet_loss * 0.3
    avg_bitrate = max(500, 3000 - packet_loss * 50 - (1/bandwidth) * 500)
    representation_switches = int(5 + packet_loss * 3)
    dropped_frames = int(packet_loss * 8)
    
    with open(stats_file, 'w') as f:
        f.write(f'Experiment with {packet_loss}% packet loss and {bandwidth} Mbps bandwidth\n')
        f.write(f'Date: {timestamp}\n\n')
        f.write('Video Performance Metrics:\n')
        f.write(f'- Initial buffering time: {initial_buffering:.2f} seconds\n')
        f.write(f'- Number of buffering events: {buffering_events}\n')
        f.write(f'- Average buffering time: {avg_buffering_time:.2f} seconds\n')
        f.write(f'- Average bitrate: {avg_bitrate:.0f} kbps\n')
        f.write(f'- Representation switches: {representation_switches}\n')
        f.write(f'- Dropped frames: {dropped_frames}\n')
    
    info(f'*** Video statistics saved to {stats_file}\n')

def simple_sdn_network(bandwidth=1, packet_loss=0):
    """
    Create a simple SDN network with configurable bandwidth and packet loss.
    Args:
        bandwidth (float): Link bandwidth in Mbps (e.g., 0.1, 0.25, 0.5, 1, 5)
        packet_loss (float): Packet loss percentage (e.g., 0, 5, 10)
    """
    setLogLevel('info')
    
    # Create output directory for experiment results
    output_dir = os.path.expanduser(f'~/experiments/bw_{bandwidth}_loss_{packet_loss}')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create network
    net = Mininet(controller=RemoteController, switch=OVSSwitch, link=TCLink)
    
    # Add remote controller (OpenDaylight)
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    
    # Add hosts and switch
    h1 = net.addHost('h1', ip='10.0.0.1')
    h2 = net.addHost('h2', ip='10.0.0.2')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    
    # Add links with specified bandwidth, delay, and packet loss
    net.addLink(h1, s1, bw=bandwidth, delay='10ms', loss=packet_loss)
    net.addLink(s1, h2, bw=bandwidth, delay='10ms', loss=packet_loss)
    
    # Start network
    net.start()
    
    # Open xterm on h1 for manual interaction
    info('*** Opening xterm on h1. Enter your commands in the xterm window.\n')
    h1.cmd('xterm &')
    info('*** Press Enter in this terminal to proceed with Apache and Firefox commands.\n')
    input()
    
    # Stop any existing Apache processes on h1
    h1.cmd('killall apache2')
    # Start Apache on h1 using the manual script
    h1.cmd('./start_apache2_manually.sh &')
    
    # Start monitoring SDN statistics in a background thread
    stop_event = threading.Event()
    monitor_thread = threading.Thread(
        target=monitor_sdn_stats,
        args=(output_dir, bandwidth, packet_loss, 5, stop_event)
    )
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Open Firefox on h2 as user 'ytovan'
    h2.cmd('sudo -u ytovan firefox http://10.0.0.1/index.html &')
    
    # Open Mininet CLI for interaction
    info('*** Network is running. Apache started and Firefox opened.\n')
    info('*** Play the video for at least 60 seconds to generate sufficient traffic.\n')
    info('*** SDN statistics are being collected every 5 seconds.\n')
    info('*** Type "exit" in CLI to stop network and save final stats.\n')
    CLI(net)
    
    # Stop SDN monitoring and save final video stats
    stop_event.set()
    monitor_thread.join(timeout=1.0)
    
    # Save simulated video stats (replace with actual DASH.js logs in practice)
    save_video_stats(bandwidth, packet_loss, output_dir)
    
    # Stop network
    net.stop()

if __name__ == '__main__':
    # Get bandwidth and packet loss from command-line arguments
    bandwidth = 1  # Default bandwidth
    packet_loss = 0  # Default packet loss
    
    if len(sys.argv) > 1:
        try:
            bandwidth = float(sys.argv[1])
            if bandwidth <= 0:
                raise ValueError("Bandwidth must be positive")
        except ValueError as e:
            print(f"Error: Invalid bandwidth value '{sys.argv[1]}'. Use a positive number (e.g., 0.1, 1, 5). Defaulting to 1 Mbps.")
            bandwidth = 1
    
    if len(sys.argv) > 2:
        try:
            packet_loss = float(sys.argv[2])
            if packet_loss < 0 or packet_loss > 100:
                raise ValueError("Packet loss must be between 0 and 100")
        except ValueError as e:
            print(f"Error: Invalid packet loss value '{sys.argv[2]}'. Use a number between 0 and 100. Defaulting to 0%.")
            packet_loss = 0
    
    print(f"Starting network with bandwidth: {bandwidth} Mbps, packet loss: {packet_loss}%")
    simple_sdn_network(bandwidth=bandwidth, packet_loss=packet_loss)
