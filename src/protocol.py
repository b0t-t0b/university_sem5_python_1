"""Binary framing and XML serialization for Variant 22 RPC."""

import xml.etree.ElementTree as ET
from src.constants import (
    BYTE_ORDER,
    ENCODING,
    REQ_HEADER_SIZE,
    REQ_LEN_OFFSET,
    REQ_LEN_SIZE,
    REQ_OP_OFFSET,
    REQ_OP_SIZE,
    RESP_HEADER_SIZE,
    RESP_LEN_OFFSET,
    RESP_LEN_SIZE,
    RESP_OP_OFFSET,
    RESP_OP_SIZE,
    STATUS_ERROR,
    STATUS_SUCCESS,
    ZERO,
)


def encode_request_header(op_code, body_len):
    """Pack 4-byte request header: 1-byte op_code, 3-byte body length."""
    op_bytes = int(op_code).to_bytes(REQ_OP_SIZE, byteorder=BYTE_ORDER)
    len_bytes = int(body_len).to_bytes(REQ_LEN_SIZE, byteorder=BYTE_ORDER)
    return op_bytes + len_bytes


def decode_request_header(header_bytes):
    """Unpack 4-byte request header returning (op_code, body_len)."""
    if len(header_bytes) != REQ_HEADER_SIZE:
        raise ValueError("Invalid request header length")
    op_code = int.from_bytes(
        header_bytes[REQ_OP_OFFSET:REQ_LEN_OFFSET],
        byteorder=BYTE_ORDER
    )
    body_len = int.from_bytes(
        header_bytes[REQ_LEN_OFFSET:REQ_HEADER_SIZE],
        byteorder=BYTE_ORDER
    )
    return op_code, body_len


def encode_response_header(op_code, body_len):
    """Pack 6-byte response header: 5-byte body length, 1-byte op_code."""
    len_bytes = int(body_len).to_bytes(RESP_LEN_SIZE, byteorder=BYTE_ORDER)
    op_bytes = int(op_code).to_bytes(RESP_OP_SIZE, byteorder=BYTE_ORDER)
    return len_bytes + op_bytes


def decode_response_header(header_bytes):
    """Unpack 6-byte response header returning (op_code, body_len)."""
    if len(header_bytes) != RESP_HEADER_SIZE:
        raise ValueError("Invalid response header length")
    body_len = int.from_bytes(
        header_bytes[RESP_LEN_OFFSET:RESP_OP_OFFSET],
        byteorder=BYTE_ORDER
    )
    op_code = int.from_bytes(
        header_bytes[RESP_OP_OFFSET:RESP_HEADER_SIZE],
        byteorder=BYTE_ORDER
    )
    return op_code, body_len


def serialize_request_xml(params):
    """Convert dictionary of parameters to UTF-8 XML bytes."""
    root = ET.Element("request")
    params_elem = ET.SubElement(root, "params")
    for key, val in params.items():
        child = ET.SubElement(params_elem, "param", name=key)
        if val is None:
            child.set("null", "true")
        else:
            child.text = str(val)
    return ET.tostring(root, encoding=ENCODING)


def deserialize_request_xml(xml_bytes):
    """Parse request XML bytes into parameter dictionary."""
    root = ET.fromstring(xml_bytes)
    params = {}
    params_elem = root.find("params")
    if params_elem is not None:
        for child in params_elem:
            param_name = child.get("name")
            if child.get("null") == "true":
                params[param_name] = None
            else:
                params[param_name] = child.text
    return params


def _append_val(parent, val):
    """Append serialized representation of Python value to XML parent."""
    if val is None:
        node = ET.SubElement(parent, "null")
    elif isinstance(val, bool):
        node = ET.SubElement(parent, "bool")
        node.text = str(val).lower()
    elif isinstance(val, int):
        node = ET.SubElement(parent, "int")
        node.text = str(val)
    elif isinstance(val, (list, tuple)):
        tag_name = "tuple" if isinstance(val, tuple) else "list"
        node = ET.SubElement(parent, tag_name)
        for sub_val in val:
            _append_val(node, sub_val)
    else:
        node = ET.SubElement(parent, "str")
        node.text = str(val)


def _parse_val(elem):
    """Parse typed XML element back to Python value."""
    if elem.tag == "null":
        return None
    if elem.tag == "bool":
        return elem.text == "true"
    if elem.tag == "int":
        return int(elem.text)
    if elem.tag == "str":
        return "" if elem.text is None else elem.text
    if elem.tag == "tuple":
        return tuple(_parse_val(child) for child in elem)
    if elem.tag == "list":
        return [_parse_val(child) for child in elem]
    return elem.text


def serialize_response_xml(status, result=None, error=None):
    """Convert status and payload to UTF-8 XML response bytes."""
    root = ET.Element("response")
    st_elem = ET.SubElement(root, "status")
    st_elem.text = status
    if status == STATUS_SUCCESS:
        res_elem = ET.SubElement(root, "result")
        _append_val(res_elem, result)
    else:
        err_elem = ET.SubElement(root, "error")
        err_elem.text = "" if error is None else str(error)
    return ET.tostring(root, encoding=ENCODING)


def deserialize_response_xml(xml_bytes):
    """Parse response XML returning (status, payload)."""
    root = ET.fromstring(xml_bytes)
    status_node = root.find("status")
    status = status_node.text if status_node is not None else STATUS_ERROR
    if status == STATUS_SUCCESS:
        res_node = root.find("result")
        if res_node is None or len(res_node) == ZERO:
            return status, None
        return status, _parse_val(res_node[ZERO])
    err_node = root.find("error")
    err_msg = err_node.text if err_node is not None else "Unknown error"
    return status, err_msg
