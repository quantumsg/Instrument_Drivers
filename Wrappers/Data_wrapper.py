import qcodes.plots.pyqtgraph as qplt
import numpy as np
import datetime as t
import os
import csv

'''
Data wrapper that can create a live plot (based on qcodes.plots.pyqtgraph),
a text file and a csv file containing the data.
By: Zhang Zhongming

INSTRUCTIONS ON USE

To initialize:
data = Data(<directory>, <experiment_name>, <column_block_size>)
Remark: The directory is where all the data will be stored, the folder must be created before
you use this wrapper.

To add a coordinate:
data.add_coordinate(<coordinate name>, <coordinate units>, <coordinate array>)

Remark: coordinate array is a pre-set set of values that the coordinate can take.
Remark: Value is variable that is to be measured

To add a value:
data.add_value(<value name>, <value unit>)

Remark: The coordinate name and value names identifies the coordinate and value.
Important: use DIFFERENT names for every coordinate and value.

To add a 2D plot:
data.add_2D_plot(<plot title>, <coordinate name>, <value name>, newtrace = <bool>, 
                fig_width = <fig_width>, fig_height = <fig_height>, 
                fig_x_pos = <fig_x_pos>, fig_y_pos = <fig_y_pos>)

To add a 3D plot:
data.add_3D_plot(<plot title>, <coordinate1 name>, <coordinate2 name>, <value name>,
                fig_width = <fig_width>, fig_height = <fig_height>, 
                fig_x_pos = <fig_x_pos>, fig_y_pos = <fig_y_pos>)
                
Remark: fig_width and fig_height is in pixels. The width and height of the entire monitor is usually
around 2000 x 1000. fig_x_pos is the position of the top left corner of the window    
                
                
To open the files:
data.open_files()

To add results to the data object:
data.add_result(<results dictionary>)

Important: data.open_files() must be called before you can call data.add_result()

Remark: The results dictionary is a python dictionary that has as it's key,
coordinate/value names and as the corresponding values, coordinate index/experimental reading
respectively. A coordinate index is the position of the value that the coordinate is taking
on the coordinate array. For example, if the coordinate array is [0.1, 7 ,-4, 5],
a coordinate index of 0 means it is taking the value 0.1, 2 means its taking on -4 and so on. 

Important: ALL values and coordinates must be present in the results dictionary.

To add a new trace to all 2D plots:
data.newtraces()

At the end of the measurement:
data.end_measurement()

Remark: end_measurement() closes the text file and saves all plots in the png format.
Important: If this function is not called, the plots will not be saved and
you may lose data on the text file. 

The function generate_array(start, stop, step, reverse = False) is useful for generating
the required arrays.
It returns two things, the array meant for the coordinate, and the corresponding array of
coordinate indexes. 

for example:
>>> array1, array2 = generate_array(0,10,1, reverse = True)
>>> print(array1)
[0. 1. 2. 3. 4. 5. 6. 7. 8. 9.]
>>> print(array2)
[0 1 2 3 4 5 6 7 8 9 8 7 6 5 4 3 2 1 0]
>>> array1, array2 = generate_array(0,2,0.2, reverse = False)
>>> print(array1)
[0.  0.2 0.4 0.6 0.8 1.  1.2 1.4 1.6 1.8 2. ]
>>> print(array2)
[ 0  1  2  3  4  5  6  7  8  9 10]
'''

# --------- USEFUL FUNCTIONS ------------
def generate_array(start, stop, step, reverse = False):
    array = np.arange(min(start,stop),max(start,stop) + 1e-10, step)
    count_array = np.arange(0, len(array))
    if reverse:
        count_array = np.hstack((count_array[:-1], np.flip(count_array)))
        return array, count_array
    else:
        return array, count_array

def produce_datetime(time_module):
    string = str(time_module.datetime.now())
    date_ = string[:10]
    time_ = string[11:19]
    time_ = time_[:2] + '-' + time_[3:5] + '-' + time_[-2:]
    return date_, time_

def make_block(string, size):
    string = string
    while len(string) <= size:
        string += ' '
    return string

class Coordinate:
    def __init__(self, name, unit, array):
        self.name = name
        self.unit = unit
        self.array = array

class Value:
    def __init__(self, name, unit):
        self.name = name
        self.unit = unit

