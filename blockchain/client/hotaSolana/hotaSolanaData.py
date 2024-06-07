import time
from solathon.core.instructions import transfer, create_account, Instruction, AccountMeta
from solathon import Client, Transaction, PublicKey, Keypair
import random
from hotaSolana.hotaSolanaDataBase import *
from hotaSolana.hotaSolanaMeathod import *
from nacl.public import PrivateKey as NaclPrivateKey
import base64
from nacl.signing import SigningKey

class HotaSolanaRPC:
    def __init__(self, program_id: str, localhost=False, namenet="devnet"):
        self.program_id = PublicKey(program_id)
        self.localhost = localhost
        self.namenet = namenet
        self.urlNetSolana = ""

        if localhost:
            self.connection = Client(
                "http://localhost:8899")
            self.urlNetSolana = "http://localhost:8899"
            print("Connected to localhost")
        else:
            self.connection = Client(
                f"https://api.{namenet}.solana.com")
            self.urlNetSolana = f"https://api.{namenet}.solana.com"
            print(f"Connected to {namenet}")
    
    def get_account_info(self, public_key: PublicKey):
        account_info = self.connection.get_account_info(
            public_key, commitment={
                "encoding": "base64"
            })
        return account_info
    
    def get_account_data_struct(self, public_key: PublicKey, AccountDataClass: BaseStruct, shift_bytes = [8, 0]) -> BaseStruct:
        print(f"Get account data struct: {public_key}, type: {AccountDataClass.__name__}")
        account_info = self.get_account_info(public_key)
        account_data_bytes = base64.b64decode(account_info.data[0])
        print("Account data len: ", len(account_data_bytes))
        account_data = AccountDataClass()
        print("Local account data len: ", account_data.size())
        if shift_bytes[0] > 0:
            print("shift_left: ", account_data_bytes[:shift_bytes[0]].hex())
            account_data_bytes = account_data_bytes[shift_bytes[0]:]
        if shift_bytes[1] > 0:
            print("shift_right: ", account_data_bytes[-shift_bytes[1]:].hex())
            account_data_bytes = account_data_bytes[:-shift_bytes[1]]
            
        account_data.deserialize(account_data_bytes)
        return account_data

    def get_account_data(self, public_key: PublicKey, AccountDataClass: BaseStruct, shift_bytes = [8, 0]):
        return self.get_account_data_struct(public_key, AccountDataClass, shift_bytes).struct2object()

    def send_transaction(self, instruction_data: BaseStruct, pubkeys=[], keypairs=[], fee_payer: PublicKey = None):
        is_signers = [False] * len(pubkeys)
        # Unque keypairs
        dict_keypairs: dict[str, Keypair] = {}
        for keypair in keypairs:
            dict_keypairs[str(keypair.public_key)] = keypair
        keypairs = list(dict_keypairs.values())

        for keypair in keypairs:
            for i in range(len(pubkeys)):
                if keypair.public_key == pubkeys[i]:
                    is_signers[i] = True

        keys = [AccountMeta(public_key=pubkeys[i],
                            is_signer=is_signers[i], is_writable=True)
                for i in range(len(pubkeys))]

        instruction = Instruction(
            keys=keys,
            program_id=self.program_id,
            data=bytes(instruction_data.serialize()),
        )

        # print("Instruction data len: ", len(instruction_data.serialize()))

        transaction = Transaction(
            instructions=[
                instruction
            ],
            signers=keypairs, fee_payer=fee_payer
        )

        signature = self.connection.send_transaction(transaction)
        print(f"Transaction sent with signature {signature}")
        return signature
    
    def get_balance(self, public_key: PublicKey):
        balance = self.connection.get_balance(public_key)
        return balance
    
    def drop_sol(self, public_key: PublicKey, amount):
        sig = self.connection.request_airdrop(
            public_key, amount
        )
        print(f"Dropped {amount} SOL with signature {sig}")
        return sig

