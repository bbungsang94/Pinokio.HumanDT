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
using OpenCvSharp;

namespace HumanDT.UI
{
    public partial class MappingForm : DevExpress.XtraEditors.XtraForm
    {
        private bool _VideoPointsFlag;
        private bool _PlanPointsFlag;
        private Dictionary<int, int> _VideoPointsCounts;
        private int _PlanPointsCount;
        private List<Tuple<float, float>> _VideoPoints;
        private List<Tuple<float, float>> _PlanPoints;
        private int _TargetVideoIdx;
        
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
            _VideoPoints = new List<Tuple<float, float>>();
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

            _VideoPoints = new List<Tuple<float, float>>();
            _PlanPoints = new List<Tuple<float, float>>();

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

                obj.CurrentName = GetImageName(obj.FrameCount, obj.FrameRate);
                Image image = Image.FromFile(obj.VideoPath + obj.CurrentName);
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
                            return;
                            //_VideoPoints[0].Clear();
                            //Video1_pictureBox.Image = null;
                            //_VideoPointsCounts[0] = 0;
                            //_VideoPointsFlag = false;
                            //btnVideoPoints.BackColor = Color.FromArgb(210, 210, 210);
                            //btnVideoPoints.Enabled = true;
                        }
                        int x = Control.MousePosition.X;
                        int y = Control.MousePosition.Y;

                        System.Drawing.Point mousePos = new System.Drawing.Point(x, y); //프로그램 내 좌표
                        System.Drawing.Point mousePosPtoClient = pic.PointToClient(mousePos);  //picbox 내 좌표
                        var test = Video1_pictureBox.Size;
                        var widthRate = (float)Video1_pictureBox.Size.Width / (float)Video1_pictureBox.BackgroundImage.Size.Width;
                        var heightRate = (float)Video1_pictureBox.Size.Height / (float)Video1_pictureBox.BackgroundImage.Size.Height;

                        var xPoint = (float)mousePosPtoClient.X / widthRate;
                        var yPoint = (float)mousePosPtoClient.Y / heightRate;

                        _VideoPoints.Add(new Tuple<float, float>(xPoint, yPoint));
                        _TargetVideoIdx = 0;
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
            _VideoPoints.Clear();
            Video1_pictureBox.Image = null;
            _VideoPointsCounts[0] = 0;
            btnVideoPoints.BackColor = Color.ForestGreen;

            _PlanPointsFlag = false;
            btnPlanPoints.Enabled = true;
            btnPlanPoints.BackColor = Color.FromArgb(210, 210, 210);
        }

        private void BtnPlanImportClick(object sender, EventArgs e)
        {
            using (OpenFileDialog openFileDialog = new OpenFileDialog())
            {
                openFileDialog.Filter = "Image Files|*.jpg;*.jpeg;*.png;*.gif;*.tif;...";
                if (openFileDialog.ShowDialog() == DialogResult.OK)
                {
                    planPictureBox.BackgroundImage = new Bitmap(openFileDialog.FileName);
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
            btnPlanPoints.BackColor = Color.ForestGreen;

            _PlanPoints.Clear();
            planPictureBox.Image = null;
            _PlanPointsCount = 0;
        }

        private void BtnPlanPictureClick(object sender, EventArgs e)
        {
            if (_PlanPointsFlag)
            {
                if (sender.GetType() == planPictureBox.GetType())
                {
                    PictureBox pic = (PictureBox)sender;
                    if (((MouseEventArgs)e).Button == MouseButtons.Left)
                    {
                        Graphics g = planPictureBox.CreateGraphics();
                        if (_PlanPointsCount == 4)
                        {
                            return;
                            //_PlanPoints.Clear();
                            //planPictureBox.Image = null;
                            //_PlanPointsCount = 0;
                            //_PlanPointsFlag = false;
                            //btnVideoPoints.BackColor = Color.FromArgb(210, 210, 210);
                            //btnVideoPoints.Enabled = true;
                        }
                        int x = Control.MousePosition.X;
                        int y = Control.MousePosition.Y;

                        System.Drawing.Point mousePos = new System.Drawing.Point(x, y); //프로그램 내 좌표
                        System.Drawing.Point mousePosPtoClient = pic.PointToClient(mousePos);  //picbox 내 좌표
                        var test = planPictureBox.Size;
                        var widthRate = (float)planPictureBox.Size.Width / (float)planPictureBox.BackgroundImage.Size.Width;
                        var heightRate = (float)planPictureBox.Size.Height / (float)planPictureBox.BackgroundImage.Size.Height;

                        var xPoint = (float)mousePosPtoClient.X / widthRate;
                        var yPoint = (float)mousePosPtoClient.Y / heightRate;

                        _PlanPoints.Add(new Tuple<float, float>(xPoint, yPoint));
                        _PlanPointsCount++;
                        g.FillEllipse(Brushes.Blue, mousePosPtoClient.X - 5, mousePosPtoClient.Y - 5, 10, 10);
                    }
                    if (((MouseEventArgs)e).Button == MouseButtons.Right)
                    {
                        //do something
                    }
                }
            }
        }

        private void BtnAnalysisClick(object sender, EventArgs e)
        {
            if (_VideoPoints.Count == 4 && _PlanPoints.Count == 4)
            {
                Point2f[] srcPoint = new Point2f[4];
                srcPoint[0] = new Point2f(_VideoPoints[0].Item1, _VideoPoints[0].Item2);
                srcPoint[1] = new Point2f(_VideoPoints[1].Item1, _VideoPoints[1].Item2);
                srcPoint[2] = new Point2f(_VideoPoints[2].Item1, _VideoPoints[2].Item2);
                srcPoint[3] = new Point2f(_VideoPoints[3].Item1, _VideoPoints[3].Item2);

                //Point2f[] dstPoint = new Point2f[4];


                //Mat matrix = Cv2.GetPerspectiveTransform()
            }
            
        }
    }
}