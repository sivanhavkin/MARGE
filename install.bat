@echo off
echo.
echo  M@RGE - setup
echo  -----------------------------
echo.
echo  You will need two API keys:
echo  - Anthropic (claude.ai/settings)
echo  - OpenAI (platform.openai.com)
echo.

set /p anthropic_key="  Anthropic API key: "
set /p openai_key="  OpenAI API key: "

echo ANTHROPIC_API_KEY=%anthropic_key% > .env
echo OPENAI_API_KEY=%openai_key% >> .env

echo.
echo  * setup complete
echo  run M@RGE.py to begin
echo.
pause