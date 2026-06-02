from gpytorch.constraints import Interval
from gpytorch.priors import Prior
from utils.debug import * 
from utils.data_utils import FeatureCache 
import torch 
from gpytorch.kernels import Kernel

tkwargs = {
    "dtype": torch.double,
    "device": torch.device("cuda" if torch.cuda.is_available() else "cpu")
}

feature_cache = FeatureCache() 

class CategoricalOverlap(Kernel):
    """Implementation of the categorical overlap kernel.
    This is the most basic form of the categorical kernel that essentially invokes a Kronecker delta function
    between any two elements.
    """

    has_lengthscale = True

    def __init__(self, **kwargs):
        super(CategoricalOverlap, self).__init__(has_lengthscale=True, **kwargs)

    def forward(self, x1, x2, diag=False, last_dim_is_batch=False, **params):
        # First, convert one-hot to ordinal representation

        diff = x1[:, None] - x2[None, :]
        # nonzero location = different cat
        diff[torch.abs(diff) > 1e-5] = 1
        # invert, to now count same cats
        diff1 = torch.logical_not(diff).float()
        if self.ard_num_dims is not None and self.ard_num_dims > 1:
            k_cat = torch.sum(self.lengthscale * diff1, dim=-1) / torch.sum(self.lengthscale)
        else:
            # dividing by number of cat variables to keep this term in range [0,1]
            k_cat = torch.sum(diff1, dim=-1) / x1.shape[1]
        if diag:
            return torch.diag(k_cat).to(**tkwargs)
        return k_cat.to(**tkwargs)

class TransformedCategorical(CategoricalOverlap):
    """
    Second kind of transformed kernel of form:
    $$ k(x, x') = \exp(\frac{\lambda}{n}) \sum_{i=1}^n [x_i = x'_i] )$$ (if non-ARD)
    or
    $$ k(x, x') = \exp(\frac{1}{n} \sum_{i=1}^n \lambda_i [x_i = x'_i]) $$ if ARD
    """

    has_lengthscale = True

    def forward_before(self, x1, x2, diag=False, last_dim_is_batch=False, exp='rbf', **params):
        # expand x1 and x2 to calc hamming distance
        # print(x1.shape, x2.shape, diag)
        is_dim_2 = len(x1.shape) == 2
        if is_dim_2:
            x1 = x1.unsqueeze(0)
        if is_dim_2:
            x2 = x2.unsqueeze(0)
        M1_expanded = x1.unsqueeze(2)
        M2_expanded = x2.unsqueeze(1)

        # calc hamming distance
        diff = (M1_expanded != M2_expanded)

        # (# batch, # batch)
        diff1 = diff
        def rbf(d, ard):
            if ard:
                return torch.exp(-torch.sum(d * self.lengthscale, dim=-1) / torch.sum(self.lengthscale))
            else:
                return torch.exp(-self.lengthscale * torch.sum(d, dim=-1) / x1.shape[1])

        def mat52(d, ard):
            raise NotImplementedError

        if exp == 'rbf':
            k_cat = rbf(diff1, self.ard_num_dims is not None and self.ard_num_dims > 1)
        elif exp == 'mat52':
            k_cat = mat52(diff1, self.ard_num_dims is not None and self.ard_num_dims > 1)
        else:
            raise ValueError('Exponentiation scheme %s is not recognised!' % exp)
        if diag:
            # highlight(k_cat, type(k_cat), k_cat.shape, x1.shape, x2.shape)
            diagonal = torch.diagonal(k_cat, offset=0, dim1=-2, dim2=-1).contiguous()
            return diagonal
        # print(k_cat.shape)
        if is_dim_2:
            k_cat = k_cat.squeeze(0)
        
        return k_cat.to(**tkwargs)
    
    def forward(self, x1, x2, diag=False, last_dim_is_batch=False, exp='rbf', **params):
        if x1.dim() <= 3:
            return self.forward_before(x1, x2, diag, last_dim_is_batch, exp, **params)
        else:
            # Check input shapes
            # print(x1.shape, x2.shape)
            batch_size1, l, n1, m = x1.shape
            batch_size2, _, n2, _ = x2.shape
            
            assert batch_size2 == batch_size1

            # Expand x1 and x2 to calculate the Hamming distance
            M1_expanded = x1.unsqueeze(3)  # Shape: (batch_size, l, n1, 1, m)
            M2_expanded = x2.unsqueeze(2)  # Shape: (batch_size, l, 1, n2, m)

            # Calculate Hamming distance
            hamming_dist = (M1_expanded != M2_expanded).float().sum(dim=-1)  # Shape: (batch_size, l, n1, n2)

            # Extract lengthscale and determine if ARD is used
            # lengthscale = params.get('lengthscale', torch.ones(m, device=x1.device, dtype=x1.dtype))
            # ard = params.get('ard', False)

            # Define the RBF kernel function
            def rbf(d, ard=False):
                if ard:
                    # Apply lengthscale per dimension
                    return torch.exp(-torch.sum(d / self.lengthscale, dim=-1))
                else:
                    # Apply a single lengthscale to all dimensions
                    return torch.exp(-self.lengthscale * d)

            # Define the Matern 5/2 kernel function (not implemented)
            def mat52(d):
                raise NotImplementedError

            # Calculate the kernel matrix
            if exp == 'rbf':
                k_cat = rbf(hamming_dist)
            elif exp == 'mat52':
                k_cat = mat52(hamming_dist)
            else:
                raise ValueError('Exponentiation scheme %s is not recognized!' % exp)

            if diag:
                # Assuming k_cat is at least 2D and you need the diagonal from the last two dimensions
                diagonal = torch.diagonal(k_cat, offset=0, dim1=-2, dim2=-1).contiguous()
                return diagonal

            # assert 0, k_cat.shape
            return k_cat  # Shape: (batch_size, l, n1, n2)

