# tasks
The tasks subpackage of BUNDLE introduces two key classes: Task and AsyncTask. These classes are designed to encapsulate and manage the execution of synchronous and asynchronous tasks, respectively.

## Task and AsyncTask 
*Task*: A class for managing and executing synchronous tasks.
*AsyncTask*: An extension of Task for handling asynchronous tasks, using Python's async features.

Both classes provide a structured approach to task execution, tracking, and management in Python applications.

## Task
The Task class is used for defining and executing synchronous tasks. It provides methods to execute tasks and track their execution state.

```python

Copy code
from bundle.tasks import Task

class MyTask(Task):
    def exec(self, *args, **kwds):
        # Task logic here
        print("Executing task...")

# Create and execute the task
task = MyTask()
task()

```

## AsyncTask 
AsyncTask extends Task to support asynchronous execution. It is suitable for tasks that involve IO-bound operations or require non-blocking execution.

```python
import asyncio
from bundle.tasks import AsyncTask

class MyAsyncTask(AsyncTask):
    async def exec(self, *args, **kwds):
        # Async task logic here
        print("Executing async task...")

# Create and execute the async task
async_task = MyAsyncTask()

# Run the async task in an event loop
asyncio.run(async_task())
```


In both cases, the exec method is where the main logic of the task is implemented. For AsyncTask, this method is an asynchronous coroutine that needs to be awaited or run in an event loop.

The tasks subpackage provides a robust foundation for task management in both synchronous and asynchronous environments, making it a versatile tool for a wide range of applications.