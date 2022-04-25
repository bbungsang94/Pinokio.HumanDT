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
    public partial class AnalysisForm : DevExpress.XtraEditors.XtraForm
    {
        public AnalysisForm(List<ImageObject> imageObjects)
        {
            InitializeComponent();
        }

        private void Close_button_Click(object sender, EventArgs e)
        {
            this.Close();
        }
    }
}