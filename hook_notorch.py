import os
import sys

# Keep transformers in tokenizer-only mode and avoid touching torch.
os.environ.setdefault('USE_TORCH', '0')

_BLOCKED = {
    'torch', 'torchvision', 'torchaudio',
}


class _BlockHeavy:
    def find_module(self, name, path=None):
        if name in _BLOCKED:
            return self
        for blocked in _BLOCKED:
            if name.startswith(blocked + '.'):
                return self
        return None

    def load_module(self, name):
        raise ImportError(
            f'[BabelGG] Module blocked at runtime: {name}\n'
            f'This module is not needed at runtime.'
        )


sys.meta_path.insert(0, _BlockHeavy())
