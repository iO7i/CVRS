"""Select scalar observations without relabeling diagnostics as benchmark AP."""
def scalar_observations(result):
    output={}
    def visit(value,prefix):
        if isinstance(value,dict):
            if 'value' in value and ('reason' in value or len(value)<=2):
                v=value['value']
                if isinstance(v,(int,float)) and not isinstance(v,bool):output[prefix]=float(v)
            else:
                for k,v in value.items():visit(v,prefix+'/'+k if prefix else k)
        elif isinstance(value,list):
            for i,v in enumerate(value):visit(v,prefix+'/'+str(i))
        elif isinstance(value,(int,float)) and not isinstance(value,bool):output[prefix]=float(value)
    if result.get('metrics'):visit(result['metrics'],'metrics')
    elif result.get('aggregate'):visit(result['aggregate'],'aggregate')
    return output
