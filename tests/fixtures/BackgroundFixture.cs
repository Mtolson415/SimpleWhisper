using System;
using System.Windows;
using System.Windows.Controls;

public class BackgroundFixture {
    [STAThread] public static void Main() {
        var window = new Window { Title = "Dictation background lock fixture", Width = 600, Height = 250 };
        var panel = new StackPanel { Margin = new Thickness(16) };
        var first = new TextBox { Name = "LockedField", Text = "Synthetic prefix: ", Margin = new Thickness(0,0,0,16) };
        var other = new TextBox { Name = "OtherField", Text = "Other field unchanged" };
        panel.Children.Add(first);
        panel.Children.Add(other);
        window.Content = panel;
        window.Loaded += (sender, args) => { first.Focus(); first.Select(first.Text.Length, 0); };
        new Application().Run(window);
    }
}
