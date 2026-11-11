using System;
using System.Windows;
using System.Windows.Controls;

public class RevisionFixture {
    [STAThread] public static void Main() {
        Window window = new Window();
        window.Title = "Dictation Revision Test";
        window.Width = 650;
        window.Height = 250;
        TextBox field = new TextBox();
        field.AcceptsReturn = true;
        field.FontSize = 22;
        field.Margin = new Thickness(16);
        window.Content = field;
        new Application().Run(window);
    }
}
