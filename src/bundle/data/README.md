# data 

The data subpackage in BUNDLE introduces advanced data handling capabilities, focusing on the Dataclass and JSONData classes. These classes enhance Python's standard data handling methods, providing efficient and effective ways to manage complex data structures.

*data.py*
---
The data.py module define the class `Dataclass``.

## Dataclass
Dataclass extends the standard Python dataclass to facilitate easy conversions between dataclass instances and dictionaries, addressing the need for streamlined data handling in Python.

### Features

* Python class -> dict 
* dict -> Python class


### Definition 

It's preferred to initialize always the class attribute by `bundle.data.field` with a *default constructor* as for the dataclasses. 

```python
import bundle

# Define a custom data class
class MyData(bundle.data.Dataclass):
    name: str = bundle.data.field(default_constructor=str)
    value: int = bundle.data.field(default_constructor=int)
```

__Hint__: if need to assign default arguments in the CTor then use a lambda

```python
str_example: str = bundle.data.field(default_constructor=lambda: str("Nice"))
```

### Instantiation

The instantiation happen as a normal dataclass.

### Dataclass()
Using the constructor.


```python
my_data = MyData(name="Example", value=42)
```

### from_dict: dict -> Python class
Using the class method from_dict. Convert the dict into the class. 

```python
new_data = MyData.from_dict(data_dict)
```

### as_dict: Python class -> dict 
Covert class to dict.

```python
data_dict = my_data.as_dict()
```


*json.py*
---
The json.py module define the class `JSONData``.


## JSONData 
The JSONData class in the data subpackage of BUNDLE extends the capabilities of the Dataclass by enabling serialization to and from JSON. This class is ideal for applications requiring robust data interchange, configuration management, or data persistence. JSONData provides a seamless way to handle JSON serialization and deserialization, including validation with jsonschema. It is designed to make working with JSON data in Python more intuitive, efficient, and reliable.

### Features
* JSON Serialization: Convert Python objects into JSON format, supporting both simple and complex data structures.
* JSON Deserialization: Reconstruct Python objects from JSON, preserving the data's structure and types.
* JSON Schema Validation: Validate JSON data against predefined schemas to ensure data integrity and format consistency.
* Custom Serialization: Handle non-JSON serializable objects using pickle, extending the range of data types that can be serialized.

### Definition 
As Dataclass.

```python
import bundle

@bundle.data.dataclass
class MyJsonData(bundle.data.JSONData):
    name: str = "Default Name"
    value: int = 0
```

### Instantiation
As Dataclass.

```python
my_json_data = MyJsonData(name="Example", value=42)
```

### Serialization
Convert a JSONData instance to a JSON string or file:

```python
# Serialize to JSON string
json_str = my_json_data.as_json()
print(json_str)

# Serialize to JSON file
json_file_path = "data.json"
my_json_data.dump_json(json_file_path)
```

__Hint__: During the serialization any Python object will be serialized with pickle.

### Deserialization
Load a JSONData instance from a JSON string or file:

```python
# Load from JSON file
loaded_data = MyJsonData.from_json(json_file_path)
print(loaded_data)
```


### JSON Schema Validation
Generate and validate against a JSON schema:

```python
# Generate JSON schema
json_schema_path = "schema.json"
MyJsonData.to_jsonschema(json_schema_path)
# Validate the instance against the schema
is_valid = my_json_data.is_valid_by_jsonschema(json_schema_path)
print(f"Validation result: {is_valid}")
```

