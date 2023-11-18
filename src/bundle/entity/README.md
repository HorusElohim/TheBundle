# entity
The entity subpackage in BUNDLE introduces the basic backbone class Entity.


## Entity 
The Entity class in the entity subpackage of BUNDLE is a foundational block designed to facilitate the development of more complex classes. It extends the JSONData class from the data subpackage, providing advanced data handling and serialization capabilities.

```python
@data.dataclass
class Entity(data.JSONData):
    name: str = data.field(default_factory=str)
    path: Path = data.field(default_factory=Path)
    born_time: int = data.field(default_factory=time.time_ns, compare=False)
    dead_time: int = data.field(default_factory=int)
    auto_save: bool = data.field(default_factory=bool)
```

Entity serves as a base class for defining objects with rich features like automatic JSON serialization, lifecycle tracking, and dynamic property management. It's ideal for applications that require structured data representation with additional metadata and behavior.

### Features
* [Dataclass & JSONData](../data/README.md)
* Lifecycle Tracking: Automatic tracking of the entity's creation and destruction times.
* Automatic JSON Serialization: Option to automatically save the entity to a JSON file upon destruction.
* Dynamic Property Management: Properties like age and code provide insights into the entity's state and context.
* Flexible Path Management: Ability to dynamically update the entity's associated path.



### Class Definition
Define a custom entity by extending the Entity class:

```python
import bundle

@bundle.data.dataclass
class MyEntity(bundle.entity.Entity):
    pass
```

### Instantiation and Lifecycle
Create an instance of the entity and observe its lifecycle:

```python
# Create an instance
my_entity = MyEntity(name="Example", auto_save=True)

# Access lifecycle properties
print(f"Entity age: {my_entity.age}")
print(f"Entity code: {my_entity.code}")
```
The entity will automatically save to JSON upon destruction if auto_save is True

###  Dynamic Path Management
Update the entity's path dynamically:

```python
my_entity.move("new/location")
print(f"Updated path: {my_entity.path}")
```
