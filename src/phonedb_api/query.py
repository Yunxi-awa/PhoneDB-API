import re

import requests
from bs4 import BeautifulSoup, Tag
import copy


class FormHandler:
    """
    一个用于动态解析和处理HTML表单的类。
    它可以加载一个HTML文件，解析其中的特定表单，获取其默认提交值，
    并提供一个方法来根据用户指定的参数覆盖默认值，生成一个准备发送的POST请求负载。
    """

    def __init__(self, html_content: str):
        """
        初始化处理器，加载并解析HTML文件中的第二个表单。

        Args:
            html_content (str): HTML内容字符串。
        """

        self.soup = BeautifulSoup(html_content, 'html.parser')
        forms = self.soup.find_all('form')
        if len(forms) < 2:
            raise ValueError("错误：HTML中未找到第二个<form>标签。")

        self.form = forms[1]
        self.form_action = self.form.get('action')
        self.fields = {}
        self.default_payload = {}

        self._parse_form()
        self._populate_default_payload()

    def _get_clean_label_text(self, element: Tag) -> str:
        """为字段标签提取干净的文本，保留括号但移除末尾的冒号。"""
        if not element:
            return ""
        text = ' '.join(element.get_text(strip=True).split())
        return text.rstrip(':').strip()

    def _get_clean_option_text(self, element: Tag) -> str:
        """为选项提取干净的文本，移除末尾的计数和括号里的额外描述。"""
        if not element:
            return ""
        text = ' '.join(element.get_text(strip=True).split())
        text = re.sub(r'\s*\[\d+\]\s*$', '', text)
        return text.strip()

    def _pre_initialize_group_field(self, desc_element: Tag, label: str):
        """为一个分组的复选框字段预先创建字段定义。"""
        if label and label not in self.fields:
            first_input = desc_element.find_next('input', {'name': re.compile(r'.+\[\]')})
            if first_input:
                self.fields[label] = {
                    'name': first_input.get('name'),
                    'type': 'checkbox',
                    'options': {}
                }

    def _parse_item(self, item: Tag, group_label: str = None):
        """解析一个单独的 form_item div。"""
        item_label_tag = item.find(['strong', 'b'], recursive=False)
        label = self._get_clean_label_text(item_label_tag) if item_label_tag else group_label

        if not label:
            return
        if item_label_tag and label in self.fields:
            if self.fields[label].get('type') != 'checkbox' or self.fields[label].get('options'):
                return

        select = item.find('select')
        if select:
            options = {self._get_clean_option_text(opt): opt.get('value')
                       for opt in select.find_all('option') if opt.get('value')}
            self.fields[label] = {'name': select.get('name'), 'type': 'select', 'options': options}
            return

        inputs = item.find_all('input', type='text')
        if inputs:
            if len(inputs) == 1:
                self.fields[label] = {'name': inputs[0].get('name'), 'type': 'text'}
            else:
                min_input = next((i for i in inputs if i.get('name', '').endswith('_min')), None)
                max_input = next((i for i in inputs if i.get('name', '').endswith('_max')), None)
                if min_input and max_input:
                    self.fields[label] = {
                        'type': 'range',
                        'min_name': min_input.get('name'),
                        'max_name': max_input.get('name'),
                    }
            return

        checkboxes = item.find_all('input', type='checkbox')
        if checkboxes:
            field_name = checkboxes[0].get('name')
            target_field_label = label
            if item_label_tag and label not in self.fields:
                self.fields[label] = {'name': field_name, 'type': 'checkbox', 'options': {}}

            if target_field_label in self.fields and self.fields[target_field_label]['type'] == 'checkbox':
                for cb in checkboxes:
                    label_el = item.find('label', {'for': cb.get('id')})
                    if label_el:
                        option_text = self._get_clean_option_text(label_el)
                        if option_text:
                            self.fields[target_field_label]['options'][option_text] = cb.get('value')

    def _parse_form(self):
        """通过单次遍历HTML结构来解析表单字段定义。"""
        current_group_label = None
        for element in self.form.find_all(['div'], class_=['form_desc', 'form_item']):
            if 'form_desc' in element.get('class', []):
                label_tag = element.find('strong')
                if label_tag:
                    current_group_label = self._get_clean_label_text(label_tag)
                    self._pre_initialize_group_field(element, current_group_label)
            elif 'form_item' in element.get('class', []):
                self._parse_item(element, current_group_label)

    def _populate_default_payload(self):
        """
        填充一个字典，该字典包含表单在未做任何修改时的默认提交值。
        """
        payload = {}

        # 处理 <select> 和 <input type="text">
        for element in self.form.find_all(['select', 'input']):
            name = element.get('name')
            if not name or '[]' in name:  # 暂时跳过复选框
                continue

            if element.name == 'select':
                selected_option = element.find('option', selected=True)
                if selected_option:
                    payload[name] = selected_option.get('value', '')
            elif element.get('type') == 'text':
                payload[name] = element.get('value', '')

        # 处理复选框
        checked_boxes = self.form.find_all('input', type='checkbox', checked=True)
        for cb in checked_boxes:
            name = cb.get('name')
            value = cb.get('value')
            if not name:
                continue

            if '[]' in name:
                if name not in payload:
                    payload[name] = []
                payload[name].append(value)
            else:
                payload[name] = value

        # 添加提交按钮的name
        submit_button = self.form.find('button', type='submit')
        if submit_button and submit_button.get('name'):
            payload[submit_button.get('name')] = submit_button.get('value', '')

        self.default_payload = payload

    def get_default_payload(self) -> dict:
        """
        返回表单的默认提交负载。

        Returns:
            dict: 默认负载的副本。
        """
        return copy.deepcopy(self.default_payload)

    def create_payload(self, params: dict = None) -> tuple[str, dict]:
        """
        根据用户提供的参数覆盖默认值，生成最终的表单负载。
        如果未提供参数，则返回默认负载。

        Args:
            params (dict, optional): 一个字典，键是表单的显示标签，值是期望设定的值。
                                     如果为None，则返回默认负载。默认为 None。

        Returns:
            tuple: 包含表单的action URL和准备好的负载字典。

        Raises:
            ValueError: 如果任何参数不合法。
        """
        if params is None:
            params = {}

        payload = self.get_default_payload()
        errors = []

        fields_lookup = {}
        for label, data in self.fields.items():
            case_insensitive_label = label.lower()
            fields_lookup[case_insensitive_label] = data.copy()
            if 'options' in data:
                fields_lookup[case_insensitive_label]['options_inverted'] = {
                    key.lower(): val for key, val in data['options'].items() if key
                }

        for label, value in params.items():
            field_data = fields_lookup.get(label.lower())

            if not field_data and label.lower().endswith('(s)'):
                singular_label = label.lower().removesuffix('(s)')
                field_data = fields_lookup.get(singular_label)

            if not field_data:
                clean_label = re.sub(r'\s*\([^)]*\)', '', label).strip().lower()
                if clean_label in fields_lookup:
                    field_data = fields_lookup[clean_label]
                else:
                    errors.append(f"不合法的参数键: '{label}'。在表单中未找到此标签。")
                    continue

            field_type = field_data['type']
            name = field_data.get('name')

            if field_type == 'select':
                actual_value = field_data['options_inverted'].get(str(value).lower())
                if actual_value is None and value:
                    errors.append(f"不合法的选项 '{value}' 对于参数 '{label}'。")
                else:
                    payload[name] = actual_value

            elif field_type == 'text':
                payload[name] = value

            elif field_type == 'range':
                if not isinstance(value, dict) or not ('min' in value or 'max' in value):
                    errors.append(f"不合法的范围参数值 '{label}': 必须是包含 'min' 和/或 'max' 键的字典。")
                    continue
                if 'min' in value:
                    payload[field_data['min_name']] = value['min']
                if 'max' in value:
                    payload[field_data['max_name']] = value['max']

            elif field_type == 'checkbox':
                values_to_process = value if isinstance(value, list) else [value]
                actual_values = []
                for item in values_to_process:
                    actual_value = field_data['options_inverted'].get(str(item).lower())
                    if actual_value is None and item:  # 允许空字符串或None被忽略
                        errors.append(f"不合法的选项 '{item}' 对于参数 '{label}'。")
                    elif actual_value is not None:
                        actual_values.append(actual_value)

                # 覆盖时，先清空默认值
                if name in payload:
                    del payload[name]
                if actual_values:
                    payload[name] = actual_values

        if errors:
            raise ValueError("创建表单负载失败，存在以下错误:\n" + "\n".join(errors))

        return self.form_action, payload