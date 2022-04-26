using DevExpress.XtraEditors;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Diagnostics;
using System.Threading;
using DevExpress.XtraSplashScreen;
using Timer = System.Windows.Forms.Timer;

namespace HumanDT.UI
{
    public partial class AnalysisForm : DevExpress.XtraEditors.XtraForm
    {
        private readonly ProcessStartInfo _ProcessInfo = new();
        private readonly Process _Process;
        private readonly List<TrackingObject> _TrackingObjects = new();
        private readonly List<ImageObject> _ImageObjects = new();
        private readonly List<bool> _ImageRead = new();
        readonly List<PictureBox> _PictureBoxes = new();
        private string _OutputPath;
        private string _TrackingPath;
        private List<string> _VideoList = new();

        private ConfigStruct _Config;
        public AnalysisForm(List<ImageObject> imageObjects, ConfigStruct config, Process process)
        {
            InitializeComponent();
            _PictureBoxes.Add(pictureBox1);
            _PictureBoxes.Add(pictureBox2);
            _PictureBoxes.Add(pictureBox3);
            _PictureBoxes.Add(pictureBox4);
            _Process = process;
            _Config = config;
            _ImageObjects = imageObjects;
            SplashScreenManager.ShowForm(typeof(ProgressForm));


            #region Python 실행
            string program_path = Application.StartupPath;
            System.IO.DirectoryInfo directory = new System.IO.DirectoryInfo(program_path);
            directory = GetParent(6, directory);
            System.IO.FileInfo[] filepath = directory.GetFiles("main.py", System.IO.SearchOption.AllDirectories);
            _Config.FilePath = filepath[0].DirectoryName;

            //_ProcessInfo.FileName = "cmd.exe";

            //_ProcessInfo.WindowStyle = ProcessWindowStyle.Hidden;
            //_ProcessInfo.CreateNoWindow = true; //flase가 띄우기, true가 안 띄우기
            //_ProcessInfo.UseShellExecute = false;
            //_ProcessInfo.RedirectStandardInput = true;
            //_ProcessInfo.RedirectStandardOutput = true;
            //_ProcessInfo.RedirectStandardError = true;

            //_Process.StartInfo = _ProcessInfo;
            _Process.Start();

            _Process.StandardInput.WriteLine($"conda activate {_Config.CondaEnv}");
            if (_Config.FilePath.Contains("D:"))
            {
                _Process.StandardInput.WriteLine("D:");
            }
            _Process.StandardInput.WriteLine("cd " + _Config.FilePath);
            _Process.StandardInput.WriteLine("python main.py");

            _Process.StandardInput.Close();

            Thread.Sleep(10000);
            #endregion
            _OutputPath = _Config.FilePath + "\\output";
            System.IO.DirectoryInfo di = new System.IO.DirectoryInfo(_OutputPath);
            _OutputPath = _OutputPath + "\\" + di.GetDirectories()[0].Name;
            _TrackingPath = _OutputPath + "\\" + "tracking_result";
            di = new System.IO.DirectoryInfo(_TrackingPath);
            foreach (var videoDirectory in di.GetDirectories())
            {
                _VideoList.Add(videoDirectory.Name);
            }
            for (int i = 0; i < _PictureBoxes.Count; i++)
            {
                TrackingObject temp_object = new()
                {
                    FrameRate = 15,
                    VideoPath = _TrackingPath + "\\" + _VideoList[i] + "\\",
                    FrameCount = _ImageObjects[i].FrameCount,
                    CurrentName = GetImageName(0, 30)
                };
                _TrackingObjects.Add(temp_object);
                _ImageRead.Add(true);
            }
            SplashScreenManager.CloseForm();

            TimerStart();
        }
        private void TimerStart()
        {
            Timer timer = new();
            timer.Interval = 66;
            timer.Tick += new EventHandler(Image_reader);
            timer.Start();
        }
        private static string GetImageName(int count, int frame_rate)
        {
            double time_val = (double)count / (double)frame_rate;
            string time_str = string.Format("{0:00000.00000}", time_val);
            time_str = time_str.Replace(".", "-");
            time_str += ".jpeg";
            return time_str;
        }
        private System.IO.DirectoryInfo GetParent(int Iteration, System.IO.DirectoryInfo Directory)
        {
            if (Iteration == 0)
            {
                return Directory;
            }
            else
            {
                return GetParent(--Iteration, Directory.Parent);
            }
        }

        private void Close_button_Click(object sender, EventArgs e)
        {
            this.Close();
        }
        private void Image_reader(object sender, EventArgs e)
        {
            for (int i = 0; i < _VideoList.Count; i++)
            {
                if (_ImageRead[i])
                {
                    LoadImage(i, true);
                }
            }
        }
        private void LoadImage(int idx, bool increase, int framecount = -1)
        {
            var obj = _TrackingObjects[idx];
            if (framecount > -1)
            {
                obj.FrameCount = framecount;
            }

            try
            {
                obj.CurrentName = GetImageName(obj.FrameCount + 1, obj.FrameRate);
                Image image = Image.FromFile(obj.VideoPath + obj.CurrentName);
                if (increase)
                {
                    obj.FrameCount += 1;
                }
                _PictureBoxes[idx].BackgroundImage = image;
                _TrackingObjects[idx] = obj;
            }
            catch
            {
                obj.FrameCount -= 1;
                _ImageRead[idx] = false;
            }
        }
    }
}