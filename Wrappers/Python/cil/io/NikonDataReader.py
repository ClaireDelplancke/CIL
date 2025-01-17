# -*- coding: utf-8 -*-
#   This work is part of the Core Imaging Library (CIL) developed by CCPi 
#   (Collaborative Computational Project in Tomographic Imaging), with 
#   substantial contributions by UKRI-STFC and University of Manchester.

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
from cil.framework import AcquisitionData, AcquisitionGeometry
from cil.io.TIFF import TIFFStackReader
import warnings
import numpy
import os
    
        
class NikonDataReader(object):
    
    def __init__(self, 
                 **kwargs):
        '''Basic reader for xtekct files
        
        Parameters
        ----------

            
        xtek_file: str with full path to .xtexct file
            
        roi: dictionary with roi to load 
                {'angle': (start, end, step), 
                 'horizontal': (start, end, step), 
                 'vertical': (start, end, step)}
                Files are stacked along axis_0. axis_1 and axis_2 correspond
                to row and column dimensions, respectively.
                Files are stacked in alphabetic order. 
                To skip projections or to change number of projections to load, 
                adjust 'angle'. For instance, 'angle': (100, 300)
                will skip first 100 projections and will load 200 projections.
                'angle': -1 is a shortcut to load all elements along axis.
                Start and end can be specified as None which is equivalent 
                to start = 0 and end = load everything to the end, respectively.
                Start and end also can be negative.
            
        normalise: bool, normalises loaded projections by detector 
                white level (I_0). Default value is True
                            
        fliplr: bool, default = False, flip projections in the left-right direction
                (about vertical axis)
                            
        mode: str, 'bin' (default) or 'slice'. In bin mode, 'step' number
                of pixels is binned together, values of resulting binned
                pixels are calculated as average. 
                In 'slice' mode 'step' defines standard numpy slicing.
                Note: in general 
                output array size in bin mode != output array size in slice mode
        
        Output
        ------
        
        Acquisition data with corresponding geomrtry, arranged as ['angle', horizontal'] 
        if a single slice is loaded and ['vertical, 'angle', horizontal'] 
        if more than 1 slices are loaded.
                    
        '''
        
        self.file_name = kwargs.get('file_name', None)
        self.roi = kwargs.get('roi', {'angle': -1, 'horizontal': -1, 'vertical': -1})
        self.normalise = kwargs.get('normalise', True)
        self.mode = kwargs.get('mode', 'bin')
        self.fliplr = kwargs.get('fliplr', False)
        
        if 'normalize' in kwargs.keys():
            self.normalise = kwargs.get('normalize', True)
            warnings.warn("'normalize' has now been deprecated. Please use 'normalise' instead.")

        if self.file_name is not None:
            self.set_up(file_name = self.file_name,
                        roi = self.roi,
                        normalise = self.normalise,
                        mode = self.mode,
                        fliplr = self.fliplr)
            
    def set_up(self, 
               file_name = None, 
               roi = {'angle': -1, 'horizontal': -1, 'vertical': -1},
               normalise = True,
               mode = 'bin',
               fliplr = False,
               **kwargs):
        
        self.file_name = file_name
        self.roi = roi
        self.normalise = normalise
        self.mode = mode
        self.fliplr = fliplr
        
        if 'normalize' in kwargs.keys():
            self.normalise = kwargs.get('normalize', True)
            warnings.warn("'normalize' has now been deprecated. Please use 'normalise' instead.")

        if self.file_name == None:
            raise Exception('Path to xtek file is required.')
        
        # check if xtek file exists
        if not(os.path.isfile(self.file_name)):
            raise Exception('File\n {}\n does not exist.'.format(self.file_name))
        
        if os.path.basename(self.file_name).split('.')[-1].lower() != 'xtekct':
            raise TypeError('This reader can only process xtekct files. Got {}'.format(os.path.basename(self.file_name)))
                
        # check labels     
        for key in self.roi.keys():
            if key not in ['angle', 'horizontal', 'vertical']:
                raise Exception("Wrong label. One of ollowing is expected: angle, horizontal, vertical")
        
        roi = self.roi.copy()
        
        if 'angle' not in roi.keys():
            roi['angle'] = -1
            
        if 'horizontal' not in roi.keys():
            roi['horizontal'] = -1
        
        if 'vertical' not in roi.keys():
            roi['vertical'] = -1
                
        # parse xtek file
        with open(self.file_name, 'r') as f:
            content = f.readlines()    
                
        content = [x.strip() for x in content]
        
        #initialise parameters
        detector_offset_h = 0
        detector_offset_v = 0
        object_offset_x = 0
        object_roll_deg = 0

        for line in content:
            # filename of TIFF files
            if line.startswith("Name"):
                self._experiment_name = line.split('=')[1]
            # number of projections
            elif line.startswith("Projections"):
                num_projections = int(line.split('=')[1])
            # white level - used for normalization
            elif line.startswith("WhiteLevel"):
                self._white_level = float(line.split('=')[1])
            # number of pixels along Y axis
            elif line.startswith("DetectorPixelsY"):
                pixel_num_v_0 = int(line.split('=')[1])
            # number of pixels along X axis
            elif line.startswith("DetectorPixelsX"):
                pixel_num_h_0 = int(line.split('=')[1])
            # pixel size along X axis
            elif line.startswith("DetectorPixelSizeX"):
                pixel_size_h_0 = float(line.split('=')[1])
            # pixel size along Y axis
            elif line.startswith("DetectorPixelSizeY"):
                pixel_size_v_0 = float(line.split('=')[1])
            # source to center of rotation distance
            elif line.startswith("SrcToObject"):
                source_to_origin = float(line.split('=')[1])
            # source to detector distance
            elif line.startswith("SrcToDetector"):
                source_to_det = float(line.split('=')[1])
            # initial angular position of a rotation stage
            elif line.startswith("InitialAngle"):
                initial_angle = float(line.split('=')[1])
            # angular increment (in degrees)
            elif line.startswith("AngularStep"):
                angular_step = float(line.split('=')[1])
            # detector offset x in units                
            elif line.startswith("DetectorOffsetX"):
                detector_offset_h = float(line.split('=')[1])
            # detector offset y in units  
            elif line.startswith("DetectorOffsetY"):
                detector_offset_v = float(line.split('=')[1])
            # object offset x in units  
            elif line.startswith("ObjectOffsetX"):
                object_offset_x = float(line.split('=')[1])
            # object roll in degrees  
            elif line.startswith("ObjectRoll"):
                object_roll_deg = float(line.split('=')[1])
            # directory where data is stored
            elif line.startswith("InputFolderName"):
                input_folder_name = line.split('=')[1]
                if input_folder_name == '':
                    self.tiff_directory_path = os.path.dirname(self.file_name)
                else:
                    self.tiff_directory_path = os.path.join(os.path.dirname(self.file_name), input_folder_name)




        self._roi_par = [[0, num_projections, 1] ,[0, pixel_num_v_0, 1], [0, pixel_num_h_0, 1]]
        
        for key in roi.keys():
            if key == 'angle':
                idx = 0
            elif key == 'vertical':
                idx = 1
            elif key == 'horizontal':
                idx = 2
            if roi[key] != -1:
                for i in range(2):
                    if roi[key][i] != None:
                        if roi[key][i] >= 0:
                            self._roi_par[idx][i] = roi[key][i]
                        else:
                            self._roi_par[idx][i] = self._roi_par[idx][1]+roi[key][i]
                if len(roi[key]) > 2:
                    if roi[key][2] != None:
                        if roi[key][2] > 0:
                            self._roi_par[idx][2] = roi[key][2] 
                        else:
                            raise Exception("Negative step is not allowed")
        
        if self.mode == 'bin':
            # calculate number of pixels and pixel size
            pixel_num_v = (self._roi_par[1][1] - self._roi_par[1][0]) // self._roi_par[1][2]
            pixel_num_h = (self._roi_par[2][1] - self._roi_par[2][0]) // self._roi_par[2][2]
            pixel_size_v = pixel_size_v_0 * self._roi_par[1][2]
            pixel_size_h = pixel_size_h_0 * self._roi_par[2][2]
        else: # slice
            pixel_num_v = numpy.int(numpy.ceil((self._roi_par[1][1] - self._roi_par[1][0]) / self._roi_par[1][2]))
            pixel_num_h = numpy.int(numpy.ceil((self._roi_par[2][1] - self._roi_par[2][0]) / self._roi_par[2][2]))
            pixel_size_v = pixel_size_v_0
            pixel_size_h = pixel_size_h_0
        
        det_start_0 = -(pixel_num_h_0 / 2)
        det_start = det_start_0 + self._roi_par[2][0]
        det_end = det_start + pixel_num_h * self._roi_par[2][2]
        det_pos_h = (det_start + det_end) * 0.5 * pixel_size_h_0 + detector_offset_h
        
        det_start_0 = -(pixel_num_v_0 / 2)
        det_start = det_start_0 + self._roi_par[1][0]
        det_end = det_start + pixel_num_v * self._roi_par[1][2]
        det_pos_v = (det_start + det_end) * 0.5 * pixel_size_v_0 + detector_offset_v         

        #angles from xtek.ct ignore *.ang and _ctdata.txt as not correct
        angles = numpy.asarray( [ angular_step * proj for proj in range(num_projections) ] , dtype=numpy.float32)
        
        if self.mode == 'bin':
            n_elem = (self._roi_par[0][1] - self._roi_par[0][0]) // self._roi_par[0][2]
            shape = (n_elem, self._roi_par[0][2])
            angles = angles[self._roi_par[0][0]:(self._roi_par[0][0] + n_elem * self._roi_par[0][2])].reshape(shape).mean(1)
        else:
            angles = angles[slice(self._roi_par[0][0], self._roi_par[0][1], self._roi_par[0][2])]
        
        #convert NikonGeometry to CIL geometry
        angles = -angles - initial_angle + 180

        object_roll_deg * numpy.pi /180.
        rotate_axis_x = numpy.tan(object_roll_deg * numpy.pi /180.)

        if self.fliplr:
            origin = 'top-left'
        else:
            origin = 'top-right'

        if pixel_num_v == 1 and (self._roi_par[1][0]+self._roi_par[1][1]) // 2 == pixel_num_v_0 // 2:
            self._ag = AcquisitionGeometry.create_Cone2D(source_position=[0, -source_to_origin],
                                                     rotation_axis_position=[-object_offset_x, 0],
                                                     detector_position=[-det_pos_h, source_to_det-source_to_origin])
            self._ag.set_angles(angles, 
                                angle_unit='degree')
            
            self._ag.set_panel(pixel_num_h, pixel_size=pixel_size_h, origin=origin)

            self._ag.set_labels(labels=['angle', 'horizontal'])
        else:
            self._ag = AcquisitionGeometry.create_Cone3D(source_position=[0, -source_to_origin, 0],
                                                         rotation_axis_position=[-object_offset_x, 0, 0],
                                                         rotation_axis_direction=[rotate_axis_x,0,1],
                                                         detector_position=[-det_pos_h, source_to_det-source_to_origin, det_pos_v])
            self._ag.set_angles(angles, 
                                angle_unit='degree')
            
            self._ag.set_panel((pixel_num_h, pixel_num_v),
                               pixel_size=(pixel_size_h, pixel_size_v),
                               origin=origin)
        
            self._ag.set_labels(labels=['angle', 'vertical', 'horizontal'])

    def get_geometry(self):
        
        '''
        Return AcquisitionGeometry object
        '''
        
        return self._ag
    def get_roi(self):
        '''returns the roi'''
        roi = self._roi_par[:]
        if self._ag.dimension == '2D':
            roi.pop(1)

        roidict = {}
        for i,el in enumerate(roi):
            # print (i, el)
            roidict['axis_{}'.format(i)] = tuple(el)
        return roidict

    def read(self):
        
        '''
        Reads projections and return AcquisitionData container
        '''
        
        reader = TIFFStackReader()

        roi = self.get_roi()

        reader.set_up(file_name = self.tiff_directory_path,
                      roi=roi, mode=self.mode)

        ad = reader.read_as_AcquisitionData(self._ag)
              
        if (self.normalise):
            ad.array[ad.array < 1] = 1
            # cast the data read to float32
            ad = ad / numpy.float32(self._white_level)
            
        
        if self.fliplr:
            dim = ad.get_dimension_axis('horizontal')
            ad.array = numpy.flip(ad.array, dim)
        
        return ad

    def load_projections(self):
        '''alias of read for backward compatibility'''
        return self.read()
