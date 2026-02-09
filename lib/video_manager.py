import asyncio
import time
from prettytable import PrettyTable
from utils.logger import logger
from utils.pi_health_check import health_worker
from utils.router_health import get_router_health

async def run_cmd(cmd, suppress_output=False, live_output=False):
    """
    Run command with optional live output display
    """
    if live_output:
        # Create process with PIPE for live output
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout_lines = []
        stderr_lines = []
        
        async def read_stream(stream, lines_list, prefix=""):
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded_line = line.decode().rstrip()
                lines_list.append(decoded_line)
                
        await asyncio.gather(
            read_stream(proc.stdout, stdout_lines, ""),
            read_stream(proc.stderr, stderr_lines, "")
        )
        
        await proc.wait()
        
        return {
            "returncode": proc.returncode,
            "stdout": "\n".join(stdout_lines),
            "stderr": "\n".join(stderr_lines),
        }
    else:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=(
                asyncio.subprocess.DEVNULL if suppress_output else asyncio.subprocess.PIPE
            ),
            stderr=(
                asyncio.subprocess.DEVNULL if suppress_output else asyncio.subprocess.PIPE
            ),
        )
        stdout, stderr = await proc.communicate()
        return {
            "returncode": proc.returncode,
            "stdout": None if suppress_output else stdout.decode(),
            "stderr": None if suppress_output else stderr.decode(),
        }

