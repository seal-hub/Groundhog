import logging
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)


#The background is set with 40 plus the number of the color, and the foreground with 30


#These are the sequences need to get colored ouput
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[0;%dm"
BOLD_COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"


def fix_formatter(logger_format: str, use_color=True):
    if use_color:
        logger_format = logger_format.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        logger_format = logger_format.replace("$RESET", "").replace("$BOLD", "")
    return logger_format


COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
}


def colorize(message: str, color: int = WHITE, bold: bool = False) -> str:
    color_seq = BOLD_COLOR_SEQ if bold else COLOR_SEQ
    return color_seq % (30+color) + message + RESET_SEQ


DETAILED_LOGGER_FORMAT = f'%(module)-25s - %(funcName)-30s %(asctime)s.%(msecs)03d %(levelname)-20s: %(message)s'
SIMPLE_LOGGER_FORMAT = f'%(levelname)20s: %(message)s'
LOGGER_DATE_FORMAT = f'%m-%d {colorize("%H:%M:%S", bold=True)}'


class ColoredFormatter(logging.Formatter):
    def __init__(self, detailed: bool = False, use_color=True):
        logger_format = fix_formatter(DETAILED_LOGGER_FORMAT if detailed else SIMPLE_LOGGER_FORMAT, use_color=use_color)
        logging.Formatter.__init__(self, logger_format, LOGGER_DATE_FORMAT)
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            record.levelname = colorize(levelname, COLORS[levelname], levelname == 'ERROR')
        return logging.Formatter.format(self, record)


