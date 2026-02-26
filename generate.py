import yt_dlp
import time
import random
import re
import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET
from xml.dom import minidom

# ============= CONFIGURATION =============
QUALITY_PROFILES = {
    'hd': {'min_height': 720, 'suffix': '[HD]', 'priority': [1080, 720]},
    'mobile': {'max_height': 480, 'suffix': '[Mobile]', 'priority': [480, 360]},
    'audio': {'format': 'bestaudio', 'suffix': '[Audio]', 'priority': []}
}

# Country mapping for channels (you can customize this)
CHANNEL_COUNTRIES = {
    # Nigerian channels
    'arise': 'NG',
    'channels': 'NG',
    'tvc': 'NG',
    'nta': 'NG',
    'ait': 'NG',
    'silverbird': 'NG',
    'nigerian': 'NG',
    'lagos': 'NG',
    'abuja': 'NG',
    
    # Ghanaian channels
    'ghana': 'GH',
    'joy': 'GH',
    'adom': 'GH',
    'multitv': 'GH',
    'ghone': 'GH',
    'utv': 'GH',
    'atv': 'GH',
    'tv3': 'GH',
    'cititv': 'GH',
    
    # Default
    'default': 'US'  # United States as fallback
}
# =========================================

class YouTubePlaylistGenerator:
    def __init__(self, cookies_file='cookies.txt'):
        self.cookies_file = cookies_file
        self.cache_file = '.channel_cache.json'
        self.logos_dir = 'logos'
        self.channels_dir = 'channels'
        self.load_cache()
        
        # Create directories
        for directory in [self.logos_dir, self.channels_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"📁 Created directory: {directory}/")
    
    def load_cache(self):
        """Load cached channel data"""
        try:
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
        except:
            self.cache = {'channels': {}, 'logos': {}}
    
    def save_cache(self):
        """Save channel data to cache"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)
    
    def safe_filename(self, name):
        """Convert channel name to safe filename"""
        safe = re.sub(r'[^\w\s-]', '', name).strip()
        safe = re.sub(r'[-\s]+', '_', safe)
        return safe.lower()
    
    def detect_channel_country(self, channel_name):
        """Detect which country the channel belongs to based on name"""
        channel_name_lower = channel_name.lower()
        
        for keyword, country in CHANNEL_COUNTRIES.items():
            if keyword in channel_name_lower and keyword != 'default':
                print(f"  🌍 Detected {country} channel: {keyword}")
                return country
        
        return CHANNEL_COUNTRIES['default']
    
    def fetch_channel_logo(self, channel_id, channel_name):
        """Fetch and cache channel logo"""
        logo_path = f"{self.logos_dir}/{channel_id}.jpg"
        
        if os.path.exists(logo_path):
            file_age = time.time() - os.path.getmtime(logo_path)
            if file_age < 604800:  # 7 days
                return logo_path
        
        try:
            qualities = ['maxresdefault', 'sddefault', 'hqdefault', 'mqdefault']
            base_url = "https://i.ytimg.com/vi/{}/{}.jpg"
            
            if channel_id in self.cache['channels']:
                video_id = self.cache['channels'][channel_id].get('video_id')
                if video_id:
                    for quality in qualities:
                        url = base_url.format(video_id, quality)
                        response = requests.head(url, timeout=5)
                        if response.status_code == 200:
                            img_data = requests.get(url, timeout=10).content
                            with open(logo_path, 'wb') as f:
                                f.write(img_data)
                            print(f"  ✅ Logo saved: {quality}")
                            return logo_path
            return None
        except Exception as e:
            print(f"  ⚠️ Logo fetch failed: {str(e)[:50]}")
            return None
    
    def get_stream_info(self, url):
        """Get stream URL and metadata with better live detection and geo-bypass"""
        
        # First, try to get channel name without full extraction to detect country
        try:
            # Quick extraction just for channel name
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(url, download=False, process=False)
                channel_name = info.get('channel', '') if info else ''
        except:
            channel_name = ''
        
        # Detect country from channel name
        country = self.detect_channel_country(channel_name)
        print(f"  🌍 Using geo-bypass for country: {country}")
        
        # Enhanced yt-dlp options with geo-bypass
        ydl_opts = {
            'cookies': self.cookies_file,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 5,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'android', 'ios'],
                    'skip': ['webpage', 'configs']
                }
            },
            # ENHANCED GEO-BYPASS FOR ALL REGIONS
            'geo_bypass': True,
            'geo_bypass_country': country,
            'xff': country,
            'headers': {
                'X-Forwarded-For': f'{country.lower()}-proxy',
                'Accept-Language': f'en-{country},en;q=0.9',
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None
                
                video_id = info.get('id')
                channel_id = info.get('channel_id', video_id)
                title = info.get('title', 'Unknown')
                channel_name = info.get('channel', 'Unknown')
                channel_url = info.get('channel_url', url)
                
                # Clean channel name
                clean_name = re.sub(r'[^\w\s-]', '', channel_name).strip()
                
                # Cache channel info
                self.cache['channels'][channel_id] = {
                    'name': channel_name,
                    'video_id': video_id,
                    'channel_url': channel_url,
                    'last_seen': datetime.now().isoformat()
                }
                
                # BETTER LIVE DETECTION
                is_live = False
                live_status = info.get('live_status', '')
                
                # Check multiple indicators
                if live_status == 'is_live':
                    is_live = True
                elif info.get('is_live'):
                    is_live = True
                elif info.get('was_live'):
                    is_live = False
                
                # Also check formats for live indicators
                formats = info.get('formats', [])
                has_live_format = any(
                    f.get('manifest_url') and 'live' in str(f.get('protocol', ''))
                    for f in formats
                )
                
                if has_live_format and not is_live:
                    is_live = True
                
                # Check for scheduled streams
                if 'schedule' in str(info.get('title', '')).lower():
                    is_live = False
                
                if not is_live:
                    print(f"  ⚠️ Not currently live (status: {live_status})")
                    return {
                        'status': 'offline',
                        'video_id': video_id,
                        'channel_id': channel_id,
                        'name': clean_name,
                        'title': title,
                        'channel_url': channel_url,
                        'is_live': False
                    }
                
                # Get quality-specific streams
                quality_streams = {}
                
                # Filter for actual live video formats
                video_formats = []
                for f in formats:
                    if f.get('manifest_url') or 'live' in str(f.get('protocol', '')):
                        if f.get('height') and f.get('url') and f.get('vcodec') != 'none':
                            video_formats.append(f)
                
                # If no live formats found, try all video formats
                if not video_formats:
                    video_formats = [
                        f for f in formats 
                        if f.get('height') and f.get('url') and f.get('vcodec') != 'none'
                    ]
                
                if not video_formats:
                    print("  ⚠️ No suitable video formats found")
                    return {
                        'status': 'offline',
                        'video_id': video_id,
                        'channel_id': channel_id,
                        'name': clean_name,
                        'title': title,
                        'channel_url': channel_url,
                        'is_live': False
                    }
                
                # Sort by quality
                video_formats.sort(key=lambda f: (f.get('height', 0), f.get('fps', 0)), reverse=True)
                
                # Get HD format (720p+)
                hd_formats = [f for f in video_formats if f.get('height', 0) >= 720]
                if hd_formats:
                    quality_streams['hd'] = {
                        'url': hd_formats[0]['url'],
                        'height': hd_formats[0].get('height', 0),
                        'fps': hd_formats[0].get('fps', 30),
                        'quality_tag': f"{hd_formats[0].get('height', 0)}p"
                    }
                
                # Get mobile format (480p and below)
                mobile_formats = [f for f in video_formats if f.get('height', 0) <= 480]
                if mobile_formats:
                    quality_streams['mobile'] = {
                        'url': mobile_formats[0]['url'],
                        'height': mobile_formats[0].get('height', 0),
                        'fps': mobile_formats[0].get('fps', 30),
                        'quality_tag': f"{mobile_formats[0].get('height', 0)}p"
                    }
                
                # Always have at least one format
                if not quality_streams and video_formats:
                    quality_streams['main'] = {
                        'url': video_formats[0]['url'],
                        'height': video_formats[0].get('height', 0),
                        'fps': video_formats[0].get('fps', 30),
                        'quality_tag': f"{video_formats[0].get('height', 0)}p"
                    }
                
                # Get channel logo
                logo_path = self.fetch_channel_logo(channel_id, clean_name)
                
                print(f"  ✅ Geo-bypass successful for {country}")
                if quality_streams:
                    first_url = next(iter(quality_streams.values())).get('url', '')
                    print(f"  🔗 URL preview: {first_url[:100]}...")
                
                return {
                    'status': 'live',
                    'video_id': video_id,
                    'channel_id': channel_id,
                    'name': clean_name,
                    'title': title,
                    'channel_url': channel_url,
                    'streams': quality_streams,
                    'logo': logo_path,
                    'is_live': True,
                    'country': country
                }
                
        except Exception as e:
            print(f"  ⚠️ Error: {str(e)[:150]}")
            return None
    
    def generate_individual_playlists(self, channels_data):
        """Generate individual M3U8 files for each channel with validation"""
        individual_channels = []
        
        for channel in channels_data:
            channel_name = channel.get('name', 'unknown')
            channel_id = channel.get('channel_id', '')
            country = channel.get('country', 'Unknown')
            
            # Create safe filename
            safe_name = self.safe_filename(channel_name)
            filename = f"{self.channels_dir}/{safe_name}.m3u8"
            
            # Check if channel is actually live
            is_live = channel.get('is_live', False) and channel.get('status') == 'live'
            
            if is_live:
                # Get best quality stream
                main_stream = channel.get('streams', {}).get('hd', {})
                if not main_stream:
                    for s in channel.get('streams', {}).values():
                        main_stream = s
                        break
                
                if main_stream and main_stream.get('url'):
                    quality_tag = main_stream.get('quality_tag', '')
                    logo_attr = f' tvg-logo="{channel["logo"]}"' if channel.get('logo') else ''
                    
                    # Add a note about URL expiration
                    expiry_time = (datetime.now() + timedelta(hours=5)).strftime('%H:%M UTC')
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        # Write header
                        f.write(f"""#EXTM3U
