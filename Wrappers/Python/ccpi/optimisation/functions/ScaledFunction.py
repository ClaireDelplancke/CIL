# -*- coding: utf-8 -*-
#   This work is part of the Core Imaging Library developed by
#   Visual Analytics and Imaging System Group of the Science Technology
#   Facilities Council, STFC

#   Copyright 2018-2019 Evangelos Papoutsellis and Edoardo Pasca

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#       http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
from numbers import Number
import numpy

class ScaledFunction(object):
    '''ScaledFunction

    A class to represent the scalar multiplication of an Function with a scalar.
    It holds a function and a scalar. Basically it returns the multiplication
    of the product of the function __call__, convex_conjugate and gradient with the scalar.
    For the rest it behaves like the function it holds.

    Args:
       function (Function): a Function or BlockOperator
       scalar (Number): a scalar multiplier
    Example:
       The scaled operator behaves like the following:
       
    '''
    def __init__(self, function, scalar):
        super(ScaledFunction, self).__init__()
        self.L = None
        if not isinstance (scalar, Number):
            raise TypeError('expected scalar: got {}'.format(type(scalar)))
        self.scalar = scalar
        self.function = function

    def __call__(self,x, out=None):
        '''Evaluates the function at x '''
        return self.scalar * self.function(x)

    def convex_conjugate(self, x):
        '''returns the convex_conjugate of the scaled function '''
        # if out is None:
        #     return self.scalar * self.function.convex_conjugate(x/self.scalar)
        # else:
        #     out.fill(self.function.convex_conjugate(x/self.scalar))
        #     out *= self.scalar
        return self.scalar * self.function.convex_conjugate(x/self.scalar)

    def proximal_conjugate(self, x, tau, out = None):
        '''This returns the proximal operator for the function at x, tau
        '''
        if out is None:
            return self.scalar * self.function.proximal_conjugate(x/self.scalar, tau/self.scalar)
        else:
            out.fill(self.scalar * self.function.proximal_conjugate(x/self.scalar, tau/self.scalar))
            

    def grad(self, x):
        '''Alias of gradient(x,None)'''
        warnings.warn('''This method will disappear in following 
        versions of the CIL. Use gradient instead''', DeprecationWarning)
        return self.gradient(x, out=None)

    def prox(self, x, tau):
        '''Alias of proximal(x, tau, None)'''
        warnings.warn('''This method will disappear in following 
        versions of the CIL. Use proximal instead''', DeprecationWarning)
        return self.proximal(x, out=None)

    def gradient(self, x, out=None):
        '''Returns the gradient of the function at x, if the function is differentiable'''
        if out is None:            
            return self.scalar * self.function.gradient(x)    
        else:
            out.fill( self.scalar * self.function.gradient(x) )

    def proximal(self, x, tau, out=None):
        '''This returns the proximal operator for the function at x, tau
        '''
        if out is None:
            return self.function.proximal(x, tau*self.scalar)     
        else:
            out.fill( self.function.proximal(x, tau*self.scalar) )
            
if __name__ == '__main__':        

    from ccpi.optimisation.functions import L2NormSquared, MixedL21Norm
    from ccpi.framework import ImageGeometry, BlockGeometry
    
    M, N, K = 2,3,5
    ig = ImageGeometry(voxel_num_x=M, voxel_num_y = N, voxel_num_z = K)
    
    u = ig.allocate('random_int')
    b = ig.allocate('random_int') 
    
    BG = BlockGeometry(ig, ig)
    U = BG.allocate('random_int')
        
    f2 = 0.5 * L2NormSquared(b=b)
    f1 = 30 * MixedL21Norm()
    tau = 0.355
    
    res_no_out1 =  f1.proximal_conjugate(U, tau)
    res_no_out2 =  f2.proximal_conjugate(u, tau)    
    
    
#    print( " ######## with out ######## ")
    res_out1 = BG.allocate()
    res_out2 = ig.allocate()
    
    f1.proximal_conjugate(U, tau, out = res_out1)
    f2.proximal_conjugate(u, tau, out = res_out2)


    numpy.testing.assert_array_almost_equal(res_no_out1[0].as_array(), \
                                            res_out1[0].as_array(), decimal=4) 
    
    numpy.testing.assert_array_almost_equal(res_no_out2.as_array(), \
                                            res_out2.as_array(), decimal=4)     
      
          
          
    
    
    
    
    
    
    
    
    
    
    
    

    


    
