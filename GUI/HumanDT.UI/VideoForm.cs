using System;
using System.Collections.Generic;
using System.Windows.Forms;
using System.Diagnostics;
using System.Threading;
using Timer = System.Windows.Forms.Timer;
using System.Drawing;

namespace HumanDT.UI
{
    struct ImageObject
    {
        public int video_length;
        public string video_path;
        public string current_name;
        public int frame_rate;
        public int frame_count;
    }
    struct ConfigStruct
    {
        public string CondaEnv;
        public string FilePath;
        public List<string> VideoPath;
        public string SavePath; 
    }
    public partial class VideoForm : Form
    {
        private readonly ProcessStartInfo _processInfo = new();
        private readonly Process _process = new();
        private ConfigStruct config;
        private readonly List<ImageObject> image_Objects = new();
        private readonly List<bool> ImageRead = new();
        public VideoForm()
        {
            InitializeComponent();
            this.TopMost = true;

            
            _processInfo.FileName = "cmd.exe";

            //cmd 창 띄우기
            _processInfo.WindowStyle = ProcessWindowStyle.Hidden;
            _processInfo.CreateNoWindow = true; //flase가 띄우기, true가 안 띄우기
            _processInfo.UseShellExecute = false;
            _processInfo.RedirectStandardInput = true;
            _processInfo.RedirectStandardOutput = true;
            _processInfo.RedirectStandardError = true;

            _process.StartInfo = _processInfo;

            config = new ConfigStruct
            {
                VideoPath = new List<string>()
            };
            config.VideoPath.Add("D:/MnS/HumanDT/Pinokio.HumanDT/API/video/LOADING DOCK F3 Rampa 9-10.avi");
            config.VideoPath.Add("D:/MnS/HumanDT/Pinokio.HumanDT/API/video/LOADING DOCK F3 Rampa 11-12.avi");
            config.VideoPath.Add("D:/MnS/HumanDT/Pinokio.HumanDT/API/video/LOADING DOCK F3 Rampa 13 - 14.avi");
            config.VideoPath.Add("D:/MnS/HumanDT/Pinokio.HumanDT/API/video/LOADING DOCK F3 Rampa 15-16.avi");
            config.SavePath = "D:/MnS/HumanDT/Pinokio.HumanDT/API/temp/";
            config.FilePath = "D:/MnS/HumanDT/Pinokio.HumanDT/API/utilities/";
            config.CondaEnv = "VDT";
            for (int i = 0; i < config.VideoPath.Count; i++)
            {
                ImageObject temp_object = new()
                {
                    frame_rate = 30,
                    video_path = media_play(i) + "/",
                    frame_count = 0,
                    current_name = get_image_name(0, 30)
                };
                image_Objects.Add(temp_object);
                ImageRead.Add(false);

            }
            timer_start();
        }

        private void panel1_Paint(object sender, PaintEventArgs e)
        {

        }

        private void Analysis_button_Click(object sender, EventArgs e)
        {
            #region Python 실행
            //실행할 파일 명 입력하기
            _process.Start();

            //명령어 실행
            _process.StandardInput.Write(@"ipconfig" + Environment.NewLine);
            //_process.StandardInput.WriteLine("conda activate FLOM");
            //_process.StandardInput.WriteLine("D:");
            //_process.StandardInput.WriteLine(@"cd D:\source-D\respos-D\Pinokio.HumanDT\API");
            //_process.StandardInput.WriteLine("python main.py");

            _process.StandardInput.Close();

            Thread.Sleep(5000);

            string resultValue = _process.StandardOutput.ReadToEnd();

            _process.WaitForExit();

            _process.Close();
            #endregion

            DialogResult result = MessageBox.Show("실시간 분석 결과를 보겠습니까?", "최종 결과만 보기 위해서는 '아니요' 버튼을 눌러주세요.", MessageBoxButtons.YesNo);
            //if(result == DialogResult.Yes)
            //{
            //    AnalysisForm mainForm = new AnalysisForm();
            //    mainForm.ShowDialog();
            //    this.Close();
            //}
            //else if(result == DialogResult.No)
            //{
            //    ProgressBar progressBar = new ProgressBar(_process);
            //    progressBar.Show();
            //}
            
        }

        private void btnPlay1_Click(object sender, EventArgs e)
        {
            ImageRead[0] = true;
        }

        private void btnPlay2_Click(object sender, EventArgs e)
        {
            ImageRead[1] = true;
        }

        private void btnPlay3_Click(object sender, EventArgs e)
        {
            ImageRead[2] = true;
        }

        private void btnPlay4_Click(object sender, EventArgs e)
        {
            ImageRead[3] = true;
        }

        private void btnTotalPlay_Click(object sender, EventArgs e)
        {
            for (int i = 0; i < config.VideoPath.Count; i++)
            {
                ImageRead[i] = true;
            }
        }

        private void timer_start()
        {
            Timer timer = new();
            timer.Interval = 33; // 1/30초
            timer.Tick += new EventHandler(Image_reader);
            timer.Start();
        }

        private void Image_reader(object sender, EventArgs e)
        {
            List<PictureBox> pictureBoxes = new();
            pictureBoxes.Add(picIdx1);
            pictureBoxes.Add(picIdx2);
            pictureBoxes.Add(picIdx3);
            pictureBoxes.Add(picIdx4);

            for (int i = 0; i < config.VideoPath.Count; i++)
            {
                if (ImageRead[i])
                {
                    var obj = image_Objects[i];
                    obj.current_name = get_image_name(obj.frame_count, obj.frame_rate);
                    obj.frame_count++;
                    Image image = Image.FromFile(obj.video_path + obj.current_name);
                    pictureBoxes[i].BackgroundImage = image;
                }
            }
        }

        private string media_play(int idx)
        {
            string[] sperables = config.VideoPath[idx].Split('/');
            string folder_name = sperables[sperables.Length - 1].Substring(0, sperables[sperables.Length - 1].LastIndexOf('.'));
            
            string save_path = config.SavePath + folder_name;

            //실행할 파일 명 입력하기
            _process.Start();

            //명령어 실행
            _process.StandardInput.WriteLine("conda activate " + config.CondaEnv);
            if (sperables[0].Equals("D:"))
            {
                _process.StandardInput.WriteLine("D:");
            }
            _process.StandardInput.WriteLine("cd " + config.FilePath);
            _process.StandardInput.WriteLine("python image_extractor.py --video_path \"" + config.VideoPath[idx] + "\" --save_path \"" + save_path);

            _process.StandardInput.Close();
            return save_path;
        }

        private string get_image_name(int count, int frame_rate)
        {
            double time_val = (double)count / (double)frame_rate;
            string time_str = string.Format("{0:000000.00000}", time_val);
            time_str = time_str.Replace(".", "-");
            time_str += ".jpeg";
            return time_str;
        }

        private void btnStop1_Click(object sender, EventArgs e)
        {
            ImageRead[0] = true;
        }

        private void btnStop2_Click(object sender, EventArgs e)
        {

        }

        private void btnStop3_Click(object sender, EventArgs e)
        {

        }

        private void btnStop4_Click(object sender, EventArgs e)
        {

        }

        private void btnTotalStop_Click(object sender, EventArgs e)
        {

        }
    }
}
