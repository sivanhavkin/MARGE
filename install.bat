@echo off
echo.
echo  M@RGE - setup
echo  -----------------------------
echo.
echo  You will need two API keys:
echo  - Anthropic (claude.ai/settings)
echo  - OpenAI (platform.openai.com)
echo  (Press Enter to skip a key and leave it unchanged)
echo.

set anthropic_key=
set /p anthropic_key="  Anthropic API key: "
set openai_key=
set /p openai_key="  OpenAI API key: "

set "wrote_env="

if not "%anthropic_key%"=="" (
    echo ANTHROPIC_API_KEY=%anthropic_key%> .env
    set wrote_env=1
)

if not "%openai_key%"=="" (
    if defined wrote_env (
        echo OPENAI_API_KEY=%openai_key%>> .env
    ) else (
        echo OPENAI_API_KEY=%openai_key%> .env
    )
    set wrote_env=1
)

echo.
echo  * setup complete
echo  run M@RGE.py to begin
echo.
pause