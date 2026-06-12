import time
import wx
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from splash_window import SplashWindow

def run_performance_test():
    app = wx.App()
    
    start_time = time.perf_counter()
    loop_times = []
    
    def on_finished():
        total_time = time.perf_counter() - start_time
        print(f"Total Splash Time: {total_time:.4f} seconds")
        print(f"Number of updates performed: {len(loop_times)}")
        if loop_times:
            avg_update = sum(loop_times) / len(loop_times)
            max_update = max(loop_times)
            min_update = min(loop_times)
            print(f"Average update duration: {avg_update*1000:.4f} ms")
            print(f"Min update duration: {min_update*1000:.4f} ms")
            print(f"Max update duration: {max_update*1000:.4f} ms")
        app.ExitMainLoop()

    splash = SplashWindow(on_finished)
    
    original_update = splash.update_layered_window_state
    def instrumented_update(alpha):
        t0 = time.perf_counter()
        original_update(alpha)
        t1 = time.perf_counter()
        loop_times.append(t1 - t0)
        
    splash.update_layered_window_state = instrumented_update
    splash.Show()
    
    timer_test = wx.Timer()
    def force_finish(event):
        splash.timer.Stop()
        splash.Close()
        on_finished()
        
    app.Bind(wx.EVT_TIMER, force_finish, timer_test)
    timer_test.StartOnce(5500)
    
    app.MainLoop()

if __name__ == "__main__":
    run_performance_test()
