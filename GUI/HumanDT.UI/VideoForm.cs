using System;
using System.Collections.Generic;
using System.Windows.Forms;
using System.Diagnostics;
using System.Threading;
using Timer = System.Windows.Forms.Timer;
using System.Drawing;
using DevExpress.XtraSplashScreen;

namespace HumanDT.UI
{
    public partial class VideoForm : Form
    {
        private readonly ProcessStartInfo _ProcessInfo = new();
        private readonly Process _Process = new();
        private ConfigStruct _Config;
        private readonly List<ImageObject> _ImageObjects = new();
        private readonly List<bool> _ImageRead = new();
        readonly List<PictureBox> _PictureBoxes = new();
        private int _Focused = 0;
        public VideoForm()
        {
            InitializeComponent();

            _PictureBoxes.Add(picIdx1);
            _PictureBoxes.Add(picIdx2);
            _PictureBoxes.Add(picIdx3);
            _PictureBoxes.Add(picIdx4);


            this.TopMost = true;
#if DEBUG
            this.TopMost = false;
#endif

            _ProcessInfo.FileName = "cmd.exe";

            _ProcessInfo.WindowStyle = ProcessWindowStyle.Hidden;
            _ProcessInfo.CreateNoWindow = true; //flase가 띄우기, true가 안 띄우기
            _ProcessInfo.UseShellExecute = false;
            _ProcessInfo.RedirectStandardInput = true;
            _ProcessInfo.RedirectStandardOutput = true;
            _ProcessInfo.RedirectStandardError = true;

            _Process.StartInfo = _ProcessInfo;

            _Config = new ConfigStruct
            {
                VideoPath = new List<string>()
            };
            //_Config.VideoPath.Add("D:/MnS/HumanDT/Pinokio.HumanDT/API/video/LOADING DOCK F3 Rampa 9-10.avi");
            //_Config.VideoPath.Add("D:/MnS/HumanDT/Pinokio.HumanDT/API/video/LOADING DOCK F3 Rampa 11-12.avi");
            //_Config.VideoPath.Add("D:/MnS/HumanDT/Pinokio.HumanDT/API/video/LOADING DOCK F3 Rampa 13 - 14.avi");
            //_Config.VideoPath.Add("D:/MnS/HumanDT/Pinokio.HumanDT/API/video/LOADING DOCK F3 Rampa 15-16.avi");
            //_Config.SavePath = @"../../API/temp/";

            string program_path = Application.StartupPath;
            System.IO.DirectoryInfo directory = new System.IO.DirectoryInfo(program_path);
            directory = GetParent(6, directory);
            System.IO.FileInfo[] filepath = directory.GetFiles("image_extractor.py", System.IO.SearchOption.AllDirectories);
            _Config.FilePath = filepath[0].DirectoryName;

            //_Config.CondaEnv = "VDT";
            _Config.CondaEnv = "";

            pnlView.Visible = false;

        }

        private void UpdateProperty(object sender, EventArgs e)
        {
            var obj = _ImageObjects[_Focused];
            System.IO.DirectoryInfo dir = new(obj.VideoPath);
            var length = dir.GetFiles().Length;
            double video_frame_rate = (double)obj.FrameRate;
            double current_time = (double)obj.FrameCount / video_frame_rate;
            double start_time = (double)obj.StartCount / video_frame_rate;
            double video_length_second = (double)length / video_frame_rate;

            TimeSpan time = TimeSpan.FromSeconds(current_time);
            lbCurrentTime.Text = time.ToString(@"hh\:mm\:ss\:fff");
            time = TimeSpan.FromSeconds(start_time);
            lbStartTime.Text = time.ToString(@"hh\:mm\:ss\:fff");
            time = TimeSpan.FromSeconds(video_length_second);
            lbVideoLength.Text = time.ToString(@"hh\:mm\:ss\:fff");
            lbFrameRate.Text = obj.FrameRate.ToString();
        }

        private void TimerStart()
        {
            Timer timer = new();
            timer.Interval = 66;
            timer.Tick += new EventHandler(Image_reader);
            timer.Start();

            Timer update_checker = new();
            update_checker.Interval = 1000;
            update_checker.Tick += new EventHandler(UpdateProperty);
            update_checker.Start();
        }