#EXT-X-VERSION:3
# Channel: {channel_name}
# ID: {channel_id}
# Quality: {quality_tag}
# Country: {country}
# Status: LIVE (as of {datetime.now().strftime('%H:%M UTC')})
# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
# URL expires: ~{expiry_time} (refresh playlist if expired)

""")
                        # Write EXTINF line with clear line break
                        f.write(f'#EXTINF:-1 tvg-id="{channel_id}"{logo_attr} tvg-name="{channel_name}" group-title="Individual",{channel_name} [{quality_tag}] 🔴 LIVE\n')
                        # Write URL on its own line
                        f.write(main_stream['url'])
                        f.write("\n")
                    
                    print(f"  ✅ LIVE ({country}): {filename}")
                    
                    individual_channels.append({
                        'name': channel_name,
                        'file': filename,
                        'id': channel_id,
                        'quality': quality_tag,
                        'status': 'live',
                        'url': main_stream['url'],
                        'country': country
                    })
                else:
                    # No valid stream URL
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"""#EXTM3U
#EXT-X-VERSION:3
# Channel: {channel_name}
# ID: {channel_id}
# Status: STREAM UNAVAILABLE
# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

#EXTINF:-1 tvg-name="{channel_name}",{channel_name} [Stream Unavailable - Check YouTube]
{channel.get('channel_url', 'https://youtube.com')}
""")
                    print(f"  ⚠️ UNAVAILABLE: {filename}")
            else:
                # Channel is offline
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"""#EXTM3U
#EXT-X-VERSION:3
# Channel: {channel_name}
# ID: {channel_id}
# Status: OFFLINE
# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

