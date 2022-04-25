using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace HumanDT.UI
{
    public struct ImageObject
    {
        public int Video_length;
        public string Video_path;
        public string Current_name;
        public int Frame_rate;
        public int Frame_count;
        public int Start_count;
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
