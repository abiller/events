from dataclasses import dataclass
import json

from clearml import Task
from argparse import ArgumentParser

# need to define this to do validation on str to bool
def boolean_string(s):
    if s not in {'False', 'True'}:
        raise ValueError('Not a valid boolean string')
    return s == 'True'


# parser from zylo117/Yet-Another-EfficientDet-Pytorch
parser = ArgumentParser('Yet Another EfficientDet Pytorch: SOTA object detection network - Zylo117')
parser.add_argument('--debug', type=boolean_string, default=False,
                    help='whether visualize the predicted boxes of training, '
                         'the output images will be in test/')
parser.add_argument('--data_path', type=str, default='datasets/', help='the root folder of dataset')
parser.add_argument('--log_path', type=str, default='logs/')
parser.add_argument('--saved_path', type=str, default='logs/')

parser.add_argument('--batch_size', type=int, default=12, help='The number of images per batch among all devices')
parser.add_argument('--head_only', type=boolean_string, default=False,
                    help='whether finetunes only the regressor and the classifier, '
                         'useful in early stage convergence or small/easy dataset')
parser.add_argument('--lr', type=float, default=1e-4)
parser.add_argument('--optim', type=str, default='adamw', help='select optimizer for training, '
                                                               'suggest using \'admaw\' until the'
                                                               ' very final stage then switch to \'sgd\'')
parser.add_argument('--num_epochs', type=int, default=500)
parser.add_argument('--val_interval', type=int, default=1, help='Number of epoches between valing phases')
parser.add_argument('--save_interval', type=int, default=500, help='Number of steps between saving')

parser.add_argument('--es_min_delta', type=float, default=0.0,
                    help='Early stopping\'s parameter: minimum change loss to qualify as an improvement')
parser.add_argument('--es_patience', type=int, default=0,
                    help='Early stopping\'s parameter: number of epochs with no improvement after which training will be stopped. Set to 0 to disable this technique.')

parser.add_argument('-w', '--load_weights', type=str, default=None,
                    help='whether to load weights from a checkpoint, set None to initialize, set \'last\' to load last checkpoint')
parser.add_argument('-p', '--project', type=str, default='coco', help='project file that contains parameters')
parser.add_argument('-c', '--compound_coef', type=int, default=0, help='coefficients of efficientdet')
parser.add_argument('-n', '--num_workers', type=int, default=12, help='num_workers of dataloader')

@dataclass
class MyFeatureConfig():
    """Config for my new feature"""
    # the word size
    word_size: int = 128


if __name__ == "__main__":
    # this will create "ARGS" in the UI
    task = Task.init(project_name='CLEAR00',
                     task_name='how to config',)

    args = parser.parse_args()

    my_config = task.connect_configuration('hyperparameters.json',
        name='json',
        description='devops stuff')

    my_feature_config = task.connect(MyFeatureConfig, '//feature:words')


    # need to load the json
    cfg = json.load(open(my_config,'rt'))
    # want a dataclass
    my_feature_config = MyFeatureConfig(**my_feature_config)

    print(cfg)
    print(my_feature_config.word_size)
    print(args)

    ...
    # actual experiment...
    ...
    #
    task.set_user_properties(
        TUrtle='do not touch',
        device='cloud007'
    )
    task.close()
