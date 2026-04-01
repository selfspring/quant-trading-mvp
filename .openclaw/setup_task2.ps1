$action = New-ScheduledTaskAction -Execute "C:\Users\chen\AppData\Local\Programs\Python\Python312\python.exe" -Argument "E:\quant-trading-mvp\scripts\run_llm_analysis.py" -WorkingDirectory "E:\quant-trading-mvp"
Set-ScheduledTask -TaskPath "\QuantTrading\" -TaskName "LLM-Analysis-Morning" -Action $action
Set-ScheduledTask -TaskPath "\QuantTrading\" -TaskName "LLM-Analysis-Afternoon" -Action $action
Set-ScheduledTask -TaskPath "\QuantTrading\" -TaskName "LLM-Analysis-Night" -Action $action
