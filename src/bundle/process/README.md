# process
The process subpackage within BUNDLE offers sophisticated process handling capabilities, ideal for managing and interacting with system processes in both synchronous and asynchronous contexts. It includes classes for executing and managing standard and streaming processes, extending these functionalities for asynchronous operations as well.

* *_abc.py*: Defines the abstract base class ProcessABC for process-related classes.
* *synchronous.py*: Contains the synchronous Process and StreamingProcess classes.
* *asynchronous.py*: Houses the asynchronous counterparts AsyncProcess and StreamingAsyncProcess.


## ProcessABC
The abstract base class for all process classes. It sets the groundwork for defining common process-related functionalities.

## Process
A class that encapsulates the functionality of a standard system process. It executes a given command synchronously and captures its output.

```python
from bundle.process import Process

# Initialize and execute a process
simple_process = Process(command="echo 'Hello, Process!'")
if simple_process():
    print("success")
else:
    print("error")

# Access output and return code
print(simple_process.stdout)
print("Return code:", return_code)
```

## AsyncProcess
An asynchronous version of the Process class, executing commands asynchronously.

```python
import asyncio
from bundle.process import AsyncProcess

async def main():
    async_process = AsyncProcess(command="echo 'Hello, AsyncProcess!'")
    await async_process.exec()

    print(async_process.stdout)

# Run the asynchronous process
asyncio.run(main())
```

## StreamingProcess
A specialized class for handling processes that continuously generate output (streaming output). Useful for processes that need real-time output monitoring.

```python
from bundle.process import StreamingProcess

# Define a callback for stdout
def on_stdout(line):
    print("STDOUT:", line)

def on_stderr(line):
    print("STDERR:", line)

streaming_process = StreamingProcess(command="ping 127.0.0.1")
streaming_process.stdout_callback = on_stdout
streaming_process.stderr_callback = on_stderr
streaming_process()
```

## StreamingAsyncProcess
Combines the functionality of StreamingProcess with asynchronous execution. It's designed for handling streaming processes asynchronously.

```python
import asyncio
from bundle.process import StreamingAsyncProcess

async def main():
    # Define a callback for stdout
    async def on_stdout(line):
        print("ASYNC STDOUT:", line)
    
    async def on_stderr(line):
        print("ASYNC STDERR:", line)

    streaming_async_process = StreamingAsyncProcess(command="ping 127.0.0.1", stdout_callback=on_stdout)
    streaming_async_process.stdout_callback = on_stdout
    streaming_async_process.stderr_callback = on_stderr
    await streaming_async_process()

asyncio.run(main())
```

## Usage Considerations
The Process and StreamingProcess classes are intended for synchronous operations. They block the execution until the process is complete.
AsyncProcess and StreamingAsyncProcess provide non-blocking alternatives, running processes in the background.
The stdout_callback in StreamingProcess and StreamingAsyncProcess allows for real-time processing of output.