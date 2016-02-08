# Copyright (c) 2015, Qiurui He
# Department of Engineering, University of Cambridge

import numpy as np
import flexible_function as ff      # GPSS kernel definitions
import GPy.kern as GPyKern          # GPy kernel definitions
import grammar                      # GPSS kernel expansion


class GPCKernel(object):
    """
    GP classification kernel for AutoGPC.

    Each instance of GPCKernel is a node in the search tree. GPCKernel is a
    wrapper around the Kernel class defined in gpss-research [1]. The Kernel
    instance in GPCKernel is `translated' to a form compatible with GPy [2] and
    is subsequently used for training in GPy.

    For the time being, we support:
    1) 1-D squared exponential kernels
    2) 1-D periodic kernels
    3) sum of kernels
    4) product of kernels

    References:

    [1] The GPy authors. "GPy: A Gaussian process framework in python,"
    2012-2016.
    https://github.com/SheffieldML/GPy

    [2] J. R. Lloyd, D. Duvenaud, R. Grosse, J. B. Tenenbaum, and Z. Ghahramani,
    "Automatic construction and natural-language description of nonparametric
    regression models,"
    in Proceedings of the 28th AAAI Conference on Artificial Intelligence,
    pp. 1242-1250, June 2014.
    https://github.com/jamesrobertlloyd/gpss-research
    """

    def __init__(self, gpssKernel, numDims, depth):
        """
        :param gpssKernel: a GPSS kernel as defined in flexible_function.py
        :param numDims: total number of dimensions in input space
        :param depth: depth of the current node in the search tree (root is 0)
        """
        # TODO: add reference to input data points
        self.kernel = gpssKernel
        self.ndims = numDims
        self.depth = depth
        self.model = None
        self.isSparse = None

    def expand(self):
        """
        Expand this kernel using grammar defined in grammar.py.

        :param kernel: a GPSS kernel as defined in flexible_function.py
        :param ndim: the number of input dimensions
        :returns: list of GPCKernel resulting from the expansion
        """
        g = grammar.MultiDGrammar(self.ndims, base_kernels='SE', rules=None)
        kernels = grammar.expand(self.kernel, g)
        # kernels = [k.simplified() for k in kernels]
        kernels = [k.canonical() for k in kernels]
        kernels = ff.remove_duplicates(kernels)
        kernels = [k for k in kernels if not isinstance(k, ff.NoneKernel)]
        kernels = [GPCKernel(k, self.ndims, self.depth + 1) for k in kernels]
        return kernels

    def getGPyKernel(self):
        """
        Convert this GPCKernel to GPy kernel.

        :returns: an object of type GPy.kern.Kern
        """
        return gpss2gpy(self.kernel)

    def train(self):
        # TODO: unfinished
        self.model = GPy.models.GPClassification(X, Y, kernel=self.getGPyKernel())
        self.isSparse = False
        self.model.optimize()

    def trainSparse(self):
        # TODO: unfinished
        self.model = GPy.models.SparseGPClassification(X, Y, kernel=self.getGPyKernel(), num_inducing=20)
        self.isSparse = True
        self.model.optimize()


def gpss2gpy(kernel):
    """
    Convert a GPSS kernel to a GPy kernel recursively.

    Support only:
    1) 1-D squared exponential kernels
    2) 1-D periodic kernels
    3) sum of kernels
    4) product of kernels

    :param kernel: a GPSS kernel as defined in flexible_function.py
    :returns: an object of type GPy.kern.Kern
    """
    if isinstance(kernel, ff.SqExpKernel):
        ndim = 1
        sf2 = kernel.sf ** 2
        ls = kernel.lengthscale
        dims = np.array([kernel.dimension])
        return GPyKern.RBF(ndim, variance=sf2, lengthscale=ls, active_dims=dims)

    elif isinstance(kernel, ff.PeriodicKernel):
        ndim = 1
        sf2 = kernel.sf ** 2
        wl = kernel.period
        ls = kernel.lengthscale
        dims = np.array([kernel.dimension])
        return GPyKern.StdPeriodic(ndim, variance=sf2, wavelength=wl, lengthscale=ls, active_dims=dims)

    elif isinstance(kernel, ff.SumKernel):
        return GPyKern.Add(map(gpss2gpy, kernel.operands))

    elif isinstance(kernel, ff.ProductKernel):
        return GPyKern.Prod(map(gpss2gpy, kernel.operands))

    else:
        raise NotImplementedError("Cannot translate kernel of type " + type(gpssKernel).__name__)