        private void Image_reader(object sender, EventArgs e)
        {
            for (int i = 0; i < _Config.VideoPath.Count; i++)
            {
                if (_ImageRead[i])
                {
                    LoadImage(i, true);
                }
            }
        }
        private void LoadImage(int idx, bool increase, int framecount = -1)
        {
            var obj = _ImageObjects[idx];
            if (framecount > -1)
            {
                obj.FrameCount = framecount;
            }

            try
            {
                obj.CurrentName = GetImageName(obj.FrameCount, obj.FrameRate);
                Image image = Image.FromFile(obj.VideoPath + obj.CurrentName);
                if (increase)
                {
                    obj.FrameCount += 1;
                }
                _PictureBoxes[idx].BackgroundImage = image;
                _ImageObjects[idx] = obj;
            }
            catch
            {
                obj.FrameCount -= 1;
                _ImageRead[idx] = false;
            }
        }

        private string MediaPlay(int idx)
        {
            string[] sperables = _Config.VideoPath[idx].Split('\\');
            string folder_name = sperables[sperables.Length - 1][..sperables[sperables.Length - 1].LastIndexOf('.')];

            string save_path = _Config.SavePath + folder_name + "\\";

            _Process.Start();

            _Process.StandardInput.WriteLine("conda activate " + _Config.CondaEnv);
            if (sperables[0].Equals("D:"))
            {
                _Process.StandardInput.WriteLine("D:");
            }
            _Process.StandardInput.WriteLine("cd " + _Config.FilePath);
            _Process.StandardInput.WriteLine("python image_extractor.py --video_path \"" + _Config.VideoPath[idx] + "\" --save_path \"" + save_path);

            _Process.StandardInput.Close();
            Thread.Sleep(3500);
            return save_path;
        }

        private static string GetImageName(int count, int frame_rate)
        {
            double time_val = (double)count / (double)frame_rate;
            string time_str = string.Format("{0:00000.00000}", time_val);
            time_str = time_str.Replace(".", "-");
            time_str += ".jpeg";
            return time_str;
        }

