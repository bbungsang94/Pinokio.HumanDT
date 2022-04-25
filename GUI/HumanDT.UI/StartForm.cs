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
    public partial class StartForm : DevExpress.XtraEditors.XtraForm
    {
        public StartForm()
        {
            InitializeComponent();
        }

        private void Close_button_Click(object sender, EventArgs e)
        {
            this.Close();
        }

        private void Start_button_Click(object sender, EventArgs e)
        {   
            MappingForm mapping_form = new MappingForm();
            mapping_form.ShowDialog();
            this.Close();
            //VideoForm video_form = new VideoForm();
            //video_form.ShowDialog();
            //this.Close();
        }
    }
}