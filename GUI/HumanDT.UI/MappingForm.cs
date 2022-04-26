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
        private Dictionary<int, List<Point2f[]>> _FixedVideoPoints;
        private int _TargetVideoIdx;
        private Dictionary<int, List<double[]>> _MappingMatrix;
        private ConfigStruct _Config;
        private List<ImageObject> _ImageObjects;
        private string _MatrixPath;
        readonly List<PictureBox> _PictureBoxes = new();

        public MappingForm(ConfigStruct config, List<ImageObject> imageObjects, string matrixPath)
        {
            InitializeComponent();
            _VideoPointsFlag = false;
            _VideoPointsCounts = new Dictionary<int, int>();
            _MappingMatrix = new Dictionary<int, List<double[]>>();
            _VideoPoints = new List<Tuple<float, float>>();
            _FixedVideoPoints = new Dictionary<int, List<Point2f[]>>();
            _Config = config;
            _ImageObjects = imageObjects;
            _MatrixPath = matrixPath;
            
            
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

            _MappingMatrix[0] = new List<double[]>();
            _MappingMatrix[1] = new List<double[]>();
            _MappingMatrix[2] = new List<double[]>();
            _MappingMatrix[3] = new List<double[]>();

            _FixedVideoPoints[0] = new List<Point2f[]>();
            _FixedVideoPoints[1] = new List<Point2f[]>();
            _FixedVideoPoints[2] = new List<Point2f[]>();
            _FixedVideoPoints[3] = new List<Point2f[]>();
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
                int pictureBoxIdx;
                if (sender.Equals(Video1_pictureBox)) { pictureBoxIdx = 0; }
                else if (sender.Equals(Video2_pictureBox)) { pictureBoxIdx = 1; }
                else if (sender.Equals(Video3_pictureBox)) { pictureBoxIdx = 2; }
                else { pictureBoxIdx = 3; }

                if (_TargetVideoIdx == -1)
                    _TargetVideoIdx = pictureBoxIdx;
                if (_TargetVideoIdx == pictureBoxIdx)
                {
                    if (sender.GetType() == _PictureBoxes[pictureBoxIdx].GetType())
                    {
                        PictureBox pic = (PictureBox)sender;
                        if (((MouseEventArgs)e).Button == MouseButtons.Left)
                        {
                            Graphics g = _PictureBoxes[pictureBoxIdx].CreateGraphics();
                            if (_VideoPointsCounts[pictureBoxIdx] == 4)
                            {
                                return;
                            }
                            int x = Control.MousePosition.X;
                            int y = Control.MousePosition.Y;

                            System.Drawing.Point mousePos = new System.Drawing.Point(x, y); //프로그램 내 좌표
                            System.Drawing.Point mousePosPtoClient = pic.PointToClient(mousePos);  //picbox 내 좌표
                            var test = _PictureBoxes[pictureBoxIdx].Size;
                            var widthRate = (float)_PictureBoxes[pictureBoxIdx].Size.Width / (float)_PictureBoxes[pictureBoxIdx].BackgroundImage.Size.Width;
                            var heightRate = (float)_PictureBoxes[pictureBoxIdx].Size.Height / (float)_PictureBoxes[pictureBoxIdx].BackgroundImage.Size.Height;

                            var xPoint = (float)mousePosPtoClient.X / widthRate;
                            var yPoint = (float)mousePosPtoClient.Y / heightRate;

                            _VideoPoints.Add(new Tuple<float, float>(xPoint, yPoint));
                            _VideoPointsCounts[pictureBoxIdx]++;
                            g.FillEllipse(Brushes.Red, mousePosPtoClient.X - 5, mousePosPtoClient.Y - 5, 10, 10);
                        }
                        if (((MouseEventArgs)e).Button == MouseButtons.Right)
                        {
                            //do something
                        }
                    }
                }
            }

        }

        private void Video_Points_Click(object sender, EventArgs e)
        {
            if (_TargetVideoIdx != -1)
                _PictureBoxes[_TargetVideoIdx].Image = null;
            _TargetVideoIdx = -1;

            _VideoPointsFlag = true;
            _VideoPoints.Clear();
            
            _VideoPointsCounts[0] = 0;
            _VideoPointsCounts[1] = 0;
            _VideoPointsCounts[2] = 0;
            _VideoPointsCounts[3] = 0;

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

                Point2f[] dstPoint = new Point2f[4];
                dstPoint[0] = new Point2f(_PlanPoints[0].Item1, _PlanPoints[0].Item2);
                dstPoint[1] = new Point2f(_PlanPoints[1].Item1, _PlanPoints[1].Item2);
                dstPoint[2] = new Point2f(_PlanPoints[2].Item1, _PlanPoints[2].Item2);
                dstPoint[3] = new Point2f(_PlanPoints[3].Item1, _PlanPoints[3].Item2);

                Mat matrix = Cv2.GetPerspectiveTransform(srcPoint, dstPoint);
                double[] copied = new double[matrix.Total() * matrix.Channels()];
                matrix.GetArray<double>(out copied);

                _MappingMatrix[_TargetVideoIdx].Add(copied);
                _FixedVideoPoints[_TargetVideoIdx].Add(srcPoint);

                _PictureBoxes[_TargetVideoIdx].Image = null;
                planPictureBox.Image = null;
                _TargetVideoIdx = -1;

                _VideoPointsFlag = false;
                _VideoPoints.Clear();
                _VideoPointsCounts[_TargetVideoIdx] = 0;
                btnVideoPoints.BackColor = Color.FromArgb(210, 210, 210);

                _PlanPointsFlag = false;
                btnPlanPoints.Enabled = true;
                btnPlanPoints.BackColor = Color.FromArgb(210, 210, 210);
            }
        }

        private void Analysis_button_Click(object sender, EventArgs e)
        {
            foreach (var matrices in _MappingMatrix.Values)
            {
                if (matrices.Count == 0) return;
            }
            var seperates = GetSeperates();
            var mappingMatrices = GetMatrices();
            
            MappingMatrix mappingMatrix = new MappingMatrix()
            {
                Seperates = seperates,
                Matrices = mappingMatrices
            };
            var serializer = new YamlDotNet.Serialization.SerializerBuilder().Build();
            var yaml = serializer.Serialize(mappingMatrix);
            System.IO.File.WriteAllText(_MatrixPath + "\\MappingMatrix.yaml", yaml);
            
            
        }
        private Dictionary<int, List<float[]>> GetSeperates()
        {
            float[] parameter = null;
            Dictionary<int, List<float[]>> seperates = new Dictionary<int, List<float[]>>();
            seperates[0] = new List<float[]>();
            seperates[1] = new List<float[]>();
            seperates[2] = new List<float[]>();
            seperates[3] = new List<float[]>();

            foreach (var idx in _FixedVideoPoints.Keys)
            {
                if (_FixedVideoPoints[idx].Count == 2)
                {
                    parameter = GetParameter(_FixedVideoPoints[idx][0], _FixedVideoPoints[idx][1]);
                    seperates[idx].Add(parameter);
                }
                else if (_FixedVideoPoints[idx].Count == 3)
                {
                    parameter = GetParameter(_FixedVideoPoints[idx][0], _FixedVideoPoints[idx][1]);
                    seperates[idx].Add(parameter);
                    parameter = GetParameter(_FixedVideoPoints[idx][1], _FixedVideoPoints[idx][2]);
                    seperates[idx].Add(parameter);
                }
            }
            

            return seperates;
        }

        private Dictionary<int, List<double[]>> GetMatrices()
        {
            Dictionary<int, List<double[]>> matrices = new Dictionary<int, List<double[]>>();
            matrices[0] = new List<double[]>();
            matrices[1] = new List<double[]>();
            matrices[2] = new List<double[]>();
            matrices[3] = new List<double[]>();

            foreach (var idx in _MappingMatrix.Keys)
            {
                foreach (var mat in _MappingMatrix[idx])
                {
                    matrices[idx].Add(mat);
                }
            }
            return matrices;
        }
        
        private float[] GetParameter(Point2f[] points1, Point2f[] points2)
        {
            var xCenter1 = (points1[2].X + points2[2].X) / 2;
            var yCenter1 = (points1[2].Y + points2[2].Y) / 2;

            var xCenter2 = (points1[3].X + points2[3].X) / 2;
            var yCenter2 = (points1[3].Y + points2[3].Y) / 2;

            var gradient = (yCenter1 - yCenter2) / (xCenter1 - xCenter2);
            var constant = yCenter1 - gradient * xCenter1;

            return new float[] { gradient, constant };
        }
    }
}