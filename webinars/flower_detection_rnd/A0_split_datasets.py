from clearml import Task, Dataset
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from PIL import Image
from tqdm import tqdm


@dataclass
class DataSplitConf:
    # already exists - "someone already uploaded via cli"
    input_dataset_id: str = "86895530658c47a4918bda4f0d92c3e8"
    image_size_values: set = (192, 224, 311, 512)
    use_lineage: bool = False
    dataset_name: str = "flower_detection"
    folder_name_prefix: str = "jpeg-"
    delete_earlier_versions: bool = True
    cloud_queue: str = "colab"


def extract_relevant_filenames(dataset_path, im_size, folder_name_pattern=None):
    # original dataset glob patterns
    import os
    import glob
    folder_name_pattern = f"jpeg-{im_size}x{im_size}" if\
        folder_name_pattern is None else folder_name_pattern
    train_image_paths = glob.glob(
        os.path.join(dataset_path, folder_name_pattern, "train", "**", "*.jpeg"),
        recursive=True,
    )
    valid_image_paths = glob.glob(
        os.path.join(dataset_path, folder_name_pattern, "val", "**", "*.jpeg"),
        recursive=True,
    )
    return train_image_paths, valid_image_paths


def gen_norm_info(over_file_folder):
    max_value = 255.0
    pixel_mean = np.array([0, 0, 0], dtype=np.float32)
    pixel_var = np.array([0, 0, 0], dtype=np.float32)
    files = [f for f in Path(over_file_folder).glob('**/*.jp*g')]
    n_files = len(files)
    for image_fname in tqdm(files, desc='calculating...'):
        image = Image.open(image_fname)
        image = np.array(image)/max_value
        pixel_mean += image.mean(axis=(0, 1))
        pixel_var += image.var(axis=(0, 1))

    return dict(
        mean=(pixel_mean/n_files).tolist(),
        std=np.sqrt(pixel_var/n_files).tolist(),
        max_pixel_value=max_value,
    )


if __name__ == '__main__':
    project_name = 'R|D?R&D! Webinar 01'
    # force colab to get dataclasses
    Task.add_requirements('dataclasses','0.4')
    # override numpy version for colab
    Task.add_requirements('numpy', '1.19.5')
    task = Task.init(
        project_name=project_name,
        task_name='Orig dataset split to sizes',
        task_type=Task.TaskTypes.data_processing,
        output_uri = True,  # auto save everything to ClearML Free
    )

    cfg = DataSplitConf()
    task.connect(cfg, 'dataset split config')

    if cfg.cloud_queue is not None and len(cfg.cloud_queue):
        task.execute_remotely(cfg.cloud_queue)

    input_dataset = Dataset.get(dataset_id=cfg.input_dataset_id)
    input_dataset_folder = input_dataset.get_local_copy()

    # going to do some pruning relative to this folder
    all_subfolders = [d for d in Path(input_dataset_folder).iterdir() if d.is_dir()]
    all_subfolders_rel = [d.relative_to(input_dataset_folder) for d in all_subfolders]

    # prepare an artifact for upload
    results = {image_size: {'train': '', 'val': '', 'norm_info': {}}
               for image_size in cfg.image_size_values}

    for image_size in cfg.image_size_values:
        dataset_name = f"{cfg.dataset_name}_{image_size}x{image_size}_"

        train_files, validation_files = \
            extract_relevant_filenames(input_dataset_folder, image_size)

        # test that there are files train/val
        if not len(train_files):
            raise ValueError(
                f'No files found for image size {image_size} on folder {input_dataset_folder}'
            )
        if not len(validation_files):
            raise NotImplementedError('No validation files - option for train only not supported')

        # relative folder
        rel_folder = cfg.folder_name_prefix + f"{image_size}x{image_size}"
        rel_folder = Path(rel_folder)
        # actual files
        path_to_images =\
            Path(input_dataset_folder) / rel_folder

        for stage in ['train', 'val']:  # TODO 'test'

            try:
                test_if_exists = Dataset.list_datasets(
                    dataset_project=project_name,
                    partial_name=dataset_name+stage,
                    only_completed=False,
                )

                if len(test_if_exists):
                    print(f'found datasets in the project with image size {image_size}')
                    if cfg.delete_earlier_versions:
                        for t in test_if_exists:
                            try:
                                Dataset.delete(t['id'])
                                print(f'Deleted {t}')
                            except ValueError:
                                print(f'Could not delete dataset - has children?')

            except ValueError:
                pass

            print(f'Now with {dataset_name}, creating!')
            if cfg.use_lineage:
                new_dataset = Dataset.create(
                    dataset_name=dataset_name+stage,
                    dataset_project=project_name,
                    parent_datasets=[cfg.input_dataset_id]
                )
                print('...Done')

                # remove other sizes
                for other_folder_rel in all_subfolders_rel:
                    if other_folder_rel != rel_folder:
                        new_dataset.remove_files(str(other_folder_rel)+"/*", verbose=False)
                # remove other stages
                for not_stage in ['train', 'val', 'test']:
                    if not_stage != stage:
                        new_dataset.remove_files(str(rel_folder/not_stage)+"/*", verbose=False)

                # upload should be no-op in this case
                rmed = new_dataset.list_removed_files(cfg.input_dataset_id)
                print(f"pruned {len(rmed)} files from parent dataset")

            else:
                print('Not using lineage, dataset will be created from scratch')
                new_dataset = Dataset.create(
                    dataset_name=dataset_name+stage,
                    dataset_project=project_name,
                )
                print('...Done')
                new_dataset.add_files(
                    str(path_to_images/stage),
                    wildcard='*.jp*g',
                    local_base_folder=input_dataset_folder,
                    dataset_path=str(rel_folder/stage),
                    verbose=False,
                )

            new_dataset.upload(show_progress=True)
            new_dataset.finalize()
            new_dataset.publish()

            results[image_size][stage] = new_dataset.id

            if stage == 'train':
                file_folder = path_to_images / stage
                print(f"Calculating pixel centering info for train dataset... ")
                results[image_size]['norm_info'] = gen_norm_info(file_folder)

    task.upload_artifact('dataset_metadata', results)
    task.close()
