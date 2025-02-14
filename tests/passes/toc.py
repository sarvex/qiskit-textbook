# Tests notebooks/toc.yaml is valid

import yaml
from pathlib import Path

NOTEBOOKS_PATH = Path('./notebooks')
TOC_PATH = NOTEBOOKS_PATH / Path('toc.yaml')

def check_exists(path):
    path = NOTEBOOKS_PATH / path.strip('/')
    if not path.exists():
        raise AssertionError(
                f"No file: {path}\n\n"
                f"{TOC_PATH} refers to a file ({path}) that does not exist. "
                 "Please add the missing file, or remove the reference.")

def check_resource(resource):
    for key in resource.keys():
        if key not in ['title', 'description', 'link', 'author']:
            raise AssertionError(
                    f"'{key}' not in resource:\n{resource}.\n\n"
                    "Please edit this resouce in {TOC_PATH} to include a value "
                    f"for '{key}'.")

def check_page(page):
    check_exists(page['url'] + '.ipynb')
    check_exists(page['previewImgUrl'])

def check_course(course):
    assert course['type'] in ['chapter', 'course', 'summer-school']
    overview = course['overviewInfo']
    _, _ = overview['description']['short'], overview['description']['long']
    check_exists(overview['thumbnailUrl'])
    for key in overview.keys():
        assert key in ['description',
                       'thumbnailUrl',
                       'prerequisites',
                       'externalRecommendedReadings',
                       'externalRecommendedReadingsPreamble']
    for page in course['sections']:
        check_page(page)
    if 'externalRecommendedReadings' in overview:
        for resource in overview['externalRecommendedReadings']:
            check_resource(resource)
    if 'prerequisites' in overview:
        for resource in overview['prerequisites']:
            check_resource(resource)

if __name__ == '__main__':
    with open(TOC_PATH) as f:
        toc = yaml.safe_load(f)

    for course in toc:
        check_course(course)

    referenced_notebooks = []
    for course in toc:
        referenced_notebooks.extend(
            Path(f"notebooks/{section['url']}.ipynb")
            for section in course['sections']
        )
    for notebook in Path('notebooks').rglob('*.ipynb'):
        if notebook not in referenced_notebooks:
            if notebook.stem.startswith('_'):
                continue
            if notebook.stem.endswith('-checkpoint'):
                continue
            raise AssertionError(
                f"Found notebook '{notebook}' with no reference in '{TOC_PATH}'.\n"
                f"To fix, either add the notebook to '{TOC_PATH}', or prefix the filename with an underscore "
                f"(i.e. '{notebook.stem + notebook.suffix}' -> '_{notebook.stem + notebook.suffix}')."
            )
        