class HotaSolanaClient(HotaSolanaRPC):
    def __init__(self, program_id: str, localhost=False, namenet="devnet"):
        super().__init__(program_id, localhost, namenet)

    def make_key_pair(self, secret_key: str, seed = "hotaNFT"):
        self.keypair = Keypair.from_private_key(secret_key)
        print(f"Logged in with keypair {self.keypair.public_key}")

        self.public_key_seed = findProgramAddress(self.keypair.public_key, seed, self.program_id)

        print(
            f"Logged in with public_key_seed: {self.public_key_seed}")

        # Check if account is created
        try:
            self.connection.get_account_info(
                self.public_key_seed, commitment={
                    "encoding": "base64"
                })
            return {"public_key_with_seed": self.public_key_seed.__str__()}
        except Exception as e:
            raise Exception("Account not created")

    def drop_sol(self, amount):
        sig = self.connection.request_airdrop(
            self.keypair.public_key, amount
        )
        print(f"Dropped {amount} SOL with signature {sig}")
        return sig

    def get_balance(self):
        balance = self.connection.get_balance(self.keypair.public_key)
        return balance

    def get_account_info(self):
        return super().get_account_info(self.public_key_seed)

    def get_account_data(self, AccountDataClass: BaseStruct):
        return super().get_account_data(self.public_key_seed, AccountDataClass)

# Def filter BaseStruct
def FilterBaseStruct(dict_object):
    dict_object_copy = {}
    for key, value in dict_object.items():
        if isinstance(value, BaseStruct):
            dict_object_copy[key] = value
    return dict_object_copy

# @BaseStructClass
def BaseStructClass(object):
    dict_object = FilterBaseStruct(object.__dict__)
    class BaseStructClass(BaseStruct):
        def __init__(self, **kwargs):
            # Update kwargs to dict_object
            for key, value in kwargs.items():
                if key in dict_object:
                    dict_object[key] = value
            super().__init__(GenBaseEleList(dict_object))

    return BaseStructClass

# @BaseInstructionDataClass
def BaseInstructionDataClass(name: str):
    def inner_BaseInstructionDataClass(object):
        dict_object = FilterBaseStruct(object.__dict__)
        class BaseInstructionDataClass(BaseStruct):
            def __init__(self, **kwargs):
                nameHash = HotaHex(8)
                nameHash.deserialize(convertNameToHash8Bytes(name))
                # Update kwargs to dict_object
                for key, value in kwargs.items():
                    if key in dict_object:
                        dict_object[key] = value
                super().__init__(GenBaseEleList({
                    "typeInstruction": nameHash,
                    **dict_object
                }))

        return BaseInstructionDataClass
    return inner_BaseInstructionDataClass