        private void ImageStep(int idx, bool next)
        {
            _ImageRead[idx] = false;
            var obj = _ImageObjects[idx];
            int framecount = 0;
            if (next)
            {
                framecount = obj.FrameCount + 1;
            }
            else
            {
                if (obj.FrameCount > 0)
                {
                    framecount = obj.FrameCount - 1;
                }
            }
            _Focused = idx;
            LoadImage(idx, false, framecount);
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

        private void BtnStop1Click(object sender, EventArgs e)
        {
            _Focused = 0;
            _ImageRead[0] = false;
        }

        private void BtnStop2Click(object sender, EventArgs e)
        {
            _Focused = 1;
            _ImageRead[1] = false;
        }

        private void BtnStop3Click(object sender, EventArgs e)
        {
            _Focused = 2;
            _ImageRead[2] = false;
        }

        private void BtnStop4Click(object sender, EventArgs e)
        {
            _Focused = 3;
            _ImageRead[3] = false;
        }

        private void BtnTotalStopClick(object sender, EventArgs e)
        {
            for (int i = 0; i < _Config.VideoPath.Count; i++)
            {
                _ImageRead[i] = false;
            }
        }

        private void BtnPrev1Click(object sender, EventArgs e)
        {
            ImageStep(0, false);
        }

        private void BtnPrev2Click(object sender, EventArgs e)
        {
            ImageStep(1, false);
        }

        private void BtnPrev3Click(object sender, EventArgs e)
        {
            ImageStep(2, false);
        }

        private void BtnPrev4Click(object sender, EventArgs e)
        {
            ImageStep(3, false);
        }

        private void BtnNext1Click(object sender, EventArgs e)
        {
            ImageStep(0, true);
        }

        private void BtnNext2Click(object sender, EventArgs e)
        {
            ImageStep(1, true);
        }

        private void BtnNext3Click(object sender, EventArgs e)
        {
            ImageStep(2, true);
        }

        private void BtnNext4Click(object sender, EventArgs e)
        {
            ImageStep(3, true);
        }

        private void BtnVisibleClick(object sender, EventArgs e)
        {
            if (btnVisible.Text.Equals("Visible Mode"))
            {
                btnVisible.BackColor = Color.Crimson;
                btnVisible.Text = "Fast Mode";
            }
            else
            {
                btnVisible.BackColor = Color.ForestGreen;
                btnVisible.Text = "Visible Mode";
            }
        }

        private void Button3Click(object sender, EventArgs e)
        {
            Application.Exit();
        }

        private void BtnSyncClick(object sender, EventArgs e)
        {
            for (int i = 0; i < _Config.VideoPath.Count; i++)
            {
                var obj = _ImageObjects[i];
                obj.StartCount = obj.FrameCount;
                _ImageObjects[i] = obj;
            }
        }

        private void AnalysisButtonClick(object sender, EventArgs e)
        {
            MappingForm mappingForm = new MappingForm(_Config, _ImageObjects);
            mappingForm.ShowDialog();
            this.Close();

            #region Python 실행
            _Process.Start();

            _Process.StandardInput.Write(@"ipconfig" + Environment.NewLine);
            _Process.StandardInput.WriteLine("conda activate FLOM");
            _Process.StandardInput.WriteLine("D:");
            _Process.StandardInput.WriteLine(@"cd D:\source-D\respos-D\Pinokio.HumanDT\API");
            _Process.StandardInput.WriteLine("python main.py");

            _Process.StandardInput.Close();

            Thread.Sleep(5000);

            string resultValue = _Process.StandardOutput.ReadToEnd();

            _Process.WaitForExit();

            _Process.Close();
            #endregion

            if (btnVisible.Text.Equals("Visible Mode"))
            {
                AnalysisForm mainForm = new(_ImageObjects);
                mainForm.ShowDialog();
                this.Close();
            }
            else
            {
                ProgressBar progressBar = new(_Process);
                progressBar.Show();
            }
        }

        private void BtnPlay1Click(object sender, EventArgs e)
        {
            _Focused = 0;
            _ImageRead[0] = true;
        }

        private void BtnPlay2Click(object sender, EventArgs e)
        {
            _Focused = 1;
            _ImageRead[1] = true;
        }

        private void BtnPlay3Click(object sender, EventArgs e)
        {
            _Focused = 2;
            _ImageRead[2] = true;
        }

        private void BtnPlay4Click(object sender, EventArgs e)
        {
            _Focused = 3;
            _ImageRead[3] = true;
        }

        private void BtnTotalPlayClick(object sender, EventArgs e)
        {
            for (int i = 0; i < _Config.VideoPath.Count; i++)
            {
                _ImageRead[i] = true;
            }
        }

        private void BtnImportClick(object sender, EventArgs e)
        {
            using (FolderBrowserDialog folderBrowserDialog = new FolderBrowserDialog())
            {
                var currentPath = System.IO.Directory.GetCurrentDirectory();
                string newPath = System.IO.Path.GetFullPath(System.IO.Path.Combine(currentPath, @"..\..\..\..\..\..\"));
                folderBrowserDialog.SelectedPath = newPath;
                if (folderBrowserDialog.ShowDialog() == DialogResult.OK)
                {
                    System.IO.DirectoryInfo di = new System.IO.DirectoryInfo(folderBrowserDialog.SelectedPath);
                    foreach(System.IO.FileInfo file in di.GetFiles())
                    {
                        if (file.Name.Contains(".avi") || file.Name.Contains(".mp4") || file.Name.Contains(".mkv"))
                        {
                            _Config.VideoPath.Add(file.FullName);
                        }
                    }
                }
                SplashScreenManager.ShowForm(typeof(ProgressForm));
                for (int i = 0; i < _Config.VideoPath.Count; i++)
                {
                    ImageObject temp_object = new()
                    {
                        FrameRate = 15,
                        VideoPath = MediaPlay(i),
                        FrameCount = 0,
                        CurrentName = GetImageName(0, 30)
                    };
                    _ImageObjects.Add(temp_object);
                    _ImageRead.Add(false);

                }
                TimerStart();
                pnlView.Visible = true;
                SplashScreenManager.CloseForm();
            }
        }

        private void BtnSavePathClick(object sender, EventArgs e)
        {
            using (FolderBrowserDialog folderBrowserDialog = new FolderBrowserDialog())
            {
                var currentPath = System.IO.Directory.GetCurrentDirectory();
                string newPath = System.IO.Path.GetFullPath(System.IO.Path.Combine(currentPath, @"..\..\..\..\..\..\"));
                folderBrowserDialog.SelectedPath = newPath;
                if (folderBrowserDialog.ShowDialog() == DialogResult.OK)
                {
                    _Config.SavePath = folderBrowserDialog.SelectedPath + "\\";
                }
            }
        }

        private void BtnResetClick(object sender, EventArgs e)
        {
            for (int i = 0; i < _Config.VideoPath.Count; i++)
            {
                var obj = _ImageObjects[i];
                obj.FrameCount = 0;
                _ImageObjects[i] = obj;
                LoadImage(i, false);
            }
        }

        private void PicIdx1Click(object sender, EventArgs e)
        {
            _Focused = 0;
        }

        private void PicIdx2Click(object sender, EventArgs e)
        {
            _Focused = 1;
        }

        private void PicIdx3Click(object sender, EventArgs e)
        {
            _Focused = 2;
        }

        private void PicIdx4Click(object sender, EventArgs e)
        {
            _Focused = 3;
        }
    }
}
