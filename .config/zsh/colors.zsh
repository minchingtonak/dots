if [ "${LLM}" = "true" ]; then
    echo -ne '\033]11;#0a1c21\007'; # dark cyan bg for llm terminal
fi

# Manipulate colors 0-256
# \033]4;{index};{color}\007

# Change color 7 to #FFFFFF
# \033]4;7;#FFFFFF\007

# Change color 14 to #333333
# \033]4;14;#333333\007

# Manipulate special colors.
# 10 = foreground, 11 = background, 12 = cursor foregound
# 13 = mouse foreground, 708 = terminal border background
# \033]{index};{color}\007

# Change the terminal foreground to #FFFFFF
# \033]10;#FFFFFF\007

# Change the terminal background to #000000
# \033]11;#000000\007

# Change the terminal cursor to #FFFFFF
# \033]12;#FFFFFF\007

# Change the terminal border background to #000000
# \033]708;#000000\007
