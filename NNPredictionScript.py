"""
Predict USDCAD spot rate at time T given other features at time T.
"""
__version__ = '0.2'
__author__ = 'Chris Park'

import pandas as pd                                                         # Version 0.22.0
import numpy as np                                                          # Version 1.14.0
from NN import NN                                                           # Version 0.2
from utils import split_data, save_obj                                      # Version 0.1


# Parameters -----------------------------------------------------------------------------------------------------------
# Data parsing parameters
parse_inputs = True                                                # If loading from Intermediary Inputs, set to False
train_cv_test_split = [70, 20, 10]                                 # Relative size of train/cross-validation/test set
shuffle_sets = True                                                # Shuffle train/cv/test sets

# Model parameters
alpha = 0.001
num_epochs = 4000
mini_batch_size = 64
hidden_layer_nodes = [32, 16, 8, 4, 2]
hidden_activation = 'relu'
output_activation = 'relu'

# Optimizer parameters
adam_beta1 = 0.9
adam_beta2 = 0.999
adam_epsilon = 1e-8
# Regularization parameters
lambda_reg = 0.01
drop_rate = 0.0
seed = 1

# Save Model Parameters
model_parameters = dict()

model_parameters['alpha'] = alpha
model_parameters['num_epochs'] = num_epochs
model_parameters['mini_batch_size'] = mini_batch_size
model_parameters['hidden_layer_nodes'] = hidden_layer_nodes
model_parameters['hidden_activation'] = hidden_activation
model_parameters['output_activation'] = output_activation
model_parameters['adam_beta1'] = adam_beta1
model_parameters['adam_beta2'] = adam_beta2
model_parameters['adam_epsilon'] = adam_epsilon
model_parameters['lambda_reg'] = lambda_reg
model_parameters['drop_rate'] = drop_rate
model_parameters['seed'] = seed

# Read Inputs ----------------------------------------------------------------------------------------------------------
input_root = 'Inputs/NN/'
output_root = 'Outputs/NN/'

raw_data = pd.read_csv(input_root+'FX Data_table.csv', index_col=0)

# Parse Inputs ---------------------------------------------------------------------------------------------------------
if parse_inputs:
    raw_data = raw_data.fillna(method='ffill')                        # Replace missing data with last valid observation

    usdcad_spot = raw_data['USDCAD Curncy']
    raw_data = raw_data.drop('USDCAD Curncy', axis=1)                 # usdcad removed as a feature

    x = raw_data.T.as_matrix().astype('float32')
    y = usdcad_spot.T.as_matrix().astype('float32')
    y = y.reshape((1, len(y)))                                        # reshape y to be a vector
    y_labels = ['usdcad_spot']

    # Split data into train/dev/test set
    x_train, x_cv, x_test, y_train, y_cv, y_test = split_data(x, y, train_cv_test_split, shuffle_sets, seed=seed)

    # Save train, cv and test sets - note dates may be shuffled from split_data()
    writer = pd.ExcelWriter(input_root+'Intermediary Inputs/split_data.xlsx')
    pd.DataFrame(x.T, columns=raw_data.columns).to_excel(writer, 'x')
    pd.DataFrame(y.T, columns=y_labels).to_excel(writer, 'y')
    pd.DataFrame(x_train.T, columns=raw_data.columns).to_excel(writer, 'x_train')
    pd.DataFrame(x_cv.T, columns=raw_data.columns).to_excel(writer, 'x_cv')
    pd.DataFrame(x_test.T, columns=raw_data.columns).to_excel(writer, 'x_test')
    pd.DataFrame(y_train.T, columns=y_labels).to_excel(writer, 'y_train')
    pd.DataFrame(y_cv.T, columns=y_labels).to_excel(writer, 'y_cv')
    pd.DataFrame(y_test.T, columns=y_labels).to_excel(writer, 'y_test')
    writer.close()