# @BaseStoreDataClass
def BaseStoreDataClass(
    _depth: int,
    _client_rpg: HotaSolanaRPC,
    _block_class: callable,
    _init_store_cal: callable,
    _set_ele_store: callable,
    _set_block_store: callable,
    _max_len_pubkeys: int = 32,
    _num_try_get_data: int = 10,
):
    # _depth must > 0
    if _depth <= 0:
        raise Exception("Depth must > 0")
    
    def inner_BaseStoreDataClass(object):
        dict_object = FilterBaseStruct(object.__dict__)
        class LazyRPG:
            def __init__(self):
                self.elements = []
            def append(self, fun: callable):
                self.elements.append(fun)
            def __getitem__(self, key):
                # Check if element is callable
                if callable(self.elements[key]):
                    self.elements[key] = self.elements[key](key)
                return self.elements[key]
            def __setitem__(self, key, value):
                self.elements[key] = value
            def __len__(self):
                return len(self.elements)
            def fetch_all(self):
                for i in range(len(self.elements)):
                    if callable(self.elements[i]):
                        self.elements[i] = self.elements[i](i)
            def struct2object(self):
                object = []
                for i in range(len(self.elements)):
                    if callable(self.elements[i]):
                        self.elements[i] = self.elements[i](i)
                    if isinstance(self.elements[i], BaseStruct):
                        object.append(self.elements[i].struct2object())
                    elif self.elements[i] is None:
                        object.append(None)
                    else:
                        raise Exception(f"Element at index {i} is not BaseStruct or None")
                return object
        class BaseStoreDataClass(BaseStruct):
            def __init__(self, **kwargs):
                self.client_rpg = _client_rpg
                self.init_store_cal = _init_store_cal
                self.set_ele_store = _set_ele_store
                self.set_block_store = _set_block_store

                depth=HotaUint8(_depth)
                pubkeys=HotaArrayStruct(_max_len_pubkeys, lambda: HotaPublicKey())
                status=HotaArrayStruct(_max_len_pubkeys, lambda: HotaUint8(0))

                # Update kwargs to dict_object
                for key, value in kwargs.items():
                    if key in dict_object:
                        dict_object[key] = value
                super().__init__(GenBaseEleList({
                    "depth": depth,
                    "pubkeys": pubkeys,
                    "status": status,
                    **dict_object
                }))

                self.elements = None
                # Update element
                self.update_elements()

            def deserialize(self, buffers, index=0, checkSize=True):
                res = super().deserialize(buffers, index, checkSize)
                # Update element
                self.update_elements()
                return res
            
            def update_elements(self):
                self.elements = LazyRPG()
                for i in range(_max_len_pubkeys):
                    if self.get("status").get(i).struct2object() == 1:
                        if self.get("depth").struct2object() > 1:
                            self.elements.append(lambda x: self.loop_try(
                                self.client_rpg.get_account_data_struct,
                                self.get("pubkeys").get(x).struct2object(),
                                BaseStoreDataClass,
                                [8, 0],
                            ))
                        else:
                            self.elements.append(lambda x: self.loop_try(
                                self.client_rpg.get_account_data_struct,
                                self.get("pubkeys").get(x).struct2object(),
                                _block_class,
                                [8, 0],
                            ))
                    else:
                        self.elements.append(lambda x: None)

            def struct2object(self):
                object = super().struct2object()
                if self.elements is not None:
                    self.elements.fetch_all()
                    object["element"] = self.elements.struct2object()
                return object
            
            def loop_try(self, func, *args):
                for i in range(_num_try_get_data):
                    try:
                        return func(*args)
                    except Exception as e:
                        if str(e).find("Account details not found") != -1:
                            print(f"Error: {e}, at loop_try {i}")
                        else:
                            print(f"Unknow error: {e}")
                            break
                    
                    # Sleep 1 * (i + 1)
                    time.sleep(1 * (i + 1))
                raise Exception(f"Fails after {_num_try_get_data} tries to get data")
            
            def get_block_by_ids(self, ids: list[int]) -> tuple[PublicKey, BaseStruct]:
                print(f"Get block by ids: {ids}, depth: {self.get('depth').struct2object()}")
                depth = self.get("depth").struct2object()
                if len(ids) != depth:
                    raise Exception(f"Ids must have length = depth. Found ids = {ids}, depth = {depth}")
                i = ids[0]
                if self.get("status").get(i).struct2object() == 1:
                    if depth > 1:
                        return self.elements[i].get_block_by_ids(ids[1:])
                    else:
                        return self.get("pubkeys").get(i).struct2object(), self.elements[i]
                else:
                    raise Exception(f"Block not found at index {i} in get_block_by_ids\ndepth = {depth}\nids = {ids}")
            
            def set_block_by_ids(self, onwer_block: Keypair, ids: list[int], block_pubkey: PublicKey, pre_pubkey: PublicKey):
                print(f"Set block by ids: {ids}, depth: {self.get('depth').struct2object()}")

                block_pubkey_bs58 = bs58.encode(block_pubkey.byte_value)
                pre_pubkey_bs58 = bs58.encode(pre_pubkey.byte_value)
                depth = self.get("depth").struct2object()
                if len(ids) != depth:
                    raise Exception("Ids must have length = depth")
                i = ids[0]
                if depth > 1:
                    # Check if element is not available
                    if self.get("status").get(i).struct2object() == 0:
                        new_store_pubkey = self.init_store_cal(depth - 1)["public_key"]
                        self.elements[i] = self.loop_try(
                            self.client_rpg.get_account_data_struct,
                            makePublicKey(new_store_pubkey),
                            BaseStoreDataClass,
                            [8, 0],
                        )
                        self.get("pubkeys").get(i).object2struct(new_store_pubkey)
                        self.get("status").get(i).object2struct(1)
                        self.set_ele_store(pre_pubkey_bs58, new_store_pubkey, i)
                    # Set block
                    self.elements[i].set_block_by_ids(onwer_block, ids[1:], block_pubkey, PublicKey(self.get("pubkeys").get(i).struct2object()))
                else:
                    self.set_block_store(
                        onwer_block,
                        pre_pubkey_bs58,
                        block_pubkey_bs58,
                        i
                    )
                    self.elements[i] = self.loop_try(
                        self.client_rpg.get_account_data_struct,
                        makePublicKey(block_pubkey_bs58),
                        _block_class,
                        [8, 0],
                    )
                    self.get("pubkeys").get(i).object2struct(block_pubkey_bs58)
                    self.get("status").get(i).object2struct(1)
                    
                    return True
                
        return BaseStoreDataClass
    return inner_BaseStoreDataClass