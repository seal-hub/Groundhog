from GUI_utils import Node
from json_util import JSONSerializable


class Command(JSONSerializable):
    def __init__(self, action: str = "NOP"):
        self.action = action

    @classmethod
    def create_from_dict(cls, json_command: dict):
        return cls(json_command.get('action', "NOP"))


class LocatableCommand(Command):
    def __init__(self, action: str, node: Node):
        super().__init__(action)
        self.target = node

    @classmethod
    def create_from_dict(cls, json_command: dict):
        action = json_command.get('action', "NOP")
        json_target_node = json_command.get('target', {})
        target_node = Node.createNodeFromDict(json_target_node)
        return cls(action, target_node)


class InfoCommand(Command):
    def __init__(self, question: str):
        super().__init__('info')
        self.question = question

    @classmethod
    def create_from_dict(cls, json_command: dict):
        question = json_command.get('question', '')
        return cls(question)


class ClickCommand(LocatableCommand):
    def __init__(self, node: Node):
        super().__init__('click', node)

    @classmethod
    def create_from_dict(cls, json_command: dict):
        json_target_node = json_command.get('target', {})
        target_node = Node.createNodeFromDict(json_target_node)
        return cls(target_node)


class NavigateCommand(Command):
    def __init__(self, action: str):
        super().__init__(action)

    @classmethod
    def create_from_dict(cls, json_command: dict):
        action = json_command.get('action', "NOP")
        return cls(action)


class NextCommand(NavigateCommand):
    def __init__(self):
        super().__init__('next')

    @classmethod
    def create_from_dict(cls, json_command: dict):
        return cls()


class PreviousCommand(NavigateCommand):
    def __init__(self):
        super().__init__('previous')

    @classmethod
    def create_from_dict(cls, json_command: dict):
        return cls()


class SelectCommand(NavigateCommand):
    def __init__(self):
        super().__init__('select')

    @classmethod
    def create_from_dict(cls, json_command: dict):
        return cls()


class CommandResponse(JSONSerializable):
    def __init__(self, command_type: str, state: str, duration: int, **kwargs):
        self.type = command_type
        self.state = state
        self.duration = duration

    @classmethod
    def get_kwargs_from_response(cls, response: dict) -> dict:
        if response is None:
            return {
                'command_type': 'UnknownNone',
                'state': 'UnknownNone',
                'duration': -1,
            }
        return {
            'command_type': response.get('type', response.get('command_type', 'Unknown')),
            'state': response.get('state', 'Unknown'),
            'duration': int(response.get('duration', -1)),
        }

    @classmethod
    def create_from_response(cls, response: dict):
        return cls(**cls.get_kwargs_from_response(response))


class LocatableCommandResponse(CommandResponse):
    def __init__(self, target_node: Node, acted_node: Node, locating_attempts: int = -1, **kwargs):
        super().__init__(**kwargs)
        self.target_node = target_node
        self.acted_node = acted_node
        self.locating_attempts = locating_attempts

    @classmethod
    def get_kwargs_from_response(cls, response: dict) -> dict:
        kwargs = super().get_kwargs_from_response(response)
        kwargs['target_node'] = Node.createNodeFromDict(response.get('targetWidget', response.get('target_node', {})))
        kwargs['acted_node'] = Node.createNodeFromDict(response.get('actedWidget', response.get('acted_node', {})))
        kwargs['locating_attempts'] = response.get('locatingAttempts', response.get('locating_attempts', -1))
        return kwargs


class NavigateCommandResponse(CommandResponse):
    def __init__(self, navigated_node: Node, **kwargs):
        super().__init__(**kwargs)
        self.navigated_node = navigated_node

    @classmethod
    def get_kwargs_from_response(cls, response: dict) -> dict:
        kwargs = super().get_kwargs_from_response(response)
        kwargs['navigated_node'] = Node.createNodeFromDict(response.get('navigatedWidget', response.get('navigated_node', {})))
        return kwargs


class InfoCommandResponse(CommandResponse):
    def __init__(self, answer: str, **kwargs):
        super().__init__(**kwargs)
        self.answer = answer

    @classmethod
    def get_kwargs_from_response(cls, response: dict) -> dict:
        kwargs = super().get_kwargs_from_response(response)
        kwargs['answer'] = Node.createNodeFromDict(response.get('result', response.get('answer', {})))
        return kwargs


def create_command_response_from_dict(command: Command, result: dict) -> CommandResponse:
    if isinstance(command, LocatableCommand):
        response = LocatableCommandResponse.create_from_response(result)
    elif isinstance(command, NavigateCommand):
        response = NavigateCommandResponse.create_from_response(result)
    elif isinstance(command, InfoCommand):
        response = InfoCommandResponse.create_from_response(result)
    else:
        response = CommandResponse.create_from_response(result)
    return response


def create_command_from_dict(json_command: dict) -> Command:
    if 'action' not in json_command:
        return Command()
    action = json_command['action']
    if action == 'click':
        return ClickCommand.create_from_dict(json_command)
    elif action == 'info':
        return InfoCommand.create_from_dict(json_command)
    elif action == 'next':
        return NextCommand.create_from_dict(json_command)
    elif action == 'previous':
        return PreviousCommand.create_from_dict(json_command)
    elif action == 'select':
        return SelectCommand.create_from_dict(json_command)
    else:
        return Command()