class TwoDPlot:
    def __init__(self, window_title, coordinate, value, fig_width = None, fig_height= None, fig_x_pos= None,
                 fig_y_pos=None, new_trace=True):
        self.title = window_title
        self.plot = qplt.QtPlot(window_title=window_title, figsize=(fig_width, fig_height),
                               fig_x_position=fig_x_pos, fig_y_position=fig_y_pos)
        self.coordinate = coordinate
        self.value = value
        self.new_trace = new_trace
        self.trace_count = 0
        self.coord_values = []
        self.val_values = []
        self.newtrace()

    def add_value(self, coord_number, value):
        call = self.trace_count - 1
        self.coord_values[call].append(self.coordinate.array[coord_number])
        self.val_values[call].append(value)
        self.plot.update_plot()

    def newtrace(self):
        self.coord_values.append([])
        self.val_values.append([])
        call = self.trace_count
        self.plot.add(x = self.coord_values[call],
                      y = self.val_values[call],
                      xlabel = self.coordinate.name,
                      xunit= self.coordinate.unit,
                      ylabel = self.value.name,
                      yunit = self.value.unit)
        self.trace_count += 1

class ThreeDPlot:
    def __init__(self, window_title, x_coordinate, y_coordinate, value, fig_width = None, fig_height = None
                 ,fig_x_pos = None, fig_y_pos = None):
        self.title = window_title
        self.plot = qplt.QtPlot(window_title=window_title, figsize = (fig_width, fig_height),
                                fig_x_position = fig_x_pos, fig_y_position = fig_y_pos)
        self.x_coordinate = x_coordinate
        self.y_coordinate = y_coordinate
        self.value = value
        self.x_values = self.x_coordinate.array
        self.y_values = self.y_coordinate.array
        self.z_values = np.zeros((len(self.x_values),
                                  len(self.y_values)))
        self.plot.add(x = self.x_values, y = self.y_values, z = self.z_values,
                      xlabel = self.x_coordinate.name,
                      ylabel = self.y_coordinate.name,
                      zlabel = self.value.name,
                      xunit = self.x_coordinate.unit,
                      yunit = self.y_coordinate.unit,
                      zunit = self.value.unit)

    def add_value(self, xcoord, ycoord, value):
        self.z_values[xcoord, ycoord] = value
        self.plot.update_plot()

# -------- MAIN DATA OBJECT ------------
class Data:
    '''
    This dictionary contains details of where the windows will pop up and their size.
    If the number of plots added exceeds the number of keys, it will crash.
    Edit here to add more windows.
    '''
    plots_dic = {1: {'fig_width': 600, 'fig_height': 450, 'fig_x_pos': 0, 'fig_y_pos': 0},
                 2: {'fig_width': 600, 'fig_height': 450, 'fig_x_pos': 0.334, 'fig_y_pos': 0},
                 3: {'fig_width': 600, 'fig_height': 450, 'fig_x_pos': 0.667, 'fig_y_pos': 0},
                 4: {'fig_width': 600, 'fig_height': 450, 'fig_x_pos': 0, 'fig_y_pos': 0.5},
                 5: {'fig_width': 600, 'fig_height': 450, 'fig_x_pos': 0.334, 'fig_y_pos': 0.5},
                 6: {'fig_width': 600, 'fig_height': 450, 'fig_x_pos': 0.667, 'fig_y_pos': 0.5}}
    def __init__(self, directory, experiment_name, column_block_size = 40):
        self.coordinate_list = []
        self.value_list = []
        self.plot_number = 0
        self.plots_list = []
# -------- DATA FILES ----------
        self.directory = directory
        self.experiment_name = experiment_name
        date_, _time_ = produce_datetime(t)
        self.date = date_
        self.time = _time_
        self.Column_order = []
# -------- TEXT FILES ----------
        self.text_file = None
        self.column_block_size = column_block_size
# -------- CSV FILES -----------
        self.csv_file = None

# --------- COORDINATE AND VALUE -----------------
    def add_coordinate(self, name, unit, array):
        coord = Coordinate(name, unit, array)
        self.coordinate_list.append(coord)

    def add_value(self, name, unit):
        val = Value(name, unit)
        self.value_list.append(val)

    def find_coordinate(self, name):
        for coord in self.coordinate_list:
            if coord.name == name:
                return coord
        raise Exception('Please add the coordinate first')

    def find_value(self, name):
        for val in self.value_list:
            if val.name == name:
                return val
        raise Exception('Please add the value first')

