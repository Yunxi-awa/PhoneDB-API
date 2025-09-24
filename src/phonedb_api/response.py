import urllib.parse
from typing import Any, Dict, List

import aiohttp
import curl_cffi
from bs4 import BeautifulSoup, Tag

from .instance import InstMeta, InstCat
from .query import FormHandler

ItemData = Dict[str, Any]


class PhoneDBResponse(aiohttp.ClientResponse):
    """
    Parses an HTML table into a structured dictionary, handling specific edge cases
    and data corrections through a patching mechanism.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the parser with item metadata and HTML content.

        Args:
            meta: Metadata about the item being parsed.
            html: The HTML content as a string.
        """
        super().__init__(*args, **kwargs)

        self.meta = None
        self.soup = None
        self.results: ItemData = {}

        # State variables for tracking context during parsing
        self.current_section_key: str | None = None
        self.last_field_key: str | None = None

    async def parse_instance(self) -> ItemData:
        """
        Public method to execute the full parsing workflow.

        Returns:
            A dictionary containing the parsed data.
        """
        await self._initialize_results()

        # Handle early exit for specific cases
        if self.meta.inst_cat == InstCat.DEVICE and self.meta.inst_id == 24170:
            self._add_error("No Content 24170")
            return self.results

        try:
            self._extract_image_url()
            self._process_table_rows()
            self._apply_patches()
        except Exception as e:
            # Catching exceptions at a higher level after attempting structured parsing
            raise RuntimeError(f"Failed to parse {self.meta}. Error: {e}") from e

        return self.results

    async def create_query_payload(self, params: Dict[str, str]):
        a = FormHandler(await self.text())
        return a.create_payload(params)[1]

    async def _initialize_results(self):
        """Sets up the initial structure of the results' dictionary."""
        queries = urllib.parse.parse_qs(urllib.parse.urlparse(str(self.url)).query)
        self.meta = InstMeta(InstCat(queries["m"][0]), int(queries["id"][0]))
        self.soup = BeautifulSoup(await self.text(), 'lxml')
        self.results = {
            "Meta": {
                "ID": self.meta.inst_id,
                "Image": None,
                "Error": [],
            }
        }

    def _add_error(self, message: str):
        """Helper to append an error message to the Meta section."""
        self.results["Meta"]["Error"].append(message)

    @staticmethod
    def _split_by_commas_outside_parentheses(text: str) -> List[str]:
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
            self._add_error("HTML table not found.")
            return

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

    def _handle_double_td_row(self, tds: List[Tag]):
        """Handles logic for a <tr> with exactly two <td>s."""
        field_text = tds[0].get_text(strip=True)
        value_text = tds[1].get_text(strip=True)

        if not self.current_section_key:
            self._add_error(f"Found a row with data '{value_text}' but no section is active.")
            return

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
                self._add_error(f"Found a continuation value '{value_text}' with no prior field.")

    def _apply_patches(self):
        """
        Applies specific fixes or default values for known problematic item IDs
        after the main parsing is complete. This isolates special cases from
        the general parsing logic.
        """
        if self.meta.inst_id == 2239:
            power_supply_section = self.results.get("Power Supply", {})
            if not power_supply_section:  # If the section is empty
                self._add_error("“Power Supply” section was parsed as empty; adding default 'Battery'.")
                self.results["Power Supply"] = {"Battery": []}

        elif self.meta.inst_id in [4796, 6095]:
            sw_env_section = self.results.get("Software Environment", {})
            if not sw_env_section:
                self._add_error("“Software Environment” section was parsed as empty; adding defaults.")
                self.results["Software Environment"] = {
                    "Platform": ["Android"],
                    "Operating System": ["Google Android 4.2.2 (Jelly Bean)"]
                }
