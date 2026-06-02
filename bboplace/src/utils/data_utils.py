from collections import OrderedDict
import torch 
import numpy as np 

class FeatureCache:
    def __init__(self, input_type='torch', max_size=2500):
        self.input_type = input_type
        self.cache = OrderedDict()
        self.max_size = max_size

    def _get_key(self, x):
        if isinstance(x, torch.Tensor) and x.dim() > 1:
            return tuple(map(tuple, x.tolist()))
        else:
            return tuple(x.tolist())
    
    def __len__(self):
        return len(self.cache)

    def push(self, x):
        if isinstance(x, torch.Tensor) and x.dim() > 1:
            features = []
            for sample in x:
                feature = self.get(sample)
                if feature is None:
                    feature = self._featurize(sample, self.input_type)
                    self._put(self._get_key(sample), feature)
                features.append(feature)
            return torch.stack(features)
        else:
            feature = self.get(x)
            if feature is None:
                feature = self._featurize(x, self.input_type)
                self._put(self._get_key(x), feature)
            return feature

    def get(self, x):
        key = self._get_key(x)
        if key in self.cache:
            # Move the key to the end to show that it was recently accessed
            self.cache.move_to_end(key)
            return self.cache[key]
        else:
            return None
    
    # LRU strategy
    def _put(self, key, value):
        if key in self.cache:
            # Update the key and move it to the end
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # Remove the first item from the ordered dictionary
                self.cache.popitem(last=False)
        self.cache[key] = value
    
    def _featurize(self, x, ret_type='torch'):
        if x.dim() == 1:
            featurize_x = []
            for i in range(len(x)):
                for j in range(i+1, len(x)):
                    featurize_x.append(1 if x[i] > x[j] else -1)
            if ret_type == 'torch':
                featurize_x = torch.tensor(featurize_x, dtype=torch.float)
            elif ret_type == 'numpy':
                featurize_x = np.array(featurize_x, dtype=np.float64)
            else:
                assert 0
            normalizer = np.sqrt(len(x) * (len(x) - 1) / 2)
            return featurize_x / normalizer
        else: 
            assert x.dim() == 2  
            batch_size, num_features = x.shape
            comparison = x.unsqueeze(2) > x.unsqueeze(1)

            comparison = torch.tril(comparison, diagonal=-1) * 2 - 1
            featurize_x = comparison[comparison != 0].view(batch_size, -1)

            normalizer = torch.sqrt(torch.tensor(num_features * (num_features - 1) / 2, dtype=torch.float))
            featurize_x = featurize_x / normalizer

            return featurize_x