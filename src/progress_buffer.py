# This Progress Buffer, is attached to a file, everytime it is changed it updates the buffer with the new content, and the file. 

class ProgressBuffer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.buffer = ""
        self.load_from_file()

    def load_from_file(self):
        try:
            with open(self.file_path, 'r') as f:
                self.buffer = f.read()
        except FileNotFoundError:
            self.buffer = ""

    def write(self, new_content):
        self.buffer = new_content
        with open(self.file_path, 'w') as f:
            f.write(self.buffer)


    def clear_buffer(self):
        self.buffer = ""
        with open(self.file_path, 'w') as f:
            f.write("")

    def get_buffer(self):
        return self.buffer