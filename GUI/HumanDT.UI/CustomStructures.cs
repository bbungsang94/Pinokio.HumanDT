using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace HumanDT.UI
{
    public struct ImageObject
    {
        public int VideoLength;
        public string VideoPath;
        public string CurrentName;
        public int FrameRate;
        public int FrameCount;
        public int StartCount;
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
        public int StartCount { get; set; }
    }
    public struct MappingMatrix
    {
        public Dictionary<int, List<float[]>> Seperates { get; set; }
        public Dictionary<int, List<double[]>> Matrices { get; set; }
    }

    internal class CustomStructures
    {
    }
}
