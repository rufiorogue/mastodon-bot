
#
# Mastodon image bot
#
# (c) 2018-2020 Oleksandr Dunaievskyi <roovio@mailbox.org>
#

import yaml
import random
import os
import sys
import tempfile
import time
from PIL import Image
from mastodon import Mastodon
import pickledb

MAX_WIDTH = 2048


def die():
    sys.exit(1)

"""
Concatenates tokens with delim or coalesces them if one is None
"""
def join_str(delim, tokens):
    return delim.join([x for x in tokens if x])


def load_yaml_file(file_path):
    try:
        print('reading %s'%file_path)
        f = open(file_path, 'r')
    except:
        print('failed to load %s'%file_path)
        die()
    return yaml.load(f.read())


class ServerComm:
    def __init__(self, secrets, toot_visibility):
        self.toot_visibility = toot_visibility
        self.m = Mastodon(
                client_secret = secrets['client_secret'],
                access_token = secrets['access_token'],
                api_base_url = 'https://' + secrets['mastodon_hostname'],
                )
    def post_text(self, msg):
        self.m.status_post(msg, visibility=self.toot_visibility)
    def post_image(self, text, image_path, sensitive_flag):
        media_dict = self.m.media_post(image_path)
        self.m.status_post(text, media_ids=[media_dict,], sensitive=sensitive_flag, visibility=self.toot_visibility)


class InfoDb:
    def __init__(self, info_db_path):
        self.db = None
        if info_db_path:
            print('using info db:', info_db_path)
            self.db = pickledb.load(info_db_path, False)
    def get_info(self, image_path):
        if self.db:
            d_image_info:dict = self.db.get(image_path)
            if d_image_info is not False:
                print(image_path, 'found in infodb')
                #img_id:int = d_image_info['id']
                img_desc:str = d_image_info['desc']
                l_img_source:list = d_image_info['source']
                src_joined:str = ''
                if l_img_source and len(l_img_source):
                    src_joined = 'Source: ' + join_str('|', l_img_source)
                return join_str('\n', (img_desc, src_joined))
            else:
                print(image_path, 'not in infodb')
        return ''



def is_supported_image_file(image_path):
    exts =['gif', 'png', 'jpg', 'jpeg', 'mp4', 'mov', 'webm']
    for e in exts:
        if e in image_path:
            return True


class ImageEnumeratorBase:
    def __init__(self, image_dir):
        self.visited_db = pickledb.load('visited.pickledb', True)
        # enumerate all images in the tree
        print('enumerating files in image dir...')
        self.image_list = ImageEnumeratorBase.get_file_list(image_dir)
        print('found %d files'%len(self.image_list))
        # reject unknown and visited elements
        self.image_list = [x for x in self.image_list if not self.is_visited(x) and is_supported_image_file(x)]
        print('after rejection %d images left'%len(self.image_list))


    def is_visited(self, image_path) -> bool:
        return self.visited_db.exists(image_path)
    def set_visited(self, image_path):
        self.visited_db.set(image_path, True)

    @staticmethod
    def get_file_list(image_dir):
        file_list = []
        for root, dirs, files in os.walk(image_dir):
            for file in files:
                file_list.append(os.path.join(root, file))
        return file_list


class RandomImageEnumerator(ImageEnumeratorBase):
    def __init__(self, image_dir):
        super().__init__(image_dir)
    def get(self) -> str:
        choice = random.choice(self.image_list)
        print('randomly selected file %s'%choice)
        return choice


class SequentialImageEnumerator(ImageEnumeratorBase):
    def __init__(self, image_dir):
        super().__init__(image_dir)
    def get(self) -> str:
        choice = self.image_list[0] if len(self.image_list) > 0 else None
        print('selected file by order %s'%choice)
        return choice


def get_media_format_tag(image_path):
    if 'mp4' in image_path or 'webm' in image_path:
        return '#video'
    if 'gif' in image_path:
        return '#gif'
    return ''

def resize_if_needed(image_path):
    try:
        im = Image.open(image_path)
    except:
        return None
    width, height = im.size
    if width > MAX_WIDTH:
        difference_percent = MAX_WIDTH / width
        new_height = height * difference_percent
        im = im.resize((int(MAX_WIDTH), int(new_height)))
        temp_file_path = os.path.join(tempfile._get_default_tempdir(), next(tempfile._get_candidate_names())+'.jpg')
        print('saving temporary resized image as %s'%temp_file_path)
        im.save(temp_file_path)
        return temp_file_path
    else:
        return None


def extract_tags_from_path(image_dir:str, image_path:str) -> str:
    path_relative_to_image_dir = os.path.dirname(os.path.relpath(image_path, image_dir)).replace('/', '\n').replace(' ', '\n')
    tags = path_relative_to_image_dir.split('\n')
    tags = ['#' + x for x in tags]
    return join_str(' ', tags)


def main():
    config = load_yaml_file('config.yaml')
    secrets = load_yaml_file(config['secrets'])

    print('contacting server...')
    comm = ServerComm(secrets, config['toot_visibility'])
    infodb = InfoDb(config['infodb'])

    image_dir:str = config['image_dir']

    if config['order'] == 'random':
        image_provider  = RandomImageEnumerator(image_dir)
    elif config['order'] == 'seq':
        image_provider  = SequentialImageEnumerator(image_dir)
    else:
        print('invalid "order" parameter')
        die()

    image_path:str = image_provider.get()

    if image_path != None:
        desc:str = config['default_desc'] if config['default_desc'] else ''
        tags:str = config['default_tags'] if config['default_tags'] else ''

        info:str = infodb.get_info(os.path.relpath(image_path, image_dir))
        extra_tags:str = extract_tags_from_path(image_dir, image_path)

        desc = join_str('\n', [desc, info])
        tags = join_str(' ', [tags, extra_tags])
        if config['add_media_format_tag']:
            tags = join_str(' ', [tags, get_media_format_tag(image_path)])
        
        text = join_str('\n', [desc, tags])

        image_path_resized:str = resize_if_needed(image_path) # this might produce a temp file

        def post_image():
            try:
                comm.post_image(text, image_path_resized if image_path_resized != None else image_path, config['sensitive'])
                #print('post image: text=@'+text+'@  path='+image_path)
                #  raise ValueError('test exception')
                return True
            except Exception as e:
                print('oops! failed to post, reason:', e)
                return False
        retries = 5
        while not post_image() and retries > 0:
            time.sleep(1)
            retries = retries - 1
            print('retrying...')
        if retries == 0:
            print('giving up!')
        else:
            print('posted')
            # Mark as visited so we dont post twice.
            # Do this only if posting is successful.
            image_provider.set_visited(image_path)
        # clean up temp file
        if image_path_resized:
            os.remove(image_path_resized)
    else:
        print('nothing to post: already at the end of the sequence')



if __name__ == '__main__':
    main()
