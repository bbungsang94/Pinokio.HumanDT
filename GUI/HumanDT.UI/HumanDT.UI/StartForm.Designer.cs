namespace HumanDT.UI
{
    partial class StartForm
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.Start_button = new System.Windows.Forms.Button();
            this.SuspendLayout();
            // 
            // Start_button
            // 
            this.Start_button.FlatStyle = System.Windows.Forms.FlatStyle.Flat;
            this.Start_button.Font = new System.Drawing.Font("Tahoma", 48F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point);
            this.Start_button.Location = new System.Drawing.Point(240, 400);
            this.Start_button.Name = "Start_button";
            this.Start_button.Size = new System.Drawing.Size(240, 97);
            this.Start_button.TabIndex = 0;
            this.Start_button.Text = "Start";
            this.Start_button.UseVisualStyleBackColor = true;
            this.Start_button.FlatAppearance.BorderSize = 0;
            //this.Start_button.FlatAppearance.Co = 0;
            // 
            // StartForm
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(7F, 14F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.BackgroundImageLayoutStore = System.Windows.Forms.ImageLayout.Tile;
            this.BackgroundImageStore = global::HumanDT.UI.Properties.Resources.StartImage;
            this.ClientSize = new System.Drawing.Size(1920, 1080);
            this.Controls.Add(this.Start_button);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.None;
            this.Name = "StartForm";
            this.Text = "StartForm";
            this.WindowState = System.Windows.Forms.FormWindowState.Maximized;
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.Button Start_button;
    }
}