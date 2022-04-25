using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace HumanDT.UI
{
    public struct ImageObject
    {
        public int video_length;
        public string video_path;
        public string current_name;
        public int frame_rate;
        public int frame_count;
        public int start_count;
    }
    public struct ConfigStruct
    {
        public string CondaEnv;
        public string FilePath;
        public List<string> VideoPath;
        public string SavePath;
    }
    public struct VideoInfo
    {
        public double FrameRate { get; set; }
        public string VideoName { get; set; }
        public List<int> VideoSize { get; set; }
    }
    internal class CustomStructures
    {
    }
}
