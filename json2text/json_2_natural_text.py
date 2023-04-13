import importlib.util
import inspect
import re


class InvalidTemplateException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


PH_PATTERN = re.compile(r"{[A-Za-z]+}")


def apply_operation(operation, operand):
    return operation(operand)


def replace_place_holders(template, field_dict):
    matches = PH_PATTERN.findall(template)
    for match in matches:
        field_name = match[1:-1]
        if field_name not in field_dict:
            raise InvalidTemplateException(
                'template contains invalid reference to undeclared field - {}'.format(field_name))
        else:
            template = template.replace(match, field_dict[field_name])
    return template


def get_template_type(element):
    template_type = None
    if 'templateType' in element:
        template_type = element['templateType']
    return template_type


def transform_string_field(element, document, text, field_dict, func_dict):
    template_type = get_template_type(element)
    field_name = element['fieldName']
    field_value = document[field_name]

    if template_type == 'plainTemplate':
        field_dict[field_name] = field_value
        text += element['template']
    elif (template_type == 'plainFieldValue') and (field_value is not None):
        field_dict[field_name] = field_value
        text += field_value
    elif (template_type == 'joinFieldValue') and (field_value is not None and field_value != ''):
        field_dict[field_name] = field_value
        text += replace_place_holders(element['template'], field_dict)
    elif template_type == 'joinFunctionValue':
        func_name = element['function']
        field_dict[field_name] = apply_operation(func_dict[func_name], document[field_name])
        text += replace_place_holders(element['template'], field_dict)
    elif template_type is not None and (field_value is not None and field_value != ''):
        raise InvalidTemplateException('invalid template type - {} for field - {}'.format(template_type, field_name))
    return text, field_dict


def transform_object_field(element, document, text, field_dict, func_dict):
    template_type = get_template_type(element)
    field_name = element['fieldName']
    field_value = document[field_name]

    if template_type == 'plainTemplate':
        text += element['template']
    elif template_type is not None:
        raise InvalidTemplateException('invalid template type - {} for field - {}'.format(template_type, field_name))
    return build_context_from_json(element['properties'], field_value, text, field_dict, func_dict)


def transform_string_list_field(element, document, text, field_dict, func_dict):
    template_type = get_template_type(element)
    field_name = element['fieldName']

    if template_type == 'joinFunctionValue':
        func_name = element['function']
        operation = func_dict[func_name]
        field_dict[field_name] = apply_operation(operation, document[field_name])
        text += replace_place_holders(element['template'], field_dict)
    elif template_type is not None:
        raise InvalidTemplateException('invalid template type - {} for field - {}'.format(template_type, field_name))
    return text, field_dict


def transform_object_list_field(element, document, text, field_dict, func_dict):
    template_type = get_template_type(element)
    field_name = element['fieldName']
    field_value = document[field_name]

    if template_type == 'plainTemplate':
        text += element['template']
    elif template_type is not None:
        raise InvalidTemplateException('invalid template type - {} for field - {}'.format(template_type, field_name))

    valid_element_types = ['single', 'multiple']
    if ('elementType' not in element) or (element['elementType'] is None) or (
            element['elementType'] not in valid_element_types):
        raise InvalidTemplateException(
            'elementType is either not defined or is invalid for field - {}. Acceptable values are [{}]'.format(
                field_name, ", ".join(valid_element_types)))

    element_type = element['elementType']
    if element_type == 'single':
        text, field_dict = build_context_from_json(element['properties'], field_value[0], text, field_dict, func_dict)
    elif element_type == 'multiple':
        if ('elementIdentifiers' not in element) or (element['elementIdentifiers'] is None):
            raise InvalidTemplateException('elementIdentifiers are not defined for field - {}'.format(field_name))
        element_identifiers = element['elementIdentifiers']

        for identifier in element_identifiers:
            for item in element['properties']:
                if identifier in item['elementIdentifier']:
                    for data_object in document[field_name]:
                        if identifier in data_object:
                            text, field_dict = build_context_from_json(item['properties'], data_object, text,
                                                                       field_dict, func_dict)
                        else:
                            pass
                else:
                    raise InvalidTemplateException(
                        'property for elementIdentifier - {} is not defined in field - {}'.format(identifier,
                                                                                                  field_name))
    return text, field_dict


def build_context_from_json(properties, document, text, field_dict, func_dict):
    for element in properties:
        if ('fieldName' not in element) or (element['fieldName'] is None):
            raise InvalidTemplateException('mandatory field {} is missing.'.format(element['fieldName']))

        if ('fieldType' not in element) or (element['fieldType'] is None):
            raise InvalidTemplateException(
                'mandatory field {} is missing for field - {}'.format(element['fieldType'], element['fieldName']))

        field_name, field_type = element['fieldName'], element['fieldType']

        if (field_name not in document) or (document[field_name] is None):
            pass
        else:
            if ('templateType' in element) and (element['templateType'] is not None):
                template_type = element['templateType']

            if field_type == 'string':
                text, field_dict = transform_string_field(element, document, text, field_dict, func_dict)

            elif field_type == 'object':
                text, field_dict = transform_object_field(element, document, text, field_dict, func_dict)

            elif field_type == 'stringList':
                text, field_dict = transform_string_list_field(element, document, text, field_dict, func_dict)

            elif field_type == 'objectList':
                text, field_dict = transform_object_list_field(element, document, text, field_dict, func_dict)

            else:
                raise InvalidTemplateException('invalid field type - {} for field - {}'.format(field_type, field_name))

    return text, field_dict


def generate_context(document, template, func_module_path):
    if func_module_path is not None:
        spec = importlib.util.spec_from_file_location('functions', func_module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        func_dict = {}
        for name, function in inspect.getmembers(module, inspect.isfunction):
            func_dict[name] = function
    if 'properties' in template:
        properties = template['properties']
    else:
        return {
                   "err": "Template structure must be defined under 'properties'."
                          " Refer sample_template.json for more details.."}, 400
    text = ''
    try:
        text, field_dict = build_context_from_json(properties, document, text, {}, func_dict)
    except InvalidTemplateException as err:
        return {"err": err}, 400
    return {"context": text}, 200
