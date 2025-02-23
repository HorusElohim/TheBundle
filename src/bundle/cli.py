import rich_click as click

from bundle.core import logger, tracer

log = logger.get_logger(__name__)

click.rich_click.SHOW_ARGUMENTS = True

banner = """                                    
                                                                                                                               dddddddd                            
TTTTTTTTTTTTTTTTTTTTTTThhhhhhh                               BBBBBBBBBBBBBBBBB                                                 d::::::dlllllll                     
T:::::::::::::::::::::Th:::::h                               B::::::::::::::::B                                                d::::::dl:::::l                     
T:::::::::::::::::::::Th:::::h                               B::::::BBBBBB:::::B                                               d::::::dl:::::l                     
T:::::TT:::::::TT:::::Th:::::h                               BB:::::B     B:::::B                                              d:::::d l:::::l                     
TTTTTT  T:::::T  TTTTTT h::::h hhhhh           eeeeeeeeeeee    B::::B     B:::::Buuuuuu    uuuuuunnnn  nnnnnnnn        ddddddddd:::::d  l::::l     eeeeeeeeeeee    
        T:::::T         h::::hh:::::hhh      ee::::::::::::ee  B::::B     B:::::Bu::::u    u::::un:::nn::::::::nn    dd::::::::::::::d  l::::l   ee::::::::::::ee  
        T:::::T         h::::::::::::::hh   e::::::eeeee:::::eeB::::BBBBBB:::::B u::::u    u::::un::::::::::::::nn  d::::::::::::::::d  l::::l  e::::::eeeee:::::ee
        T:::::T         h:::::::hhh::::::h e::::::e     e:::::eB:::::::::::::BB  u::::u    u::::unn:::::::::::::::nd:::::::ddddd:::::d  l::::l e::::::e     e:::::e
        T:::::T         h::::::h   h::::::he:::::::eeeee::::::eB::::BBBBBB:::::B u::::u    u::::u  n:::::nnnn:::::nd::::::d    d:::::d  l::::l e:::::::eeeee::::::e
        T:::::T         h:::::h     h:::::he:::::::::::::::::e B::::B     B:::::Bu::::u    u::::u  n::::n    n::::nd:::::d     d:::::d  l::::l e:::::::::::::::::e 
        T:::::T         h:::::h     h:::::he::::::eeeeeeeeeee  B::::B     B:::::Bu::::u    u::::u  n::::n    n::::nd:::::d     d:::::d  l::::l e::::::eeeeeeeeeee  
        T:::::T         h:::::h     h:::::he:::::::e           B::::B     B:::::Bu:::::uuuu:::::u  n::::n    n::::nd:::::d     d:::::d  l::::l e:::::::e           
      TT:::::::TT       h:::::h     h:::::he::::::::e        BB:::::BBBBBB::::::Bu:::::::::::::::uun::::n    n::::nd::::::ddddd::::::ddl::::::le::::::::e          
      T:::::::::T       h:::::h     h:::::h e::::::::eeeeeeeeB:::::::::::::::::B  u:::::::::::::::un::::n    n::::n d:::::::::::::::::dl::::::l e::::::::eeeeeeee  
      T:::::::::T       h:::::h     h:::::h  ee:::::::::::::eB::::::::::::::::B    uu::::::::uu:::un::::n    n::::n  d:::::::::ddd::::dl::::::l  ee:::::::::::::e  
      TTTTTTTTTTT       hhhhhhh     hhhhhhh    eeeeeeeeeeeeeeBBBBBBBBBBBBBBBBB       uuuuuuuu  uuuunnnnnn    nnnnnn   ddddddddd   dddddllllllll    eeeeeeeeeeeeee                                                                                                                                                                     
"""


@click.group(name="bundle")
@tracer.syn.decorator_call_raise
async def main():
    click.echo(click.style(banner, fg="green"))


def add_cli_submodule(submodule_name: str) -> None:
    """Dynamically imports a subcommand and adds it to the CLI group.

    Assumes each submodule has a `cli` module and within that module an attribute
    with the same name as the submodule, e.g. `bundle.scraper.cli` has `scraper`.

    Args:
        submodule_name (str): The name of the submodule to import.
    """
    try:
        # Import the cli module from the submodule
        module = __import__(f"bundle.{submodule_name}.cli", fromlist=[submodule_name])
        command = getattr(module, submodule_name, None)
        if command:
            main.add_command(command)
        else:
            log.warning(f"Command '{submodule_name}' not found in module {module}.")
    except ImportError as e:
        log.warning(f"Module 'bundle.{submodule_name}.cli' could not be imported -> {e}")


add_cli_submodule("testing")
add_cli_submodule("scraper")
add_cli_submodule("website")
add_cli_submodule("youtube")
