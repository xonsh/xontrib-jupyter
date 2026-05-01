class NoSuchKernel(Exception):
    pass


class KernelSpec:
    def __init__(self, resource_dir="/tmp/xonsh-kernel", argv=None):
        self.resource_dir = resource_dir
        self.argv = argv or []


class KernelSpecManager:
    def get_kernel_spec(self, kernel_name):
        raise NoSuchKernel(kernel_name)

    def install_kernel_spec(self, source_dir, kernel_name, user=False, prefix=None):
        return None

    def remove_kernel_spec(self, kernel_name):
        return None

    def find_kernel_specs(self):
        return {}