else:
    pre_loaded_data = pd.read_excel(input_root+'Intermediary Inputs/split_data.xlsx', sheet_name=None)
    x = pre_loaded_data['x'].T.values
    y = pre_loaded_data['y'].T.values
    x_train = pre_loaded_data['x_train'].T.values
    x_cv = pre_loaded_data['x_cv'].T.values
    x_test = pre_loaded_data['x_test'].T.values
    y_train = pre_loaded_data['y_train'].T.values
    y_cv = pre_loaded_data['y_cv'].T.values
    y_test = pre_loaded_data['y_test'].T.values
    

# Model setup ----------------------------------------------------------------------------------------------------------
num_features = x.shape[0]
num_examples = x.shape[1]
assert (y.shape[1] == x.shape[1])                               # Check that input and outputs have same num_examples

x_train_normalized = np.log(x_train)
x_cv_normalized = np.log(x_cv)
x_test_normalized = np.log(x_test)

# Initialize Neural Network
fx_prediction_model = NN(alpha=alpha, num_epochs=num_epochs, mini_batch_size=mini_batch_size, adam_beta1=adam_beta1,
                         adam_beta2=adam_beta2, adam_epsilon=adam_epsilon, lambda_reg=lambda_reg, drop_rate=drop_rate,
                         seed=seed)

fx_prediction_model.set_layer_dims(x_train_normalized, y_train, hidden_layer_nodes)     # Set Network dimensions

# Set hidden/output layer activation functions
fx_prediction_model.set_activation_functions(hidden_activation=hidden_activation, output_activation=output_activation)

model_parameters['layer_dims'] = fx_prediction_model.layer_dims
model_parameters['activation_functions'] = fx_prediction_model.activation_functions

# Train model ----------------------------------------------------------------------------------------------------------
trained_model, train_set_metrics, train_set_predictions = fx_prediction_model.train_model(x_train_normalized, y_train)

print('Cross-validation set Model Performance ------------------')
cv_set_metrics, cv_set_predictions = fx_prediction_model.evaluate_model(x_cv_normalized, y_cv, trained_model)
print('Test set Model Performance ------------------')
test_set_metrics, test_set_predictions = fx_prediction_model.evaluate_model(x_test_normalized, y_test, trained_model)

print('Total data set Model Performance ------------------')
x_normalized = np.log(x)
full_data_metrics, full_data_predictions = fx_prediction_model.evaluate_model(x_normalized, y, trained_model)

# Daily time series over the entire data set of prediction values ------------------------------------------------------
writer = pd.ExcelWriter(output_root+'predictions_full_data.xlsx')
pd.DataFrame(x.T, index=raw_data.index, columns=raw_data.columns).to_excel(writer, 'inputs')
pd.DataFrame(full_data_predictions, index=raw_data.index, columns=y_labels).to_excel(writer, 'predictions')
pd.DataFrame(y.T, index=raw_data.index, columns=y_labels).to_excel(writer, 'outputs')
writer.close()

# Save parameters ------------------------------------------------------------------------------------------------------
save_obj(trained_model, output_root+'trained_model')
save_obj(model_parameters, output_root+'model_parameters')

# Store predictions for each set ---------------------------------------------------------------------------------------
writer = pd.ExcelWriter(output_root+'predictions_by_set.xlsx')
# Store predictions
pd.DataFrame(train_set_predictions, columns=y_labels).to_excel(writer, 'train_set_predictions')
pd.DataFrame(cv_set_predictions, columns=y_labels).to_excel(writer, 'cv_set_predictions')
pd.DataFrame(test_set_predictions, columns=y_labels).to_excel(writer, 'test_set_predictions')
# Store corresponding true labels
pd.DataFrame(y_train.T, columns=y_labels).to_excel(writer, 'y_train')
pd.DataFrame(y_cv.T, columns=y_labels).to_excel(writer, 'y_cv')
pd.DataFrame(y_test.T, columns=y_labels).to_excel(writer, 'y_test')
writer.close()
