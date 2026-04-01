$action = New-ScheduledTaskAction -Execute "C:\Users\chen\AppData\Local\Programs\Python\Python312\python.exe" -Argument "E:\quant-trading-mvp\scripts\scheduled_macro_collector.py" -WorkingDirectory "E:\quant-trading-mvp"
$trigger = New-ScheduledTaskTrigger -Daily -At "08:00AM"
Register-ScheduledTask -TaskPath "\QuantTrading\" -TaskName "Macro-Collector-Daily" -Action $action -Trigger $trigger -Description "宏观数据采集" -RunLevel Highest -Force
