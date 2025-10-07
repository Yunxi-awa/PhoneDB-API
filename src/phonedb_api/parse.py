import copy
import re

from bs4 import PageElement, Tag, NavigableString, BeautifulSoup
from loguru import logger

from .instance import InstCat, InstMeta, Instance


class QueryFormParser:
    """
        一个用于动态解析和处理HTML表单的类。
        它可以加载一个HTML文件，解析其中的特定表单，获取其默认提交值，
        并提供一个方法来根据用户指定的参数覆盖默认值，生成一个准备发送的POST请求负载。
        """

    def __init__(self, html: str):
        """
        初始化处理器，加载并解析HTML文件中的第二个表单。

        Args:
            html (str): HTML内容字符串。
        """

        self.soup = BeautifulSoup(html, 'lxml')
        forms = self.soup.find_all('form')
        if len(forms) < 2:
            raise ValueError("错误：HTML中未找到第二个<form>标签。")

        self.form = forms[1]
        self.form_action = self.form.get('action')
        self.fields = {}
        self.default_payload = {}

        self._parse_form()
        self._populate_default_payload()

    def _get_clean_label_text(self, element: PageElement | Tag | NavigableString) -> str:
        """为字段标签提取干净的文本，保留括号但移除末尾的冒号。"""
        if not element:
            return ""
        text = ' '.join(element.get_text(strip=True).split())
        return text.rstrip(':').strip()

    def _get_clean_option_text(self, element: PageElement | Tag | NavigableString) -> str:
        """为选项提取干净的文本，移除末尾的计数和括号里的额外描述。"""
        if not element:
            return ""
        text = ' '.join(element.get_text(strip=True).split())
        text = re.sub(r'\s*\[\d+]\s*$', '', text)
        return text.strip()

    def _pre_initialize_group_field(self, desc_element: Tag, label: str):
        """为一个分组的复选框字段预先创建字段定义。"""
        if label and label not in self.fields:
            first_input = desc_element.find_next('input', {'name': re.compile(r'.+\[]')})
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
                    label_el = item.find('label', {'for': str(cb.get('id'))})
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

    async def parse(self, params: dict = None) -> dict:
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

        return payload


class InstanceParser:
    """
    Parses an HTML table into a structured dictionary, handling specific edge cases
    and data corrections through a patching mechanism.
    """

    def __init__(self, meta: InstMeta, html: str):
        """
        Initializes the parser with item metadata and HTML content.

        """
        self.meta = meta
        self.soup = BeautifulSoup(html, 'lxml') if "Error 404: not found" not in html else None
        self.results: dict = {}

        # State variables for tracking context during parsing
        self.current_section_key: str | None = None
        self.last_field_key: str | None = None

    async def parse(self) -> Instance:
        """
        Public method to execute the full parsing workflow.

        Returns:
            A dictionary containing the parsed data.
        """
        self.results = {
            "Meta": {
                "Image": None,
            }
        }

        if not self.soup:
            logger.warning(f"{self.meta} 无内容")
            return Instance(self.meta, self.results)

        self._extract_image_url()
        self._process_table_rows()
        # self._apply_patches()

        return Instance(self.meta, self.results)

    @staticmethod
    def _split_by_commas_outside_parentheses(text: str) -> list[str]:
        """
        Splits a string by commas, but ignores commas inside parentheses.
        """
        parts = []
        start = 0
        depth = 0
        for i, char in enumerate(text):
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                parts.append(text[start:i].strip())
                start = i + 1
        parts.append(text[start:].strip())
        return parts

    def _extract_image_url(self):
        """Extracts the image URL from the HTML head."""
        img_tag = self.soup.select_one("head > meta:nth-child(15)")
        if img_tag and img_tag.get("content"):
            self.results["Meta"]["Image"] = img_tag.get("content")

    def _process_table_rows(self):
        """Iterates over all <tr> tags in the main table and processes them."""
        table = self.soup.select_one("table")
        if not table:
            raise ValueError(f"{self.meta} <table> 未找到")

        for tr in table.select('tr'):
            self._process_row(tr)

    def _process_row(self, tr: Tag):
        """
        Processes a single <tr> tag and dispatches to the correct handler
        based on the number of <td> children.
        """
        tds = tr.find_all('td', recursive=False)
        num_tds = len(tds)

        if num_tds == 1:
            self._handle_single_td_row(tds[0])
        elif num_tds == 2:
            self._handle_double_td_row(tds)
        else:
            # This logic can be expanded if rows with 0 or >2 tds are possible
            pass

    def _handle_single_td_row(self, td: Tag):
        """Handles logic for a <tr> with exactly one <td>."""
        header_tag = td.find(['h4', 'h5'])
        strong_tag = td.find('strong')

        if header_tag:
            # Case 1.1: This is a new section header (e.g., <h4>General</h4>)
            section_name = header_tag.get_text(strip=True).replace(':', '')
            self.current_section_key = section_name
            self.results[self.current_section_key] = {}
            self.last_field_key = None  # Reset last field on new section
        elif strong_tag and list(td.children):
            # Case 1.2: A field-value pair within one <td>
            field = strong_tag.get_text(strip=True)
            # The value is assumed to be the last text node in the <td>
            value_text = list(td.children)[-1].get_text(strip=True)
            values = self._split_by_commas_outside_parentheses(value_text)

            if self.current_section_key:
                self.results[self.current_section_key][field] = values
                self.last_field_key = field

    def _handle_double_td_row(self, tds: list[Tag]):
        """Handles logic for a <tr> with exactly two <td>s."""
        field_text = tds[0].get_text(strip=True)
        value_text = tds[1].get_text(strip=True)

        if not self.current_section_key:
            raise ValueError(f"{self.meta} 解析错误, 行 {value_text} 没有章节.")

        match self.meta.inst_id:
            case 2239 | 2243:
                power_supply_section = self.results.get("Power Supply", {})
                if not power_supply_section:  # If the section is empty
                    logger.warning(f"{self.meta} 解析错误, Power Supply 章节为空; 添加默认值 Battery.")
                    self.results["Power Supply"] = {"Battery": []}
                    self.last_field_key = "Battery"

            case 4796 | 6095:
                sw_env_section = self.results.get("Software Environment", {})
                if not sw_env_section:
                    logger.warning(
                        f"{self.meta} 解析错误, Software Environment 章节为空; 添加默认值 Platform: Android, Operating System: Google Android 4.2.2 (Jelly Bean).")
                    self.results["Software Environment"] = {
                        "Platform": ["Android"],
                        "Operating System": ["Google Android 4.2.2 (Jelly Bean)"]
                    }
                    self.last_field_key = "Operating System"
            case 8074:
                sw_env_section = self.results.get("Software Environment", {})
                if not sw_env_section:
                    logger.warning(
                        f"{self.meta} 解析错误, Software Environment 章节为空; 添加默认值 Operating System.")
                    self.results["Software Environment"] = {
                        "Operating System": []
                    }
                    self.last_field_key = "Operating System"
        if field_text:
            # Case 2.1: A standard Field-Value pair
            field = field_text
            values = self._split_by_commas_outside_parentheses(value_text)
            self.results[self.current_section_key][field] = values
            self.last_field_key = field
        else:
            # Case 2.2: A continuation of the previous field's value
            if self.last_field_key:
                self.results[self.current_section_key][self.last_field_key].append(value_text)
            else:
                raise ValueError(f"{self.meta} 解析错误, 行 {value_text} 没有字段.")
