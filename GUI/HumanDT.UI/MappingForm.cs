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
        private bool _Video_points_flag = false;
        private int _Video_points_count = 0;
        private List<int> _XPonts;
        private List<int> _YPonts;
        public MappingForm()
        {
            InitializeComponent();
            _Video_points_flag = false;
            _Video_points_count = 0;
            _XPonts = new List<int>();
            _YPonts = new List<int>();
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