class OrderKernel(Kernel):
    has_lengthscale = True

    def forward(self, X, X2, **params):
        global feature_cache
        if len(X.shape) > 2:
            assert X.shape[0] == X2.shape[0]
            batch_size = X.shape[0]

            x1 = feature_cache.push(X).to(**tkwargs)
            x2 = feature_cache.push(X2).to(**tkwargs)

            mat = (x1.unsqueeze(2) - x2.unsqueeze(1)).pow(2).sum(dim=-1)
            mat = torch.exp(-self.lengthscale * mat)

            mat = mat.view(batch_size, -1, mat.shape[-1])
            return mat
        else:
            mat = torch.zeros((len(X), len(X2))).to(**tkwargs)
            x1 = []
            for i in range(len(X)):
                x1.append(feature_cache.push(X[i]))
            x2 = []
            for j in range(len(X2)):
                x2.append(feature_cache.push(X2[j]))
                
            x1 = torch.vstack(x1).to(**tkwargs)
            x2 = torch.vstack(x2).to(**tkwargs)
            x1 = torch.reshape(x1, (x1.shape[0], 1, -1)).to(**tkwargs)
            x2 = torch.reshape(x2, (1, x2.shape[0], -1)).to(**tkwargs)
            
            x1 = x1.repeat(1, x2.shape[1], 1).to(**tkwargs)
            x2 = x2.repeat(x1.shape[0], 1, 1).to(**tkwargs)
            
            mat = torch.sum((x1 - x2)**2, dim=-1).to(**tkwargs)
            mat = torch.exp(- self.lengthscale * mat)
            return mat
        
class CombinedOrderKernel(Kernel):
    def __init__(self, n, **kwargs):
        super(CombinedOrderKernel, self).__init__(**kwargs)
        self.n = n  
        self.kernel1 = OrderKernel()
        self.kernel2 = OrderKernel()

    def forward(self, X, X2=None, diag=False, last_dim_is_batch=False, **params):
        if X2 is None:
            X2 = X
        
        if len(X.shape) > 2:
            X = X.squeeze() 
        if len(X2.shape) > 2:
            X2 = X2.squeeze()
        print(X.shape, X2.shape)
            
        # print("X.shape", X.shape, "X2.shape", X2.shape)
        
        if last_dim_is_batch:
            raise RuntimeError("CombinedOrderKernel does not accept the last_dim_is_batch argument.")
        
        X1_perm1, X1_perm2 = X[:, :self.n], X[:, self.n:]
        X2_perm1, X2_perm2 = X2[:, :self.n], X2[:, self.n:]
        
        # print("X1_perm1.shape", X1_perm1.shape, "X1_perm2.shape", X1_perm2.shape)
        # print("X2_perm1.shape", X2_perm1.shape, "X2_perm2.shape", X2_perm2.shape)

        K1 = self.kernel1.forward(X1_perm1, X2_perm1, diag=diag, **params)
        K2 = self.kernel2.forward(X1_perm2, X2_perm2, diag=diag, **params)

        return K1 + K2