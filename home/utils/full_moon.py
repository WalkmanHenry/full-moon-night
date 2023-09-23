import numpy as np
from imagehash import phash
from PIL import Image
import cv2, os


class full_moon:
    """
        This class is used to OCR, interpret and extract the text from the image of the full moon.
        And find the stars in the image.
        etc.
    """

    # The path of images files
    images_path = ''

    images_handlers = {}

    def __init__(self, images_path='static/attachments/'):
        self.images_path = images_path
        pass

    def is_similar(self, hash1, hash2):
        """
            Check if the difference between two hashes is less than 10

            :param hash1: The hash value to be compared
            :param hash2: Another hash value to be compared
            :return: `True` if hash1 - hash2 <= 10, Otherwise return `False`
        """
        return hash1 - hash2 <= 10

    def get_cards(self, image):
        """
        在图片中找到卡牌。
        """
        if isinstance(image, str):
            image_instance = self.images_handlers.setdefault(image, cv2.imread(image))
        else:
            image_instance = image

        img_gray = cv2.cvtColor(image_instance, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(img_gray, threshold1=30, threshold2=100)
        contours, hierarcy = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filter out small contours based on the area
        min_contour_area = 36000
        # 初始化一个空的列表来存储左上角和右下角坐标的格式
        bounding_boxes = []

        # Filter out small contours based on the area and create bounding_boxes
        bounding_boxes = [[x, y, x + w, y + h] for contour in contours if (cv2.contourArea(contour) > min_contour_area)
                          for x, y, w, h in [cv2.boundingRect(contour)]]

        bounding_boxes.sort(key=lambda box: (box[0], box[1]))
        return bounding_boxes

    def save_image(self, image, coord, filename):
        if isinstance(image, str):
            image_instance = self.images_handlers.setdefault(image, cv2.imread(image))
        else:
            image_instance = image

        # if file exists, delete it
        if os.path.exists(filename):
            os.remove(filename)

        image_instance = cv2.imread(image)
        cv2.imwrite(filename, image_instance[coord[1]:coord[3], coord[0]:coord[2]])
        return filename

    def check_point_in_card(self, card, point):
        """
            Check if the point is in the rectangle of the card

            :param point: [x, y]
            :param card: [[x1, y1], [x2, y2]]
            :return: `True` if x1 < x < x2, y1 < y < y2, Otherwise return `False`
        """
        x, y = point
        x1, y1, x2, y2 = card
        return x1 <= x <= x2 and y1 <= y <= y2

    def load_templates(self, template_folder):
        """
            Load the template images from the template folder
            :param template_folder: the folder that contains the template images
            :return: {template_name: template_image}
        """
        templates = {}
        for fname in os.listdir(template_folder):
            if fname.endswith(('.png', '.jpg', '.jpeg')):
                img = cv2.imread(os.path.join(template_folder, fname), 0)
                templates[fname] = img
        return templates

    def get_ocr_result(self, image):
        """
             使用 easyocr 识别图片中的文字
             :param image_path: 图片路径
         """
        # this module is realy slow, so we need import it only when we need it
        import easyocr
        reader = easyocr.Reader(['ch_sim'], gpu=True)

        # Determine image type
        if isinstance(image, str):
            image_instance = self.images_handlers.setdefault(image, cv2.imread(image))
        else:
            image_instance = image

        return reader.readtext(image_instance)


    def get_attack_and_health(self, image):
        """
            获取攻击力和生命值
            :param image: 图片
        """
        if isinstance(image, str):
            img = self.images_handlers.setdefault(image, cv2.imread(image))
        else:
            img = image

        attack_path = os.path.join(self.images_path, 'stuffs', 'attack')
        health_path = os.path.join(self.images_path, 'stuffs', 'health')
        attack_templates = self.load_templates(attack_path)
        health_templates = self.load_templates(health_path)

        # We need more accuracy so don't use grayscale images
        attack_matches = self.find_template_matches(img, attack_templates, 0.91)
        health_matches = self.find_template_matches(img, health_templates, 0.91)

        # Combine the dictionaries using dictionary comprehension
        combined_matches = {**attack_matches, **health_matches}

        return combined_matches


    def load_templates(self, template_folder):
        """
        Load all template images from a folder and store them in a dictionary.

        :param template_folder: Path to the folder containing template images.
        :return: A dictionary containing template images, where keys are file names and values are the corresponding images.
        """
        templates = {}
        for fname in os.listdir(template_folder):
            if fname.endswith(('.png', '.jpg', '.jpeg')):
                img = cv2.imread(os.path.join(template_folder, fname))
                templates[fname] = img
        return templates


    def find_template_matches(self, image, templates, similarity=0.95):
        """
        Find all matches for a given image and templates.

        :param image: Input image to search for matches.
        :param templates: A dictionary containing template images where keys are template file names and values are the corresponding images.
        :param similarity: Threshold for matching similarity, ranging from 0 to 1, with a default of 0.95.
        :return: A dictionary containing information about all matches, where keys represent the top-left coordinates of matching regions, and values are dictionaries with matching details.
        """
        matches = {}
        for template_name, template in templates.items():
            template_value = template_name.split('.')[0]
            res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            # Find the best matches
            loc = np.where(res > similarity)
            data = ''
            # Get matching coordinates
            for pt in zip(*loc[::-1]):
                # Get the matching region
                top_left = f"{pt[0]}_{pt[1]}"
                # Ignore if there is another vertex within 5 pixels of this region
                unique = True
                for pt2 in matches.values():
                    if (abs(pt2['coord'][0] - pt[0]) < 5) and (abs(pt2['coord'][1] - pt[1]) < 5):
                        unique = False
                        break
                if unique:
                    data = {'value': template_value, 'coord': pt, 'similarity': res[pt[1]][pt[0]]}
                    matches[top_left] = data
        return matches


    def extract_card_corners(self, input_dir, output_dir_attack, output_dir_health):
        """
        Extracts the bottom-left (attack) and bottom-right (health) corners of cards and saves them in separate folders.

        :param input_dir: Directory containing input card images.
        :param output_dir_attack: Directory to save extracted attack corner images.
        :param output_dir_health: Directory to save extracted health corner images.
        :return: None
        """
        # Ensure the output directories exist
        os.makedirs(output_dir_attack, exist_ok=True)
        os.makedirs(output_dir_health, exist_ok=True)

        hash_dict_attack = {}
        hash_dict_health = {}

        for fname in os.listdir(input_dir):
            if fname.endswith(('.png', '.jpg', '.jpeg')):
                # Load the image
                img_path = os.path.join(input_dir, fname)
                img = cv2.imread(img_path)
                if img is None:
                    print(f"Image load failed: {img_path}")
                    continue

                # Find contours
                img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(img_gray, threshold1=30, threshold2=100)
                contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Filter out small contours based on area
                min_contour_area = 36000
                large_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]

                for i, contour in enumerate(large_contours):
                    # Get the contour's bounding box
                    x, y, w, h = cv2.boundingRect(contour)

                    # Extract the bottom-left and bottom-right images
                    bottom_left = img[y + h - 50:y + h - 15, x + 20:x + 60]
                    bottom_right = img[y + h - 50:y + h - 15, x + w - 60:x + w - 20]

                    # Convert to PIL images
                    bottom_left_pil = Image.fromarray(bottom_left)
                    bottom_right_pil = Image.fromarray(bottom_right)

                    # Calculate hashes
                    hash_left = phash(bottom_left_pil)
                    hash_right = phash(bottom_right_pil)

                    # Check if hashes already exist, and save the images if not
                    if not any(self.is_similar(hash_left, existing_hash) for existing_hash in hash_dict_attack.keys()):
                        cv2.imwrite(os.path.join(output_dir_attack, f'{fname[:-4]}_card_{i + 1}.jpg'), bottom_left)
                        hash_dict_attack[hash_left] = f'{fname[:-4]}_card_{i + 1}_attack.jpg'

                    if not any(self.is_similar(hash_right, existing_hash) for existing_hash in hash_dict_health.keys()):
                        cv2.imwrite(os.path.join(output_dir_health, f'{fname[:-4]}_card_{i + 1}.jpg'), bottom_right)
                        hash_dict_health[hash_right] = f'{fname[:-4]}_card_{i + 1}_health.jpg'

    def get_stars(self, image):
        """
        Get stars in the image.

        :param image: Path of the image or a cv2 instance.
        :return: List of result sets containing star coordinates.
        """
        matches = []
        if isinstance(image, str):
            image_instance = self.images_handlers.setdefault(image, cv2.imread(image))
        else:
            image_instance = image

        image_gray = cv2.cvtColor(image_instance, cv2.COLOR_BGR2GRAY)
        template = cv2.imread(os.path.join(self.images_path, 'stuffs', 'star.jpg'), cv2.IMREAD_GRAYSCALE)

        res = cv2.matchTemplate(image_gray, template, cv2.TM_CCOEFF_NORMED)

        # Find the best matches
        loc = np.where(res >= 0.95)
        w, h = template.shape[::-1]

        # Loop through to mark all found matching areas
        for pt in zip(*loc[::-1]):
            # Get the matching area
            top_left = pt
            bottom_right = (pt[0] + w, pt[1] + h)

            # Remove duplicate matches
            unique = True
            for tl, br in matches:
                if abs(tl[0] - top_left[0]) < 3 and abs(tl[1] - top_left[1]) < 3:
                    unique = False
            if unique:
                matches.append((top_left, bottom_right))

        return matches

    def assign_values_to_cards(self, matches, card_list):
        """
        Assigns values to cards based on matches.

        Args:
            matches (list): A list of matches, where each match is a dictionary with 'coord', 'size', and 'value' keys.
            card_list (list): A list of card coordinates, where each card is represented as a tuple (x, y, width, height).

        Returns:
            list: A list of dictionaries representing card values, with 'attack' and 'health' keys.
        """
        card_values = [{} for _ in card_list]
        for key, match in matches.items():
            x, y = match['coord']
            value = match['value']

            for i, card in enumerate(card_list):
                if self.check_point_in_card(card, (x, y)):
                    if x < (card[0] + card[2]) / 2:
                        card_values[i]['attack'] = value
                    else:
                        card_values[i]['health'] = value
                    break
        return card_values
