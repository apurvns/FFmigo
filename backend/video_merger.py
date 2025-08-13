import subprocess
import os
import json
import threading
from typing import List, Dict, Tuple, Optional
from . import video_analyzer, ffmpeg_runner

class VideoMerger:
    def __init__(self):
        self.ffmpeg_path = ffmpeg_runner.find_ffmpeg()
        self.ffprobe_path = video_analyzer.find_ffprobe()
    
    def check_video_compatibility(self, video_paths: List[str]) -> Tuple[bool, Dict]:
        """
        Check if multiple videos are compatible for direct concatenation.
        Returns (is_compatible, compatibility_info)
        """
        print(f"[DEBUG] check_video_compatibility called with {len(video_paths)} videos")
        
        if len(video_paths) < 2:
            return True, {"reason": "Single video or no videos"}
        
        # Analyze all videos
        analyses = []
        for i, path in enumerate(video_paths):
            print(f"[DEBUG] Analyzing video {i+1}: {path}")
            analysis = video_analyzer.analyze_video(path)
            if not analysis:
                print(f"[DEBUG] Failed to analyze video {i+1}")
                return False, {"reason": f"Could not analyze {os.path.basename(path)}"}
            analyses.append(analysis)
            print(f"[DEBUG] Video {i+1} analysis complete")
        
        print(f"[DEBUG] All videos analyzed, checking compatibility...")
        
        # Check if all videos have the same specs
        first_video = analyses[0]['video_streams'][0] if analyses[0]['video_streams'] else None
        first_audio = analyses[0]['audio_streams'][0] if analyses[0]['audio_streams'] else None
        
        compatibility_info = {
            "videos": len(video_paths),
            "resolution": f"{first_video['width']}x{first_video['height']}" if first_video else "No video",
            "fps": first_video['frame_rate'] if first_video else None,
            "pixel_format": first_video['pixel_format'] if first_video else None,
            "video_codec": first_video['codec_name'] if first_video else None,
            "audio_sample_rate": first_audio['sample_rate'] if first_audio else None,
            "audio_channels": first_audio['channels'] if first_audio else None,
            "audio_codec": first_audio['codec_name'] if first_audio else None,
            "incompatibilities": []
        }
        
        for i, analysis in enumerate(analyses[1:], 1):
            video_stream = analysis['video_streams'][0] if analysis['video_streams'] else None
            audio_stream = analysis['audio_streams'][0] if analysis['audio_streams'] else None
            
            if not first_video and video_stream:
                compatibility_info["incompatibilities"].append(f"Video {i+1} has video stream but first doesn't")
            elif first_video and not video_stream:
                compatibility_info["incompatibilities"].append(f"Video {i+1} has no video stream but first does")
            elif first_video and video_stream:
                if first_video['width'] != video_stream['width'] or first_video['height'] != video_stream['height']:
                    compatibility_info["incompatibilities"].append(f"Video {i+1} has different resolution: {video_stream['width']}x{video_stream['height']}")
                
                if abs(first_video['frame_rate'] - video_stream['frame_rate']) > 0.1:
                    compatibility_info["incompatibilities"].append(f"Video {i+1} has different frame rate: {video_stream['frame_rate']:.2f}")
                
                if first_video['pixel_format'] != video_stream['pixel_format']:
                    compatibility_info["incompatibilities"].append(f"Video {i+1} has different pixel format: {video_stream['pixel_format']}")
                
                if first_video['codec_name'] != video_stream['codec_name']:
                    compatibility_info["incompatibilities"].append(f"Video {i+1} has different video codec: {video_stream['codec_name']}")
            
            if not first_audio and audio_stream:
                compatibility_info["incompatibilities"].append(f"Video {i+1} has audio stream but first doesn't")
            elif first_audio and not audio_stream:
                compatibility_info["incompatibilities"].append(f"Video {i+1} has no audio stream but first does")
            elif first_audio and audio_stream:
                if first_audio['sample_rate'] != audio_stream['sample_rate']:
                    compatibility_info["incompatibilities"].append(f"Video {i+1} has different audio sample rate: {audio_stream['sample_rate']}")
                
                if first_audio['channels'] != audio_stream['channels']:
                    compatibility_info["incompatibilities"].append(f"Video {i+1} has different audio channels: {audio_stream['channels']}")
                
                if first_audio['codec_name'] != audio_stream['codec_name']:
                    compatibility_info["incompatibilities"].append(f"Video {i+1} has different audio codec: {audio_stream['codec_name']}")
        
        is_compatible = len(compatibility_info["incompatibilities"]) == 0
        print(f"[DEBUG] Compatibility check complete: {is_compatible}")
        return is_compatible, compatibility_info
    
    def merge_videos_compatible(self, video_paths: List[str], output_path: str, progress_callback=None) -> Dict:
        """
        Merge compatible videos using simple concatenation (lossless)
        """
        if not self.ffmpeg_path:
            return {"success": False, "error": "FFmpeg not found"}
        
        # Create a file list for FFmpeg concat demuxer
        file_list_path = output_path + ".txt"
        try:
            with open(file_list_path, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path}'\n")
            
            # Use FFmpeg concat demuxer for lossless concatenation
            cmd = f'{self.ffmpeg_path} -f concat -safe 0 -i "{file_list_path}" -c copy "{output_path}"'
            
            if progress_callback:
                progress_callback(10, "Starting compatible video merge...")
            
            result = ffmpeg_runner.run_ffmpeg_command(cmd, os.path.dirname(output_path))
            
            # Clean up file list
            try:
                os.remove(file_list_path)
            except:
                pass
            
            if progress_callback:
                progress_callback(100, "Merge completed" if result['success'] else "Merge failed")
            
            # If failed, include stderr in the error message
            if not result['success'] and result.get('stderr'):
                result['error'] = result.get('stderr', result.get('error', 'Unknown error'))
            
            return result
            
        except Exception as e:
            # Clean up file list
            try:
                os.remove(file_list_path)
            except:
                pass
            return {"success": False, "error": str(e)}
    
    def merge_videos_incompatible(self, video_paths: List[str], output_path: str, progress_callback=None) -> Dict:
        """
        Merge incompatible videos by normalizing them to common specs
        """
        if not self.ffmpeg_path:
            return {"success": False, "error": "FFmpeg not found"}
        
        # Analyze first video to get target specs
        first_analysis = video_analyzer.analyze_video(video_paths[0])
        if not first_analysis or not first_analysis['video_streams']:
            return {"success": False, "error": "Could not analyze first video"}
        
        first_video = first_analysis['video_streams'][0]
        target_width = first_video['width']
        target_height = first_video['height']
        target_fps = first_video['frame_rate']
        
        # Build complex filter for all videos
        filter_parts = []
        video_inputs = []
        audio_inputs = []
        
        for i, video_path in enumerate(video_paths):
            analysis = video_analyzer.analyze_video(video_path)
            if not analysis:
                return {"success": False, "error": f"Could not analyze video {i+1}"}
            
            video_stream = analysis['video_streams'][0] if analysis['video_streams'] else None
            audio_stream = analysis['audio_streams'][0] if analysis['audio_streams'] else None
            
            # Video processing
            if video_stream:
                video_inputs.append(f"[v{i}]")
                filter_parts.append(
                    f"[{i}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                    f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={target_fps}[v{i}]"
                )
            else:
                # Create black video for videos without video stream
                duration = analysis['format'].get('duration', 10)
                filter_parts.append(
                    f"color=c=black:s={target_width}x{target_height}:r={target_fps}:d={duration}[v{i}]"
                )
                video_inputs.append(f"[v{i}]")
            
            # Audio processing
            if audio_stream:
                audio_inputs.append(f"[a{i}]")
                filter_parts.append(f"[{i}:a]aresample=44100[a{i}]")
            else:
                # Create silent audio for videos without audio stream
                duration = analysis['format'].get('duration', 10)
                filter_parts.append(f"anullsrc=r=44100:cl=stereo:d={duration}[a{i}]")
                audio_inputs.append(f"[a{i}]")
        
        # Concatenate all processed streams
        video_concat = "".join(video_inputs)
        audio_concat = "".join(audio_inputs)
        filter_parts.append(f"{video_concat}concat=n={len(video_paths)}:v=1:a=0[v]")
        filter_parts.append(f"{audio_concat}concat=n={len(video_paths)}:v=0:a=1[a]")
        
        filter_complex = ";".join(filter_parts)
        
        # Build FFmpeg command
        input_args = " ".join([f'-i "{path}"' for path in video_paths])
        cmd = f'{self.ffmpeg_path} {input_args} -filter_complex "{filter_complex}" -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset veryfast -c:a aac -b:a 192k "{output_path}"'
        
        if progress_callback:
            progress_callback(10, "Starting incompatible video merge...")
        
        result = ffmpeg_runner.run_ffmpeg_command(cmd, os.path.dirname(output_path))
        
        if progress_callback:
            progress_callback(100, "Merge completed" if result['success'] else "Merge failed")
        
        # If failed, include stderr in the error message
        if not result['success'] and result.get('stderr'):
            result['error'] = result.get('stderr', result.get('error', 'Unknown error'))
        
        return result
    
    def merge_videos(self, video_paths: List[str], output_path: str, progress_callback=None) -> Dict:
        """
        Main method to merge videos, automatically choosing the best method
        """
        print(f"[DEBUG] merge_videos called with {len(video_paths)} videos")
        print(f"[DEBUG] Output path: {output_path}")
        
        if len(video_paths) == 0:
            return {"success": False, "error": "No videos provided"}
        
        if len(video_paths) == 1:
            # Just copy the single video
            import shutil
            try:
                print(f"[DEBUG] Single video, copying {video_paths[0]} to {output_path}")
                shutil.copy2(video_paths[0], output_path)
                return {"success": True, "method": "copy"}
            except Exception as e:
                print(f"[DEBUG] Copy failed: {e}")
                return {"success": False, "error": str(e)}
        
        # Check compatibility
        if progress_callback:
            print(f"[DEBUG] Calling progress_callback(5)")
            progress_callback(5, "Checking video compatibility...")
        
        print(f"[DEBUG] Checking compatibility...")
        is_compatible, compatibility_info = self.check_video_compatibility(video_paths)
        print(f"[DEBUG] Compatibility result: {is_compatible}")
        print(f"[DEBUG] Compatibility info: {compatibility_info}")
        
        if is_compatible:
            if progress_callback:
                print(f"[DEBUG] Calling progress_callback(8) - compatible")
                progress_callback(8, "Videos are compatible, using lossless merge...")
            print(f"[DEBUG] Using compatible merge method")
            return self.merge_videos_compatible(video_paths, output_path, progress_callback)
        else:
            if progress_callback:
                print(f"[DEBUG] Calling progress_callback(8) - incompatible")
                progress_callback(8, f"Videos are incompatible ({len(compatibility_info['incompatibilities'])} differences), normalizing...")
            print(f"[DEBUG] Using incompatible merge method")
            return self.merge_videos_incompatible(video_paths, output_path, progress_callback) 