def load_properties(properties_file_path='config.properties'):
    properties = {}
    try:
        with open(properties_file_path, 'r', encoding='utf-8') as propfile:
            for line in propfile:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    properties[key.strip()] = value.strip()
        return properties
    except FileNotFoundError:
        print(f"Error: File {properties_file_path} not found!")
        return {}
    except Exception as e:
        print(f"Error reading file {properties_file_path}: {e}")
        return {}