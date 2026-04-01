$action = New-ScheduledTaskAction -Execute "C:\Users\chen\AppData\Local\Programs\Python\Python312\python.exe" -Argument "E:\quant-trading-mvp\scripts\start_news_collector.py" -WorkingDirectory "E:\quant-trading-mvp"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskPath "\QuantTrading\" -TaskName "News-Collector" -Action $action -Trigger $trigger -Description "News Collector 30m" -RunLevel Highest -Force