class VideoManager:
    def __init__(self, video_ids, duration):
        self.video_ids = video_ids
        self.duration = duration

    async def check_network_activity(self, ns):
        """Check if there's network activity in the namespace"""
        # Get initial network stats
        cmd = f"sudo ip netns exec {ns} cat /proc/net/dev"
        result = await run_cmd(cmd)
        
        if result["returncode"] != 0:
            return {"active": False, "error": "Could not read network stats"}
        
        initial_stats = result["stdout"]
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Get stats again
        result = await run_cmd(cmd)
        final_stats = result["stdout"]
        
        # Parse and compare (simple check - if output changed, there's activity)
        return {
            "active": initial_stats != final_stats,
            "initial": initial_stats,
            "final": final_stats
        }

    async def get_bandwidth_usage(self, ns):
        """Get real-time bandwidth usage for namespace"""
        cmd = f"sudo ip netns exec {ns} cat /proc/net/dev | grep -E 'eth0|wlan0|veth'"
        result = await run_cmd(cmd)
        
        if result["returncode"] != 0:
            return None
        
        # Parse the output to get bytes received
        lines = result["stdout"].strip().split('\n')
        total_bytes = 0
        
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        # Received bytes is typically the second column
                        total_bytes += int(parts[1])
                    except (ValueError, IndexError):
                        pass
        
        return total_bytes

    async def check_processes(self, ns):
        """Check if yt-dlp and mpv processes are running in namespace"""
        # Check for yt-dlp
        cmd_ytdlp = f"sudo ip netns exec {ns} pgrep -f yt-dlp"
        result_ytdlp = await run_cmd(cmd_ytdlp)
        
        # Check for mpv
        cmd_mpv = f"sudo ip netns exec {ns} pgrep -f mpv"
        result_mpv = await run_cmd(cmd_mpv)
        
        return {
            "yt-dlp_running": result_ytdlp["returncode"] == 0,
            "mpv_running": result_mpv["returncode"] == 0,
            "yt-dlp_pids": result_ytdlp["stdout"].strip() if result_ytdlp["returncode"] == 0 else "",
            "mpv_pids": result_mpv["stdout"].strip() if result_mpv["returncode"] == 0 else ""
        }

    async def verify_streaming(self, ns):
        """Comprehensive verification that streaming is actually happening"""
        verification_results = {
            "namespace": ns,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "processes": {},
            "network_activity": {},
            "bandwidth": {}
        }
        
        # Check processes
        process_check = await self.check_processes(ns)
        verification_results["processes"] = process_check
        
        # Check network activity
        network_check = await self.check_network_activity(ns)
        verification_results["network_activity"] = network_check
        
        # Get initial bandwidth
        initial_bandwidth = await self.get_bandwidth_usage(ns)
        await asyncio.sleep(3)
        final_bandwidth = await self.get_bandwidth_usage(ns)
        
        if initial_bandwidth is not None and final_bandwidth is not None:
            bytes_transferred = final_bandwidth - initial_bandwidth
            verification_results["bandwidth"] = {
                "initial_bytes": initial_bandwidth,
                "final_bytes": final_bandwidth,
                "bytes_transferred": bytes_transferred,
                "transfer_rate_kbps": (bytes_transferred / 3) / 1024  # KB/s
            }
        
        # Overall verdict
        is_streaming = (
            process_check.get("yt-dlp_running", False) or 
            process_check.get("mpv_running", False)
        ) and network_check.get("active", False)
        
        verification_results["is_streaming"] = is_streaming
        
        return verification_results

    def parse_streaming_info(self, stdout, stderr):
        """Extract useful information from streaming output"""
        info = {
            "video_id": "N/A",
            "format": "N/A",
            "resolution": "N/A",
            "file_size": "N/A",
            "download_speed": "N/A",
            "duration": "N/A",
            "audio_info": "N/A"
        }
        
        combined_output = stdout + "\n" + stderr
        
        for line in combined_output.split('\n'):
            # Extract video ID
            if "Extracting URL:" in line or "youtube]" in line:
                if "WWVBodD_BrM" in line:
                    info["video_id"] = "WWVBodD_BrM"
            
            # Extract format info
            if "Downloading 1 format(s):" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    info["format"] = parts[1].strip()
            
            # Extract resolution
            if "Video --vid=" in line:
                if "h264" in line:
                    # Extract resolution like "640x360"
                    import re
                    match = re.search(r'(\d+x\d+)', line)
                    if match:
                        info["resolution"] = match.group(1)
            
            # Extract file size
            if "of" in line and "MiB" in line:
                import re
                match = re.search(r'of\s+([\d.]+\s*[MG]iB)', line)
                if match:
                    info["file_size"] = match.group(1).strip()
            
            # Extract download speed
            if "at" in line and "/s" in line:
                import re
                match = re.search(r'at\s+([\d.]+\s*[MKG]iB/s)', line)
                if match:
                    info["download_speed"] = match.group(1).strip()
            
            # Extract duration
            if "A:" in line and "/" in line:
                import re
                match = re.search(r'A:\s*(\d{2}:\d{2}:\d{2})\s*/\s*(\d{2}:\d{2}:\d{2})', line)
                if match:
                    info["duration"] = match.group(2)
            
            # Extract audio info
            if "Audio --aid=" in line:
                import re
                match = re.search(r'\((\w+\s+\w+\s+\d+Hz)\)', line)
                if match:
                    info["audio_info"] = match.group(1)
        
        return info

    async def _stream_with_mpv(self, ns, video_id):
        start_time = time.time()
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Starting stream for namespace: {ns}")
        logger.info(f"{'='*80}\n")
        
        cmd = (
            f'sudo ip netns exec {ns} env HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= '
            f'PATH=/usr/local/bin:/usr/bin:/bin HOME=/home/blueplanet '
            f'/usr/local/bin/yt-dlp -o - "https://www.youtube.com/watch?v=WWVBodD_BrM" | '
            f'sudo ip netns exec {ns} /usr/bin/mpv --no-video --ao=null -'
        )
        
        result = await run_cmd(cmd, live_output=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        is_success = result["returncode"] in [0, 124]
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Stream completed for namespace: {ns}")
        logger.info(f"Status: {'SUCCESS' if is_success else 'FAILED'}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"{'='*80}\n")
        
        if not is_success:
            logger.error(
                f"[ERROR] {ns} stream failed. Code: {result['returncode']}"
            )
        
        
        final_verification = await self.verify_streaming(ns)
        
        streaming_info = self.parse_streaming_info(result["stdout"], result["stderr"])
        
        return {
            "success": is_success,
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "duration": duration,
            "verification": final_verification,
            "bandwidth_used": final_verification["bandwidth"].get("bytes_transferred", 0) if final_verification["bandwidth"] else 0,
            "streaming_info": streaming_info
        }

    def display_results_table(self, results):
        """Display streaming results in a formatted table"""
        table = PrettyTable()
        table.field_names = ["Namespace", "Status", "Duration (s)", "File Size", "Speed", "Resolution", "Audio", "Return Code"]
        
        success_count = 0
        failed_count = 0
        
        for ns, result in results.items():
            status = "✓ SUCCESS" if result["success"] else "✗ FAILED"
            returncode = result["returncode"]
            duration = f"{result.get('duration', 0):.2f}"
            
            # Get streaming info
            info = result.get('streaming_info', {})
            file_size = info.get('file_size', 'N/A')
            speed = info.get('download_speed', 'N/A')
            resolution = info.get('resolution', 'N/A')
            audio = info.get('audio_info', 'N/A')
            
            if result["success"]:
                success_count += 1
            else:
                failed_count += 1
            
            table.add_row([ns, status, duration, file_size, speed, resolution, audio, returncode])
        
        # Alignment
        table.align["Namespace"] = "l"
        table.align["Status"] = "c"
        table.align["Duration (s)"] = "r"
        table.align["File Size"] = "r"
        table.align["Speed"] = "r"
        table.align["Resolution"] = "c"
        table.align["Audio"] = "l"
        table.align["Return Code"] = "c"
        
        logger.info("\n" + "="*130)
        logger.info("STREAMING RESULTS SUMMARY")
        logger.info("="*130)
        logger.info(table)
        logger.info("="*130)
        logger.info(f"Total Namespaces: {len(results)} | Success: {success_count} | Failed: {failed_count} | Success Rate: {(success_count/len(results)*100):.2f}%")
        logger.info("="*130 + "\n")

    async def start_parallel_streaming(self, namespaces):
        stop_event_pi = asyncio.Event()
        stop_event_router = asyncio.Event()
        
        tasks = [
            self._stream_with_mpv(ns, self.video_ids[i % len(self.video_ids)])
            for i, ns in enumerate(namespaces)
        ]
        
        pi_task = asyncio.create_task(health_worker(stop_event_pi))
        router_task = asyncio.create_task(get_router_health(stop_event_router))
        
        results_list = await asyncio.gather(*tasks)
        
        stop_event_pi.set()
        stop_event_router.set()
        await pi_task
        await router_task
        
        results = {ns: res for ns, res in zip(namespaces, results_list)}
    
        self.display_results_table(results)
        
        return results