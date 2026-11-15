"""Validation for the JSON Schema subset used by model classifiers."""
import math


def object_schema(props):
    return dict(type='object', properties=props, required=list(props), additionalProperties=False)


def validate(value, spec):
    kind = spec['type']
    if isinstance(kind, list):
        for option in kind:
            try:
                validate(value, dict(spec, type=option))
                return
            except ValueError: pass
        raise ValueError('结构化输出字段类型错误')
    if kind == 'null':
        if value is not None: raise ValueError('结构化输出字段类型错误: null')
        return
    valid = {'object':isinstance(value,dict), 'array':isinstance(value,list),
             'string':isinstance(value,str), 'boolean':type(value) is bool,
             'number':type(value) in (int,float) and math.isfinite(value) if type(value) in (int,float) else False}[kind]
    if not valid: raise ValueError('结构化输出字段类型错误: '+kind)
    if 'enum' in spec and value not in spec['enum']: raise ValueError('结构化输出枚举无效')
    if kind == 'number' and not spec.get('minimum',-math.inf) <= value <= spec.get('maximum',math.inf): raise ValueError('结构化输出数值越界')
    if kind == 'object':
        if set(value) != set(spec['properties']): raise ValueError('结构化输出字段缺失或多余')
        for k,v in value.items(): validate(v,spec['properties'][k])
    if kind == 'array':
        if not spec.get('minItems',0) <= len(value) <= spec.get('maxItems',math.inf): raise ValueError('结构化输出行数错误')
        for v in value: validate(v,spec['items'])
