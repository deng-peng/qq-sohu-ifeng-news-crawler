import logging
import os.path


class Logger:
    def __init__(self, logname, logger):
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG)
        home = os.path.join(os.getcwdu(), 'log')
        if not os.path.exists(home):
            os.makedirs(home)
        fh = logging.FileHandler(os.path.join(home, logname))
        fh.setLevel(logging.ERROR)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def get_logger(self):
        return self.logger