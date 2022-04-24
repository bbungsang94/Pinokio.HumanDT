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
        private bool _video_points_flag = false;
        private int _video_points_count = 0;
        public MappingForm()
        {
            InitializeComponent();
        }

        private void Video_Points_Click(object sender, EventArgs e)
        {
            _video_points_flag = true;
        }

        private void Plan_Points_Click(object sender, EventArgs e)
        {
            

        }

        private void Video1_pictureBox_Click(object sender, EventArgs e)
        {
            if (_video_points_flag)
            {
                if (sender.GetType() == Video1_pictureBox.GetType())
                {
                    PictureBox pic = (PictureBox)sender;
                    int x = Control.MousePosition.X;
                    int y = Control.MousePosition.Y;

                    Point mousePos = new Point(x, y); //프로그램 내 좌표
                    Point mousePosPtoClient = pic.PointToClient(mousePos);  //picbox 내 좌표
                    Point mousePosPtoScreen = pic.PointToScreen(mousePos);  //스크린 내 좌표 (좌우 스크린 합친듯?)

                    this.Text = x.ToString() + ", " + y.ToString() +
                        ", " + mousePosPtoClient.X.ToString() + ", " + mousePosPtoClient.Y.ToString() +
                        ", " + mousePosPtoScreen.X.ToString() + ", " + mousePosPtoScreen.Y.ToString();

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