# ------------- PLOTS -----------------
    def add_2D_plot(self, window_title, coord_name, value_name, newtrace=True):
        self.plot_number += 1
        n = self.plot_number
        width = self.plots_dic[n]['fig_width']
        height = self.plots_dic[n]['fig_height']
        x_pos = self.plots_dic[n]['fig_x_pos']
        y_pos = self.plots_dic[n]['fig_y_pos']
        coord = self.find_coordinate(coord_name)
        val = self.find_value(value_name)
        plot_ = TwoDPlot(window_title, coord, val, fig_width=width, fig_height=height,
                         fig_x_pos = x_pos, fig_y_pos = y_pos, new_trace=newtrace)
        self.plots_list.append(plot_)

    def add_3D_plot(self, window_title, x_coord_name, y_coord_name, value_name):
        self.plot_number += 1
        n = self.plot_number
        width = self.plots_dic[n]['fig_width']
        height = self.plots_dic[n]['fig_height']
        x_pos = self.plots_dic[n]['fig_x_pos']
        y_pos = self.plots_dic[n]['fig_y_pos']
        xcoord = self.find_coordinate(x_coord_name)
        ycoord = self.find_coordinate(y_coord_name)
        val = self.find_value(value_name)
        plot_ = ThreeDPlot(window_title, xcoord, ycoord, val, fig_width=width, fig_height=height,
                         fig_x_pos = x_pos, fig_y_pos = y_pos)
        self.plots_list.append(plot_)

    def add_result_to_plot(self, results_dict):
        for plot in self.plots_list:
            if isinstance(plot, TwoDPlot):
                coord_name = plot.coordinate.name
                coord_val = results_dict[coord_name]
                value_name = plot.value.name
                value_val = results_dict[value_name]
                plot.add_value(coord_val, value_val)
            # ThreeDPlot
            else:
                xcoord_name = plot.x_coordinate.name
                xcoord_val = results_dict[xcoord_name]
                ycoord_name = plot.y_coordinate.name
                ycoord_val = results_dict[ycoord_name]
                value_name = plot.value.name
                value_val = results_dict[value_name]
                plot.add_value(xcoord_val, ycoord_val, value_val)

    def newtraces(self):
        for plot in self.plots_list:
            if isinstance(plot, TwoDPlot):
                if plot.new_trace:
                    plot.newtrace()
        self.text_file.write('\n\n')
        self.csv_file.writerow([])

# -------------- TEXT FILES ----------------
    def create_file_name(self, form, label = None):
        dir_name = self.directory + '/' + self.date
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
        dir_name = dir_name + '/' +self.time
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
        if label:
            filename = dir_name + '/' + self.time + '_' + self.experiment_name + '_' + label + form
        else:
            filename = dir_name + '/' + self.time + '_' + self.experiment_name + form
        return filename


    def init_data_files(self):
        string = self.experiment_name + ' on ' + self.date + ' ' + self.time
        self.text_file.write(string + '\n')
        self.csv_file.writerow([string, ])
        csv_header = [[],[],[]]
        Column_no = 1
        for coord in self.coordinate_list:
            self.text_file.write(f'Column {Column_no}\n\tname: {coord.name}\n\ttype: coordinate\n\tunit: {coord.unit}\n')
            Column_no += 1
            self.Column_order.append(coord.name)
            csv_header[0].append(coord.name)
            csv_header[1].append('coordinate')
            csv_header[2].append(coord.unit)
        for value in self.value_list:
            self.text_file.write(f'Column {Column_no}\n\tname: {value.name}\n\ttype: value\n\tunit: {value.unit}\n')
            Column_no += 1
            self.Column_order.append(value.name)
            csv_header[0].append(value.name)
            csv_header[1].append('value')
            csv_header[2].append(value.unit)
        self.text_file.write('\n\n')
        for row in csv_header:
            self.csv_file.writerow(row)
        self.csv_file.writerow([])

    def add_result_to_data_files(self, results_dict):
        csv_row = []
        for name in self.Column_order:
            if name in (coord.name for coord in self.coordinate_list):
                val = (self.find_coordinate(name)).array[results_dict[name]]
            else:
                val = results_dict[name]
            self.text_file.write(make_block(str(val), self.column_block_size))
            csv_row.append(val)
        self.csv_file.writerow(csv_row)
        self.text_file.write('\n')

# --------- END USER FUNCTIONS -----------
    # results_dict is the dictionary { name of coordinate/value :
    # coordinate number/ result }
    def add_result(self, results_dict):
        self.add_result_to_plot(results_dict)
        self.add_result_to_data_files(results_dict)

    def open_files(self):
        filename_txt = self.create_file_name('.txt')
        filename_csv = self.create_file_name('.csv')
        self.text_file = open(filename_txt, 'w')
        self.csv_file = csv.writer(open(filename_csv, 'w'))
        self.init_data_files()

    def end_measurement(self):
        self.text_file.close()
        for plot in self.plots_list:
            save_name = self.create_file_name('.png', label=plot.title)
            print(save_name)
            plot.plot.save(save_name)
        print('Measurement ended')














