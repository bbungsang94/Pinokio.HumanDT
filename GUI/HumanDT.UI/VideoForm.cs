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
            _Config.FilePath = "../../../../../../API/utilities/";
            //_Config.CondaEnv = "VDT";
            _Config.CondaEnv = "";
            
        }

        private void TimerStart()
        {
            Timer timer = new();
            timer.Interval = 66;
            timer.Tick += new EventHandler(Image_reader);
            timer.Start();
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
            Image image = null;
            if (framecount > -1)
            {
                obj.Frame_count = framecount;
            }

            try
            {
                obj.Current_name = GetImageName(obj.Frame_count, obj.Frame_rate);
                image = Image.FromFile(obj.Video_path + obj.Current_name);
                if (increase)
                {
                    obj.Frame_count += 1;
                }
                _PictureBoxes[idx].BackgroundImage = image;
                _ImageObjects[idx] = obj;
            }
            catch
            {
                obj.Frame_count -= 1;
                _ImageRead[idx] = false;
            }
        }

        private string MediaPlay(int idx)
        {
            string[] sperables = _Config.VideoPath[idx].Split('\\');
            string folder_name = sperables[sperables.Length - 1].Substring(0, sperables[sperables.Length - 1].LastIndexOf('.'));

            string save_path = _Config.SavePath + folder_name + "\\";

            _Process.Start();

            _Process.StandardInput.WriteLine("conda activate " + _Config.CondaEnv);
            if (sperables[0].Equals("D:"))
            {
                _Process.StandardInput.WriteLine("D:");
            }
            _Process.StandardInput.WriteLine("cd " + System.IO.Path.GetFullPath(_Config.FilePath));
            _Process.StandardInput.WriteLine("python image_extractor.py --video_path \"" + _Config.VideoPath[idx] + "\" --save_path \"" + save_path);

            _Process.StandardInput.Close();
            Thread.Sleep(3500);
            return save_path;
        }

        private string GetImageName(int count, int frame_rate)
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
                framecount = obj.Frame_count + 1;
            }
            else
            {
                if (obj.Frame_count > 0)
                {
                    framecount = obj.Frame_count - 1;
                }
            }
            LoadImage(idx, false, framecount);
        }

        private void BtnStop1Click(object sender, EventArgs e)
        {
            _ImageRead[0] = false;
        }

        private void BtnStop2Click(object sender, EventArgs e)
        {
            _ImageRead[1] = false;
        }

        private void BtnStop3Click(object sender, EventArgs e)
        {
            _ImageRead[2] = false;
        }

        private void BtnStop4Click(object sender, EventArgs e)
        {
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

            DialogResult result = MessageBox.Show("실시간 분석 결과를 보겠습니까?", "최종 결과만 보기 위해서는 '아니요' 버튼을 눌러주세요.", MessageBoxButtons.YesNo);
            if (result == DialogResult.Yes)
            {
                AnalysisForm mainForm = new AnalysisForm(_ImageObjects);
                mainForm.ShowDialog();
                this.Close();
            }
            else if (result == DialogResult.No)
            {
                ProgressBar progressBar = new ProgressBar(_Process);
                progressBar.Show();
            }

        }

        private void BtnPlay1Click(object sender, EventArgs e)
        {
            _ImageRead[0] = true;
        }

        private void BtnPlay2Click(object sender, EventArgs e)
        {
            _ImageRead[1] = true;
        }

        private void BtnPlay3Click(object sender, EventArgs e)
        {
            _ImageRead[2] = true;
        }

        private void BtnPlay4Click(object sender, EventArgs e)
        {
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
                        Frame_rate = 15,
                        Video_path = MediaPlay(i),
                        Frame_count = 0,
                        Current_name = GetImageName(0, 30)
                    };
                    _ImageObjects.Add(temp_object);
                    _ImageRead.Add(false);

                }
                TimerStart();
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
    }
}
