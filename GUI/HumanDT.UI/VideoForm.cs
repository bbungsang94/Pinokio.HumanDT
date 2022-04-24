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

namespace HumanDT.UI
{
    public partial class VideoForm : Form
    {
        private ProcessStartInfo _processInfo = new ProcessStartInfo();
        private Process _process = new Process();
        public VideoForm()
        {
            InitializeComponent();
            this.TopMost = true;
        }

        private void panel1_Paint(object sender, PaintEventArgs e)
        {

        }

        private void Analysis_button_Click(object sender, EventArgs e)
        {
            #region Python 실행
            //실행할 파일 명 입력하기
            _processInfo.FileName = "cmd.exe";

            //cmd 창 띄우기
            _processInfo.WindowStyle = ProcessWindowStyle.Hidden;
            _processInfo.CreateNoWindow = true; //flase가 띄우기, true가 안 띄우기
            _processInfo.UseShellExecute = false;
            _processInfo.RedirectStandardInput = true;
            _processInfo.RedirectStandardOutput = true;
            _processInfo.RedirectStandardError = true;

            _process.StartInfo = _processInfo;
            _process.Start();

            //명령어 실행
            _process.StandardInput.Write(@"ipconfig" + Environment.NewLine);
            //_process.StandardInput.WriteLine("conda activate FLOM");
            //_process.StandardInput.WriteLine("D:");
            //_process.StandardInput.WriteLine(@"cd D:\source-D\respos-D\Pinokio.HumanDT\API");
            //_process.StandardInput.WriteLine("python main.py");

            _process.StandardInput.Close();

            Thread.Sleep(5000);

            string resultValue = _process.StandardOutput.ReadToEnd();

            _process.WaitForExit();

            _process.Close();
            #endregion

            DialogResult result = MessageBox.Show("실시간 분석 결과를 보겠습니까?", "최종 결과만 보기 위해서는 '아니요' 버튼을 눌러주세요.", MessageBoxButtons.YesNo);
            if(result == DialogResult.Yes)
            {
                AnalysisForm mainForm = new AnalysisForm();
                mainForm.ShowDialog();
                this.Close();
            }
            else if(result == DialogResult.No)
            {
                ProgressBar progressBar = new ProgressBar(_process);
                progressBar.Show();
            }
            
        }
    }
}
