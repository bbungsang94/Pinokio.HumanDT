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
using DevExpress.XtraCharts;
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
        private string _PlanPath;

        private List<string> _VideoList = new();

        private ConfigStruct _Config;
        public AnalysisForm(List<ImageObject> imageObjects, ConfigStruct config, Process process)
        {
            InitializeComponent();
            _PictureBoxes.Add(pictureBox1);
            _PictureBoxes.Add(pictureBox2);
            _PictureBoxes.Add(pictureBox3);
            _PictureBoxes.Add(pictureBox4);
            _Process = new Process();
            _Config = config;
            _ImageObjects = imageObjects;
            SplashScreenManager.ShowForm(typeof(ProgressForm));

            this.SimpleChart.Series.Add(new Series("Utilization", ViewType.Bar));
            this.SimpleChart.Titles.Add(new ChartTitle { Text = "Simple Utillization Chart", TextColor = Color.White });
            this.SimpleChart.BackColor = Color.FromArgb(60, 60, 60);
            this.DetailedChart.Series.Add(new Series("Detailed Utilization", ViewType.StackedBar));
            this.DetailedChart.Titles.Add(new ChartTitle { Text = "Detailed Utillization Chart", TextColor = Color.White });
            this.DetailedChart.BackColor = Color.FromArgb(60, 60, 60);
            this.WorkinfoChart.Series.Add(new Series("WorkInfo", ViewType.Bar));
            this.WorkinfoChart.Titles.Add(new ChartTitle { Text = "WorkInfo Chart", TextColor = Color.White });
            this.WorkinfoChart.BackColor = Color.FromArgb(60, 60, 60);
            this.DistanceChart.Series.Add(new Series("Detailed Utilization", ViewType.Bar));
            this.DistanceChart.Titles.Add(new ChartTitle { Text = "Distance Chart", TextColor = Color.White });
            this.DistanceChart.BackColor = Color.FromArgb(60, 60, 60);

            //this.ChartStackBar.Series.Add(new Series("DetailedUtiliztion", ViewType.StackedBar));
            //InitializeChartControl(this.ChartStackBar);
            this.DetailedChart.Visible = false;


            #region Python 실행
            string program_path = Application.StartupPath;
            System.IO.DirectoryInfo directory = new System.IO.DirectoryInfo(program_path);
            directory = GetParent(6, directory);
            System.IO.FileInfo[] filepath = directory.GetFiles("main.py", System.IO.SearchOption.AllDirectories);
            _Config.FilePath = filepath[0].DirectoryName;

            this.StartAnalyse(_Config);

            //_ProcessInfo.FileName = @"D:\test\pythontest.bat";
            //_Process.StartInfo = _ProcessInfo;
            //_Process.Start();
            //new Thread(new ThreadStart(StartAnalyse)).Start();
            //var analyseThread = new Thread(() => StartAnalyse());
            //analyseThread.Start();

            //_ProcessInfo.FileName = "cmd.exe";

            //_ProcessInfo.WindowStyle = ProcessWindowStyle.Hidden;
            //_ProcessInfo.CreateNoWindow = true; //flase가 띄우기, true가 안 띄우기
            //_ProcessInfo.UseShellExecute = false;

            //_ProcessInfo.RedirectStandardInput = true;
            //_ProcessInfo.RedirectStandardOutput = true;
            //_ProcessInfo.RedirectStandardError = true;

            //_Process.StartInfo = _ProcessInfo;

            //_Process.Start();
            //_Process.PriorityBoostEnabled = true;
            //_Process.PriorityClass = ProcessPriorityClass.RealTime;

            //_Process.StandardInput.WriteLine($"conda activate {_Config.CondaEnv}");
            //if (_Config.FilePath.Contains("D:"))
            //{
            //    _Process.StandardInput.WriteLine("D:");
            //}
            //_Process.StandardInput.WriteLine("cd " + _Config.FilePath);
            //_Process.StandardInput.WriteLine("python main.py");

            //_Process.StandardInput.Close();
            Thread.Sleep(15000);
            #endregion
            _OutputPath = _Config.FilePath + "\\output";
            System.IO.DirectoryInfo di = new System.IO.DirectoryInfo(_OutputPath);
            _OutputPath = _OutputPath + "\\" + di.GetDirectories()[0].Name;
            _TrackingPath = _OutputPath + "\\" + "tracking_result";
            _PlanPath = _OutputPath + "\\" + "plan_result\\";
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
                    CurrentName = GetImageName(_ImageObjects[i].FrameCount, 15)
                };
                _TrackingObjects.Add(temp_object);
                _ImageRead.Add(true);
            }
            SplashScreenManager.CloseForm();

            TimerStart();
        }
        private void StartAnalyse(ConfigStruct config)
        {
            try
            {
                using (System.IO.StreamWriter sw = new System.IO.StreamWriter(config.FilePath + "\\main.bat"))
                {
                    sw.WriteLine("@echo off");
                    sw.WriteLine($"call conda activate {config.CondaEnv}");
                    if (config.FilePath.Contains("D:"))
                        sw.WriteLine("d:");
                    sw.WriteLine("cd " + config.FilePath);
                    sw.WriteLine("python main.py");
                    sw.WriteLine("call conda deactivate");
                }
                _ProcessInfo.FileName = config.FilePath + "\\main.bat";
                _Process.StartInfo = _ProcessInfo;
                _Process.Start();

            }
            catch (Exception ex)
            {
                MessageBox.Show("Error", ex.Message);
            }
        }
        private void UpdateSimpleChart(ChartControl chart, DataTable dt)
        {
            switch (chart.Name)
            {
                case "SimpleChart":
                    chart.DataSource = ConvertSimple(dt);
                    break;
                case "DetailedChart":
                    chart.DataSource = ConvertDetailed(dt);
                    chart.SeriesTemplate.ChangeView(ViewType.StackedBar);
                    break;
                case "WorkinfoChart":
                    chart.DataSource = ConvertWorkinfo(dt);
                    break;
                case "DistanceChart":
                    chart.DataSource = ConvertDistance(dt);
                    break;
            }
            chart.SeriesTemplate.SeriesDataMember = "Item";
            chart.SeriesTemplate.SetDataMembers("Name", "Values");

            chart.SeriesTemplate.LabelsVisibility = DevExpress.Utils.DefaultBoolean.True;
            chart.SeriesTemplate.Label.TextPattern = "{V:F3}";
            ((BarSeriesLabel)chart.SeriesTemplate.Label).Position = BarSeriesLabelPosition.Center;

            //SideBySideBarSeriesView view = (SideBySideBarSeriesView)chart.SeriesTemplate.View;
            //view.BarWidth = 0.5;

            XYDiagram diagram = (XYDiagram)chart.Diagram;
            diagram.DefaultPane.BackColor = Color.FromArgb(60, 60, 60);
            //chart.LookAndFeel.SkinName = "Visual Studio 2013 Dark";
            //chart.LookAndFeel.SkinMaskColor = Color.FromArgb(40, 40, 40);
            //chart.LookAndFeel.SkinMaskColor2 = Color.FromArgb(40, 40, 40);
            diagram.AxisX.Tickmarks.MinorVisible = false;
            diagram.AxisX.Label.TextColor = Color.White;
            diagram.AxisY.Label.TextColor = Color.White;
            diagram.AxisY.WholeRange.SideMarginsValue = 0;
            diagram.AxisY.WholeRange.SetMinMaxValues(0, 100);
            diagram.AxisY.Tickmarks.MinorVisible = true;
            diagram.AxisX.Tickmarks.MinorVisible = false;
            diagram.AxisY.GridLines.Visible = false;
            diagram.AxisX.Label.Angle = -60;
            diagram.AxisX.Label.ResolveOverlappingOptions.AllowStagger = true;
            diagram.AxisX.Label.ResolveOverlappingOptions.AllowHide = false;
            diagram.AxisX.Label.ResolveOverlappingOptions.AllowRotate = true;
            diagram.AxisX.Label.ResolveOverlappingOptions.MinIndent = 1;
            diagram.AxisX.QualitativeScaleOptions.AutoGrid = false;

            chart.Legend.Visibility = DevExpress.Utils.DefaultBoolean.False;
        }
        private void UpdateDetailChart(ChartControl chart, DataTable dt)
        {
            chart.DataSource = ConvertDetailed(dt);
            chart.SeriesTemplate.SeriesDataMember = "Item";
            chart.SeriesTemplate.SetDataMembers("Name", "Values");

            chart.SeriesTemplate.LabelsVisibility = DevExpress.Utils.DefaultBoolean.True;
            ((BarSeriesLabel)chart.SeriesTemplate.Label).Position = BarSeriesLabelPosition.Center;

            SideBySideBarSeriesView view = (SideBySideBarSeriesView)chart.SeriesTemplate.View;
            view.BarWidth = 0.5;

            XYDiagram diagram = (XYDiagram)chart.Diagram;
            diagram.AxisX.Tickmarks.MinorVisible = false;
            diagram.AxisX.Label.Angle = -60;
            diagram.AxisX.Label.ResolveOverlappingOptions.AllowStagger = true;
            diagram.AxisX.Label.ResolveOverlappingOptions.AllowHide = false;
            diagram.AxisX.Label.ResolveOverlappingOptions.AllowRotate = true;
            diagram.AxisX.Label.ResolveOverlappingOptions.MinIndent = 1;
            diagram.AxisX.QualitativeScaleOptions.AutoGrid = false;

            chart.Legend.Visibility = DevExpress.Utils.DefaultBoolean.False;
        }
        private DataTable ConvertSimple(DataTable dt)
        {
            DataTable newDT = new DataTable();
            newDT.Columns.AddRange(new DataColumn[] { new DataColumn("Item", typeof(string)), new DataColumn("Name", typeof(string)), new DataColumn("Values", typeof(double)) });
            foreach (DataRow dr in dt.Rows)
            {
                if (double.Parse(dr["VVARatio"].ToString()) == 0)
                    continue;
                newDT.Rows.Add("Utilization", dr["Name"], dr["VVARatio"]);
            }
            return newDT;
        }
        private DataTable ConvertDetailed(DataTable dt)
        {
            DataTable newDT = new DataTable();
            newDT.Columns.AddRange(new DataColumn[] { new DataColumn("Item", typeof(string)), new DataColumn("Name", typeof(string)), new DataColumn("Values", typeof(double)) });
            foreach (DataRow dr in dt.Rows)
            {
                if (double.Parse(dr["도크 진입"].ToString()) == 0 && double.Parse(dr["트레일러 작업"].ToString()) == 0 && double.Parse(dr["지게차 적재이동"].ToString()) == 0
                    && double.Parse(dr["1차 하역"].ToString()) == 0 && double.Parse(dr["빈 지게차 이동"].ToString()) == 0 && double.Parse(dr["N/A"].ToString()) == 0)
                    continue;
                newDT.Rows.Add("In", dr["Name"], double.Parse(dr["도크 진입"].ToString()) / double.Parse(dr["TotalTime"].ToString()) * 100);
                newDT.Rows.Add("Ready", dr["Name"], double.Parse(dr["트레일러 작업"].ToString()) / double.Parse(dr["TotalTime"].ToString()) * 100);
                newDT.Rows.Add("LoadedMove", dr["Name"], double.Parse(dr["지게차 적재이동"].ToString()) / double.Parse(dr["TotalTime"].ToString()) * 100);
                newDT.Rows.Add("Put", dr["Name"], double.Parse(dr["1차 하역"].ToString()) / double.Parse(dr["TotalTime"].ToString()) * 100);
                newDT.Rows.Add("EmptyMove", dr["Name"], double.Parse(dr["빈 지게차 이동"].ToString()) / double.Parse(dr["TotalTime"].ToString()) * 100);
                newDT.Rows.Add("N/A", dr["Name"], double.Parse(dr["N/A"].ToString()) / double.Parse(dr["TotalTime"].ToString()) * 100);
                newDT.Rows.Add("이동 거리", dr["Name"], double.Parse(dr["이동 거리"].ToString()));
                newDT.Rows.Add("작업 수", dr["Name"], double.Parse(dr["작업 수"].ToString()));
            }
            return newDT;

        }
        private DataTable ConvertWorkinfo(DataTable dt)
        {
            DataTable newDT = new DataTable();
            newDT.Columns.AddRange(new DataColumn[] { new DataColumn("Item", typeof(string)), new DataColumn("Name", typeof(string)), new DataColumn("Values", typeof(double)) });

            foreach (DataRow dr in dt.Rows)
            {
                if (double.Parse(dr["작업 수"].ToString()) == 0)
                    continue;
                newDT.Rows.Add("작업 수", dr["Name"], double.Parse(dr["작업 수"].ToString()));
            }
            return newDT;
        }
        private DataTable ConvertDistance(DataTable dt)
        {
            DataTable newDT = new DataTable();
            newDT.Columns.AddRange(new DataColumn[] { new DataColumn("Item", typeof(string)), new DataColumn("Name", typeof(string)), new DataColumn("Values", typeof(double)) });

            foreach (DataRow dr in dt.Rows)
            {
                if (double.Parse(dr["이동 거리"].ToString()) == 0)
                    continue;
                newDT.Rows.Add("이동 거리", dr["Name"], double.Parse(dr["이동 거리"].ToString()));
            }
            return newDT;
        }
        private void TimerStart()
        {
            Timer timer = new();
            timer.Interval = 200;
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
            LoadResult();
            LoadPlanImage();
            for (int i = 0; i < _VideoList.Count; i++)
            {
                if (_ImageRead[i])
                {
                    LoadImage(i, true);
                }
            }

        }
        private void LoadResult()
        {
            System.Text.Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
            DataTable dt = new DataTable();
            List<FolkliftInfo> infoList = new List<FolkliftInfo>();
            try
            {
                //using (var sr = new System.IO.StreamReader(_OutputPath + "\\" + "raw_data.csv", Encoding.GetEncoding(51949)))
                using (var fs = new System.IO.FileStream(_OutputPath + "\\" + "raw_data.csv", System.IO.FileMode.Open, System.IO.FileAccess.Read, System.IO.FileShare.ReadWrite))
                {
                    using (var sr = new System.IO.StreamReader(fs, Encoding.GetEncoding(51949)))
                    {
                        int count = 0;
                        while (!sr.EndOfStream)
                        {
                            string array = sr.ReadLine();
                            string[] values = array.Split(',');
                            if (array.Contains("N/A"))
                            {
                                dt.Columns.Add("Name");
                                for (int i = 1; i < values.Length; i++)
                                {
                                    dt.Columns.Add(values[i]);
                                }
                                dt.Columns.Add("VVARatio");
                                dt.Columns.Add("TotalTime");
                                continue;
                            }

                            FolkliftInfo info = new FolkliftInfo()
                            {
                                Name = values[0],
                                In = double.Parse(values[1]),
                                Ready = double.Parse(values[2]),
                                LoadedMove = double.Parse(values[3]),
                                Put = double.Parse(values[4]),
                                EmptyMove = double.Parse(values[5]),
                                NA = double.Parse(values[6]),
                                Distance = double.Parse(values[7]),
                                WorkCount = double.Parse(values[8])
                            };
                            infoList.Add(info);
                        }
                    }
                }
                for (int i = 0; i < infoList.Count; i++)
                {
                    dt.Rows.Add(new object[]
                    {
                    infoList[i].Name,
                    infoList[i].In,
                    infoList[i].Ready,
                    infoList[i].LoadedMove,
                    infoList[i].Put,
                    infoList[i].EmptyMove,
                    infoList[i].NA,
                    infoList[i].Distance,
                    infoList[i].WorkCount,
                    infoList[i].VVARatio,
                    infoList[i].TotalTime,
                    });
                }
                this.UpdateSimpleChart(this.SimpleChart, dt);
                this.UpdateSimpleChart(this.DetailedChart, dt);
                this.UpdateSimpleChart(this.WorkinfoChart, dt);
                this.UpdateSimpleChart(this.DistanceChart, dt);
            }
            catch { }

        }
        private void LoadPlanImage()
        {
            var obj = _TrackingObjects[0];
            try
            {
                obj.CurrentName = GetImageName(obj.FrameCount, obj.FrameRate);
                Image image = Image.FromFile(_PlanPath + obj.CurrentName);

                pictureBox5.BackgroundImage = image;
            }
            catch
            {
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
                obj.CurrentName = GetImageName(obj.FrameCount, obj.FrameRate);
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
                //_ImageRead[idx] = false;
            }
        }

        private void SimpleChart_Click(object sender, EventArgs e)
        {
            SimpleChart.Visible = true;
            DetailedChart.Visible = false;
            pictureBox5.Visible = false;
            WorkinfoChart.Visible = false;
            DistanceChart.Visible = false;
        }

        private void Trajectory_Click(object sender, EventArgs e)
        {
            SimpleChart.Visible = false;
            DetailedChart.Visible = false;
            pictureBox5.Visible = true;
            WorkinfoChart.Visible = false;
            DistanceChart.Visible = false;
        }

        private void DetailChart_Click(object sender, EventArgs e)
        {
            SimpleChart.Visible = false;
            DetailedChart.Visible = true;
            pictureBox5.Visible = false;
            WorkinfoChart.Visible = false;
            DistanceChart.Visible = false;
        }

        private void WorkinfoChart_Click(object sender, EventArgs e)
        {
            SimpleChart.Visible = false;
            DetailedChart.Visible = false;
            pictureBox5.Visible = false;
            WorkinfoChart.Visible = true;
            DistanceChart.Visible = false;
        }

        private void DistanceChart_Click(object sender, EventArgs e)
        {
            SimpleChart.Visible = false;
            DetailedChart.Visible = false;
            pictureBox5.Visible = false;
            WorkinfoChart.Visible = false;
            DistanceChart.Visible = true;
        }
    }
}