#EXTINF:-1 tvg-name="{channel_name}",{channel_name} [OFFLINE - Click for YouTube page]
{channel.get('channel_url', 'https://youtube.com')}
""")
                print(f"  ⚫ OFFLINE: {filename}")
        
        # Save list of individual channels
        with open(f"{self.channels_dir}/channels.json", 'w') as f:
            json.dump({
                'generated': datetime.now().isoformat(),
                'count': len(individual_channels),
                'channels': individual_channels
            }, f, indent=2)
        
        # Generate HTML index
        self.generate_channels_html(individual_channels)
        
        return individual_channels
    
    def generate_channels_html(self, channels):
        """Generate a simple HTML index page for all individual channels"""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>📺 Individual Channels</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header { 
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white; 
            padding: 30px; 
            text-align: center;
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .content { padding: 30px; }
        .channel-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .channel-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            border-left: 4px solid #4CAF50;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .channel-card:hover { transform: translateY(-2px); }
        .channel-name {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .channel-country {
            font-size: 0.85em;
            color: #666;
            margin-bottom: 10px;
        }
        .channel-quality {
            color: #4CAF50;
            font-size: 0.9em;
            margin-bottom: 15px;
        }
        .btn {
            display: inline-block;
            background: #4CAF50;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            margin-right: 10px;
            margin-bottom: 10px;
            font-size: 0.9em;
            border: none;
            cursor: pointer;
        }
        .btn:hover { background: #45a049; }
        .btn-outline {
            background: transparent;
            border: 2px solid #4CAF50;
            color: #4CAF50;
        }
        .btn-outline:hover {
            background: #4CAF50;
            color: white;
        }
        .footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }
        code {
            background: #f5f5f5;
            padding: 3px 6px;
            border-radius: 3px;
            font-size: 0.85em;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: bold;
            background: #e3f2fd;
            color: #1976d2;
        }
        @media (max-width: 768px) {
            .channel-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📺 Individual Channel Streams</h1>
            <p>Direct M3U8 links for each channel</p>
        </div>
        
        <div class="content">
            <div style="margin-bottom: 20px;">
                <a href="../streams.m3u8" class="btn">📋 Main Playlist</a>
                <a href="../streams_hd.m3u8" class="btn">🎥 HD Playlist</a>
                <a href="../streams_mobile.m3u8" class="btn">📱 Mobile Playlist</a>
                <a href="../epg.xml" class="btn">📺 EPG Guide</a>
            </div>
            
            <h2 style="margin-bottom: 20px;">Available Channels (""" + str(len(channels)) + """ live)</h2>
            <div class="channel-grid">
"""
        
        for ch in channels:
            filename = ch['file'].replace('channels/', '')
            country = ch.get('country', 'Unknown')
            html += f"""
                <div class="channel-card">
                    <div class="channel-name">{ch['name']}</div>
                    <div class="channel-country"><span class="badge">{country}</span></div>
                    <div class="channel-quality">🔴 LIVE • {ch['quality']}</div>
                    <div>
                        <a href="{filename}" class="btn">▶️ Play</a>
                        <a href="{filename}" download class="btn btn-outline">📥 Download</a>
                    </div>
                    <div style="margin-top: 10px;">
                        <small>Copy URL:</small><br>
                        <code>../channels/{filename}</code>
                    </div>
                </div>"""
        
        html += """
            </div>
        </div>
        
        <div class="footer">
            <p>🔄 Refreshes every 6 hours • URLs expire ~6 hours</p>
            <p>⏰ Last updated: """ + datetime.now().strftime('%Y-%m-%d %H:%M UTC') + """</p>
            <p>🔗 GitHub: <a href="https://github.com/uticap/Youtube-to-M3u8">uticap/Youtube-to-M3u8</a></p>
        </div>
    </div>
</body>
</html>"""
        
        with open(f"{self.channels_dir}/index.html", 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ Generated channels index: {self.channels_dir}/index.html")
    
    def generate_epg(self, channels_data):
        """Generate XMLTV EPG file"""
        tv = ET.Element("tv", {
            "generator-info-name": "YouTube Live EPG Generator",
            "date": datetime.now().strftime("%Y%m%d%H%M%S %Z")
        })
        
        for channel in channels_data:
            if channel.get('status') == 'live':
                channel_elem = ET.SubElement(tv, "channel", {"id": channel['channel_id']})
                
                display_name = ET.SubElement(channel_elem, "display-name")
                display_name.text = channel['name']
                
                if channel.get('logo'):
                    icon = ET.SubElement(channel_elem, "icon", {"src": channel['logo']})
                
                programme = ET.SubElement(tv, "programme", {
                    "start": datetime.now().strftime("%Y%m%d%H%M%S +0000"),
                    "stop": (datetime.now() + timedelta(hours=1)).strftime("%Y%m%d%H%M%S +0000"),
                    "channel": channel['channel_id']
                })
                
                title = ET.SubElement(programme, "title")
                title.text = channel.get('title', 'Live Stream')
                
                desc = ET.SubElement(programme, "desc")
                desc.text = f"Live YouTube stream from {channel['name']}"
                
                category = ET.SubElement(programme, "category")
                category.text = "Live"
        
        rough_string = ET.tostring(tv, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')
        
        with open('epg.xml', 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        print(f"✅ EPG generated with {len(channels_data)} channels")
    
    def generate_playlists(self, all_channels):
        """Generate multiple playlists (main, HD, mobile, audio)"""
        
        playlists = {
            'main': [],
            'hd': [],
            'mobile': [],
            'audio': []
        }
        
        headers = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            f"# Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"# Total channels: {len(all_channels)}",
            f"# Individual channels: https://uticap.github.io/Youtube-to-M3u8/channels/",
            ""
        ]
        
        for playlist_name in playlists:
            playlists[playlist_name] = headers.copy()
        
        stats = {
            'total': len(all_channels),
            'live': 0,
            'offline': 0,
            'error': 0,
            'qualities': {'1080p': 0, '720p': 0, '480p': 0, 'other': 0},
            'by_category': {},
            'by_country': {},
            'individual_channels': []
        }
        
        for channel in all_channels:
            channel_name = channel.get('name', 'Unknown')
            channel_id = channel.get('channel_id', '')
            country = channel.get('country', 'Unknown')
            
            # Track by country
            stats['by_country'][country] = stats['by_country'].get(country, 0) + 1
            
            # Determine category
            category = 'General'
            if 'news' in channel_name.lower():
                category = 'News'
            elif 'sport' in channel_name.lower():
                category = 'Sports'
            elif 'entertain' in channel_name.lower():
                category = 'Entertainment'
            
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            logo_attr = f' tvg-logo="{channel["logo"]}"' if channel.get('logo') else ''
            
            if channel.get('status') == 'live':
                stats['live'] += 1
                
                height = 0
                for stream_data in channel.get('streams', {}).values():
                    height = max(height, stream_data.get('height', 0))
                
                if height >= 1080:
                    stats['qualities']['1080p'] += 1
                elif height >= 720:
                    stats['qualities']['720p'] += 1
                elif height >= 480:
                    stats['qualities']['480p'] += 1
                else:
                    stats['qualities']['other'] += 1
                
                main_stream = channel.get('streams', {}).get('hd', {})
                if not main_stream:
                    for s in channel.get('streams', {}).values():
                        main_stream = s
                        break
                
                if main_stream:
                    quality_tag = main_stream.get('quality_tag', '')
                    playlists['main'].append(
                        f'#EXTINF:-1 tvg-id="{channel_id}"{logo_attr} tvg-name="{channel_name}" '
                        f'group-title="{category}",{channel_name} [{quality_tag}]'
                    )
                    playlists['main'].append(main_stream['url'])
                    playlists['main'].append("")
                    
                    safe_name = self.safe_filename(channel_name)
                    stats['individual_channels'].append({
                        'name': channel_name,
                        'file': f"channels/{safe_name}.m3u8",
                        'quality': quality_tag
                    })
                
                for profile_name in ['hd', 'mobile']:
                    if profile_name in channel.get('streams', {}):
                        stream = channel['streams'][profile_name]
                        suffix = QUALITY_PROFILES[profile_name]['suffix']
                        playlists[profile_name].append(
                            f'#EXTINF:-1 tvg-id="{channel_id}"{logo_attr} tvg-name="{channel_name}" '
                            f'group-title="{category}",{channel_name} {suffix}'
                        )
                        playlists[profile_name].append(stream['url'])
                        playlists[profile_name].append("")
            
            elif channel.get('status') == 'offline':
                stats['offline'] += 1
                fallback_url = f"https://www.youtube.com/watch?v={channel['video_id']}"
                
                for playlist_name in playlists:
                    playlists[playlist_name].append(
                        f'#EXTINF:-1 tvg-id="{channel_id}"{logo_attr} tvg-name="{channel_name}" '
                        f'group-title="{category}",{channel_name} [Offline]'
                    )
                    playlists[playlist_name].append(fallback_url)
                    playlists[playlist_name].append("")
            
            else:
                stats['error'] += 1
                for playlist_name in playlists:
                    playlists[playlist_name].append(
                        f'#EXTINF:-1 tvg-id="{channel_id}"{logo_attr} tvg-name="{channel_name}" '
                        f'group-title="{category}",{channel_name} [Error]'
                    )
                    playlists[playlist_name].append(f"https://youtube.com/watch?v={channel.get('video_id', '')}")
                    playlists[playlist_name].append("")
        
        summary = [
            "",
            f"# Summary: {stats['live']}/{stats['total']} streams active",
            f"# Quality: {stats['qualities']['1080p']}x1080p, {stats['qualities']['720p']}x720p, {stats['qualities']['480p']}x480p",
            f"# Categories: {', '.join([f'{k}:{v}' for k, v in stats['by_category'].items()])}",
            f"# Countries: {', '.join([f'{k}:{v}' for k, v in stats['by_country'].items()])}",
            f"# Individual channels: https://uticap.github.io/Youtube-to-M3u8/channels/",
            f"# Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        ]
        
        for playlist_name in playlists:
            playlists[playlist_name].extend(summary)
        
        playlist_files = {
            'main': 'streams.m3u8',
            'hd': 'streams_hd.m3u8',
            'mobile': 'streams_mobile.m3u8',
            'audio': 'streams_audio.m3u8'
        }
        
        for name, filename in playlist_files.items():
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(playlists[name]))
            print(f"✅ Saved: {filename}")
        
        with open('stats.json', 'w') as f:
            json.dump(stats, f, indent=2)
        
        return stats, playlists

def main():
    if not os.path.exists('streams.txt'):
        print("❌ streams.txt not found")
        return
    
    with open('streams.txt', 'r') as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    
    if not lines:
        print("⚠️ No streams found")
        return
    
    print(f"📡 Processing {len(lines)} channels...")
    print(f"🌍 Geo-bypass enabled for multiple countries (NG, GH, US, etc.)")
    
    generator = YouTubePlaylistGenerator()
    
    channels_data = []
    for i, url in enumerate(lines, 1):
        print(f"\n📺 [{i}/{len(lines)}] Processing: {url}")
        time.sleep(random.uniform(2, 5))
        
        channel_info = generator.get_stream_info(url)
        if channel_info:
            channels_data.append(channel_info)
            
            if channel_info['status'] == 'live':
                streams = list(channel_info.get('streams', {}).keys())
                country = channel_info.get('country', 'Unknown')
                print(f"  ✅ LIVE ({country}) - Qualities: {', '.join(streams)}")
            else:
                print(f"  ⚠️ {channel_info['status'].upper()}")
    
    print("\n📋 Generating EPG...")
    generator.generate_epg(channels_data)
    
    print("\n🎬 Generating playlists...")
    stats, playlists = generator.generate_playlists(channels_data)
    
    print("\n📺 Generating individual channel playlists...")
    individual_channels = generator.generate_individual_playlists(channels_data)
    
    generator.save_cache()
    
    print(f"\n{'='*50}")
    print(f"📊 FINAL STATISTICS:")
    print(f"   Live: {stats['live']}/{stats['total']}")
    print(f"   Offline: {stats['offline']}")
    print(f"   Errors: {stats['error']}")
    print(f"\n📊 Quality Distribution:")
    for quality, count in stats['qualities'].items():
        if count > 0:
            print(f"   {quality}: {count}")
    print(f"\n📊 Categories:")
    for category, count in stats['by_category'].items():
        print(f"   {category}: {count}")
    print(f"\n📊 Countries:")
    for country, count in stats['by_country'].items():
        print(f"   {country}: {count}")
    print(f"\n📁 Generated Files:")
    print("   - streams.m3u8 (Main playlist)")
    print("   - streams_hd.m3u8 (HD only)")
    print("   - streams_mobile.m3u8 (Mobile quality)")
    print("   - streams_audio.m3u8 (Audio only)")
    print("   - epg.xml (TV Guide)")
    print("   - stats.json (Detailed statistics)")
    print(f"   - channels/ (Individual channel files - {len(individual_channels)} files)")
    print(f"\n🌐 Individual Channels URL:")
    print(f"   https://uticap.github.io/Youtube-to-M3u8/channels/")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
