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
using YamlDotNet;

namespace HumanDT.UI
{
    public partial class MappingForm : DevExpress.XtraEditors.XtraForm
    {
        private bool _Video_points_flag;
        private int _Video_points_count;
        private List<int> _XPonts;
        private List<int> _YPonts;
        private ConfigStruct _Config;
        private List<VideoInfo> _VideoInfoList;
        public MappingForm(ConfigStruct config)
        {
            InitializeComponent();
            _Video_points_flag = false;
            _Video_points_count = 0;
            _XPonts = new List<int>();
            _YPonts = new List<int>();
            _Config = config;
            System.IO.DirectoryInfo di = new System.IO.DirectoryInfo(_Config.SavePath);
            _VideoInfoList = new List<VideoInfo>();
            foreach (System.IO.FileInfo file in di.GetFiles("*.yaml"))
            {
                var input = new System.IO.StreamReader(file.FullName);
                var yaml = new YamlDotNet.Serialization.Deserializer();
                _VideoInfoList.Add(yaml.Deserialize<VideoInfo>(input));
            }
        }

        private void Video_Points_Click(object sender, EventArgs e)
        {
            _Video_points_flag = true;
        }

        private void Plan_Points_Click(object sender, EventArgs e)
        {
            

        }

        private void Video1_pictureBox_Click(object sender, EventArgs e)
        {
            if (_Video_points_flag)
            {
                if (sender.GetType() == Video1_pictureBox.GetType())
                {
                    PictureBox pic = (PictureBox)sender;
                    int x = Control.MousePosition.X;
                    int y = Control.MousePosition.Y;

                    Point mousePos = new Point(x, y); //프로그램 내 좌표
                    Point mousePosPtoClient = pic.PointToClient(mousePos);  //picbox 내 좌표

                    // 좌표 이미지 원본 크기에 맞게 바꿔줘야함
                    if (((MouseEventArgs)e).Button == MouseButtons.Left)
                    {

                        //do something                    

                    }

                    if (((MouseEventArgs)e).Button == MouseButtons.Right)
                    {
                        //do something

                    }
                }
            }
        }
    }
}