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

namespace HumanDT.UI
{
    public partial class ProgressBar : DevExpress.XtraEditors.XtraForm
    {
        private Process _process;
        public ProgressBar(Process process)
        {
            _process = process;
            InitializeComponent();
#if DEBUG
            this.TopMost = true;
#endif
        }

        private void Cancel_button_Click(object sender, EventArgs e)
        {
            _process.Close();
            this.Close();
        }
    }
}