#!/bin/zsh

# remove any conflict
lsof -i :5007 -t | xargs -r kill

# start server in background
cd /Users/dunevv/WorkLocal/_AI_/HoudiniElf
python -m tools_Houdini.Houdini_Agentic_Mode.mcp_server --port 5007 &
sleep 0.2

# verify health
curl http://127.0.0.1:5007/health