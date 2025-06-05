from aenum import Enum, extend_enum

class Index(Enum):
    DeviceType    = 0x1000
    ErrorRegister = 0x1001

for name, value in (
        ('ControlWord', 0x6040),
        ('StatusWord', 0x6041),
        ('OperationMode', 0x6060),
        ):
    extend_enum(Index, name, value)

assert len(Index) == 5
assert list(Index) == [Index.DeviceType, Index.ErrorRegister, Index.ControlWord, Index.StatusWord, Index.OperationMode]
assert Index.DeviceType.value == 0x1000
assert Index.StatusWord.value == 0x6041