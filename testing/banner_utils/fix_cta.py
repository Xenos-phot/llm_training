def fix_cta(banner_config):
    cta_idx = []
    for idx, layer in enumerate(banner_config['objects']):
        if 'cta' in layer['id'].lower():
            cta_idx.append(idx)
    if len(cta_idx) !=2:
        return banner_config
    else:
        layer_1 = banner_config['objects'][cta_idx[0]]
        layer_2 = banner_config['objects'][cta_idx[1]]
        if layer_1['type'] == 'text' or layer_1['type'] == 'textbox':
            layer_text = layer_1
            layer_background = layer_2
        else:
            layer_text = layer_2
            layer_background = layer_1

        layer_text['left'] = layer_background['left'] + layer_background['width'] / 2 - layer_text['width'] / 2
        layer_text['top'] = layer_background['top'] + layer_background['height'] / 2 - layer_text['height'] / 2
        banner_config['objects'][cta_idx[1]] = layer_text
        banner_config['objects'][cta_idx[0]] = layer_background
    return banner_config