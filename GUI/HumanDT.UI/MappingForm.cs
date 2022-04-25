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

namespace HumanDT.UI
{
    public partial class MappingForm : DevExpress.XtraEditors.XtraForm
    {
        private bool _VideoPointsFlag;
        private bool _PlanPointsFlag;
        private Dictionary<int, int> _VideoPointsCounts;
        private Dictionary<int, List<Tuple<float, float>>> _VideoPoints;
        private List<int> _XPonts;
        private List<int> _YPonts;
        private ConfigStruct _Config;
        private List<ImageObject> _ImageObjects;
        private List<VideoInfo> _VideoInfoList;
        readonly List<PictureBox> _PictureBoxes = new();

        public MappingForm(ConfigStruct config, List<ImageObject> imageObjects)
        {
            InitializeComponent();
            _VideoPointsFlag = false;
            _VideoPointsCounts = new Dictionary<int, int>();
            _XPonts = new List<int>();
            _YPonts = new List<int>();
            _VideoPoints = new Dictionary<int, List<Tuple<float, float>>>();
            _Config = config;
            _ImageObjects = imageObjects;
            System.IO.DirectoryInfo di = new System.IO.DirectoryInfo(_Config.SavePath);
            _VideoInfoList = new List<VideoInfo>();

            

            foreach (System.IO.FileInfo file in di.GetFiles("*.yaml"))
            {
                var input = new System.IO.StreamReader(file.FullName);
                var yaml = new YamlDotNet.Serialization.Deserializer();
                _VideoInfoList.Add(yaml.Deserialize<VideoInfo>(input));
            }
            Initialize();
            InitializeImages();
        }

        private void Initialize()
        {
            _PictureBoxes.Add(Video1_pictureBox);
            _PictureBoxes.Add(Video2_pictureBox);
            _PictureBoxes.Add(Video3_pictureBox);
            _PictureBoxes.Add(Video4_pictureBox);

            _VideoPoints.Add(0, new List<Tuple<float, float>>());
            _VideoPoints.Add(1, new List<Tuple<float, float>>());
            _VideoPoints.Add(2, new List<Tuple<float, float>>());
            _VideoPoints.Add(3, new List<Tuple<float, float>>());

            _VideoPointsCounts.Add(0, 0);
            _VideoPointsCounts.Add(1, 0);
            _VideoPointsCounts.Add(2, 0);
            _VideoPointsCounts.Add(3, 0);
        }

        private void InitializeImages()
        {
            for (int idx = 0; idx < _ImageObjects.Count; idx++)
            {
                var obj = _ImageObjects[idx];
                
                obj.Current_name = GetImageName(obj.Frame_count, obj.Frame_rate);
                Image image = Image.FromFile(obj.Video_path + obj.Current_name);
                _PictureBoxes[idx].BackgroundImage = image;
                _ImageObjects[idx] = obj;
            }
        }

        private string GetImageName(int count, int frame_rate)
        {
            double time_val = (double)count / (double)frame_rate;
            string time_str = string.Format("{0:00000.00000}", time_val);
            time_str = time_str.Replace(".", "-");
            time_str += ".jpeg";
            return time_str;
        }

        private void Plan_Points_Click(object sender, EventArgs e)
        {


        }
        

        private void Video_pictureBox_Click(object sender, EventArgs e)
        {
            if (_VideoPointsFlag)
            {
                if (sender.GetType() == Video1_pictureBox.GetType())
                {
                    PictureBox pic = (PictureBox)sender;
                    if (((MouseEventArgs)e).Button == MouseButtons.Left)
                    {
                        Graphics g = Video1_pictureBox.CreateGraphics();
                        if (_VideoPointsCounts[0] == 4)
                        {
                            _VideoPoints[0].Clear();
                            Video1_pictureBox.Image = null;
                            _VideoPointsCounts[0] = 0;
                            _VideoPointsFlag = false;
                            btnVideoPoints.BackColor = Color.FromArgb(210, 210, 210);
                            btnVideoPoints.Enabled = true;
                            return;
                        }
                        int x = Control.MousePosition.X;
                        int y = Control.MousePosition.Y;

                        Point mousePos = new Point(x, y); //프로그램 내 좌표
                        Point mousePosPtoClient = pic.PointToClient(mousePos);  //picbox 내 좌표
                        var test = Video1_pictureBox.Size;
                        var widthRate = (float)Video1_pictureBox.Size.Width / (float)Video1_pictureBox.BackgroundImage.Size.Width;
                        var heightRate = (float)Video1_pictureBox.Size.Height / (float)Video1_pictureBox.BackgroundImage.Size.Height;

                        var xPoint = (float)mousePosPtoClient.X / widthRate;
                        var yPoint = (float)mousePosPtoClient.Y / heightRate;

                        _VideoPoints[0].Add(new Tuple<float, float>(xPoint, yPoint));
                        _VideoPointsCounts[0]++;
                        g.FillEllipse(Brushes.Red, mousePosPtoClient.X - 5, mousePosPtoClient.Y - 5, 10, 10);
                    }
                    if (((MouseEventArgs)e).Button == MouseButtons.Right)
                    {
                        //do something
                    }
                }
            }
            
        }

        private void Video_Points_Click(object sender, EventArgs e)
        {
            _VideoPointsFlag = true;
            _VideoPoints[0].Clear();
            Video1_pictureBox.Image = null;
            _VideoPointsCounts[0] = 0;
            btnVideoPoints.BackColor = Color.ForestGreen;
            btnVideoPoints.Enabled = false;
        }

        private void BtnPlanImportClick(object sender, EventArgs e)
        {
            using (OpenFileDialog openFileDialog = new OpenFileDialog())
            {
                openFileDialog.Filter = "Image Files|*.jpg;*.jpeg;*.png;*.gif;*.tif;...";
                if (openFileDialog.ShowDialog() == DialogResult.OK)
                {
                    pictureBox5.BackgroundImage = new Bitmap(openFileDialog.FileName);
                }
            }
        }

        private void BtnCloseClick(object sender, EventArgs e)
        {
            Application.Exit();
        }

        private void BtnPlanPointsClick(object sender, EventArgs e)
        {
            _VideoPointsFlag = false;
            btnVideoPoints.Enabled = true;
            btnVideoPoints.BackColor = Color.FromArgb(210, 210, 210);

            _PlanPointsFlag = true;
        }
    }
}