import os
from settings import APP_DIR

TMP_DIR = os.path.join(APP_DIR,'static','tmp')

def show_inline(pltlib):
    imgs = os.listdir(TMP_DIR)
    try:
        img_list = [int(os.path.splitext(fl)[0]) for fl in imgs]
        img_list.sort()
        last_img_id = img_list[-1] + 1
    except IndexError, TypeError:
        last_img_id = 1

    figure_fname = '%s/%s.svg' % (TMP_DIR, last_img_id)
    figure_url = '/static/tmp/%s.svg' % last_img_id 
    pltlib.savefig(figure_fname)
    print "<br/><embed width=500 height=480 src='%s' type='image/svg+xml' />" % figure_url
