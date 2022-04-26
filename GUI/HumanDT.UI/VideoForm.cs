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
        private List<object> _GuideButtons = new();
        private string _MatrixPath;
        private int _Focused = 0;
        private int _Selected = 0;
        private List<VideoInfo> _VideoInfoList;


        public VideoForm()
        {
            InitializeComponent();

            _PictureBoxes.Add(picIdx1);
            _PictureBoxes.Add(picIdx2);
            _PictureBoxes.Add(picIdx3);
            _PictureBoxes.Add(picIdx4);

            _GuideButtons.Add(SavePathButton);
            _GuideButtons.Add(ImportButton);
            _GuideButtons.Add(btnTotalPlay);
            List<Button> controls = new();
            controls.Add(btnNext1);
            controls.Add(btnNext2);
            controls.Add(btnNext3);
            controls.Add(btnNext4);
            controls.Add(btnPrev1);
            controls.Add(btnPrev2);
            controls.Add(btnPrev3);
            controls.Add(btnPrev4);
            controls.Add(btnSync);
            _GuideButtons.Add(controls);
            _GuideButtons.Add(AnalysisButton);

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
            _VideoInfoList = new List<VideoInfo>();

            directory = new System.IO.DirectoryInfo(program_path);
            directory = GetParent(6, directory);
            _MatrixPath = directory.FullName + "\\API\\params\\projection";

            _Config.CondaEnv = "VDT";
            //_Config.CondaEnv = "";

            

            pnlView.Visible = false;
            pnlProperty.Visible = false;

            Timer guide_checker = new();
            guide_checker.Interval = 700;
            guide_checker.Tick += new EventHandler(UpdateGuide);
            guide_checker.Start();
        }

        private void UpdateGuide(object sender, EventArgs e)
        {
            for (int i = 0; i < _Selected; i++)
            {
                object item = _GuideButtons[i];
                Type temp_type = item.GetType();
                if (temp_type.Name.Equals("Button"))
                {
                    Button button = (Button)item;
                    button.BackColor = Color.FromArgb(210, 210, 210);
                }
                else
                {
                    List<Button> buttons = (List<Button>)item;
                    foreach (Button button in buttons)
                    {
                        button.BackColor = Color.FromArgb(210, 210, 210);
                    }
                }
            }
            int origin = -2960686;
            object target_button = _GuideButtons[_Selected];
            Type type = target_button.GetType();
            if (type.Name.Equals("Button"))
            {
                Button button = (Button)target_button;
                Color this_color = button.BackColor;
                if (this_color.ToArgb() == origin)
                {
                    button.BackColor = Color.RoyalBlue;
                }
                else
                {
                    button.BackColor = Color.FromArgb(210, 210, 210);
                }
            }
            else
            {
                bool changed = false;
                Color color = Color.FromArgb(210, 210, 210);
                List<Button> buttons = (List<Button>)target_button;
                foreach (Button button in buttons)
                {
                    Color this_color = button.BackColor;
                    if (!changed)
                    {
                        if (this_color.ToArgb() == origin)
                        {
                            changed = true;
                            color = Color.RoyalBlue;
                        }
                        else
                        {
                            changed = true;
                            color = Color.FromArgb(210, 210, 210);
                        }
                    }

                    button.BackColor = color;
                }
            }
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

        #region Prev&Next
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
        #endregion

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
            foreach (Process process in Process.GetProcesses())
            {
                if (process.ProcessName.Contains("python"))
                    process.Kill();
            }
            System.IO.DirectoryInfo di = new System.IO.DirectoryInfo(_Config.SavePath);
            List<string> yamlList = new List<string>();
            foreach (System.IO.FileInfo file in di.GetFiles("*.yaml"))
            {
                using (var input = new System.IO.StreamReader(file.FullName))
                {
                    yamlList.Add(file.FullName);
                    var yaml = new YamlDotNet.Serialization.Deserializer();
                    _VideoInfoList.Add(yaml.Deserialize<VideoInfo>(input));
                }
            }
            for (int i = 0; i < _Config.VideoPath.Count; i++)
            {
                var obj = _ImageObjects[i];
                obj.StartCount = obj.FrameCount;
                _ImageObjects[i] = obj;
                _VideoInfoList[i] = new VideoInfo()
                {
                    FrameRate =  _VideoInfoList[i].FrameRate,
                    StartCount = obj.StartCount,
                    VideoName = _VideoInfoList[i].VideoName,
                    VideoSize = _VideoInfoList[i].VideoSize
                };
            }
            if (_Selected == 3)
                _Selected = ++_Selected % _GuideButtons.Count;

            var serializer = new YamlDotNet.Serialization.SerializerBuilder().Build();
            for (int i = 0; i < _VideoInfoList.Count; i++)
            {
                var videoInfoYaml = serializer.Serialize(_VideoInfoList[i]);
                System.IO.File.WriteAllText(yamlList[i], videoInfoYaml); 
            }
        }

        private void AnalysisButtonClick(object sender, EventArgs e)
        {
            if (System.IO.File.Exists(_MatrixPath + "\\MappingMatrix.yaml"))
            {
                var result = MessageBox.Show("Mapping Matrix가 존재합니다. 기존 Matrix를 사용하시겠습니까?", "새롭게 Matrix를 설정하려면 No를 눌러주세요", MessageBoxButtons.YesNo);
                if (result == DialogResult.Yes)
                {
                    if (btnVisible.Text.Equals("Visible Mode"))
                    {
                        AnalysisForm mainForm = new(_ImageObjects, _Config, _Process);
                        mainForm.ShowDialog();
                        this.Close();
                    }
                    else
                    {
                        ProgressBar progressBar = new(_Process);
                        progressBar.Show();
                    }
                }
                else if (result == DialogResult.No)
                {
                    if (_Config.VideoPath.Count > 0)
                    {
                        MappingForm mappingForm = new MappingForm(_Config, _ImageObjects, _MatrixPath, _Process);
                        mappingForm.ShowDialog();
                        this.Close();
                    }
                    else
                        MessageBox.Show("Save Path와 Video Path를 먼저 설정해주세요.", "Video Path가 설정되지 않았습니다.");
                }
            }
            else
            {
                MappingForm mappingForm = new MappingForm(_Config, _ImageObjects, _MatrixPath, _Process);
                mappingForm.ShowDialog();
                this.Close();
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
            if (_Selected == 2)
                _Selected = ++_Selected % _GuideButtons.Count;
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
                SplashScreenManager.CloseForm();
                TimerStart();
                pnlView.Visible = true;
                pnlProperty.Visible = true;
            }
            if (_Selected == 1)
                _Selected = ++_Selected % _GuideButtons.Count;
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
            if (_Selected == 0)
                _Selected = ++_Selected % _GuideButtons.Count;
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
