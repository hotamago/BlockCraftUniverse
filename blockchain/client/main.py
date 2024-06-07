from typing import Optional
import uvicorn

from fastapi import FastAPI, Body, Depends, HTTPException,  File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from config import *
from pydantic import BaseModel
import json

# import data
from hotaSolana.hotaSolanaDataBase import *
from hotaSolana.hotaSolanaData import *
from hotaSolana.bs58 import bs58

from baseAPI import *

description = """
hotaSolana API helps you do awesome stuff. 🚀

- block = 8x8x8
- 1 world max = 32x32x32x32x32x32 block = 8x8x8 x 32x32x32x32x32x32  small block (when init, world is empty)
- 1 store max = 256 store or 256 block
- 1 item max = 32x32x32 block = 8x8x8 x 32x32x32 small block
- 1 block = 8x8x8 small block = 512 bytes, so max is 2^8 = 256 type small block
"""

app = FastAPI(title="Solana API",
              description=description,
              summary="This is a Solana API",
              version="v2.0",
              contact={
                  "name": "Hotamago Master",
                  "url": "https://www.linkedin.com/in/hotamago/",
              })

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Solana Client
client = HotaSolanaRPC(programId, False, "devnet")

# Solana instruction data
@BaseStructClass
class XYZ:
    x=HotaUint64(0)
    y=HotaUint64(0)
    z=HotaUint64(0)

@BaseStructClass
class Block:
    owner=HotaPublicKey()
    xyz=XYZ()
    price=HotaUint64(0)
    data=HotaArrayStruct(512, lambda: HotaUint8(0))

@BaseStructClass
class Store:
    depth=HotaUint8(0)
    pubkeys=HotaArrayStruct(32, lambda: HotaPublicKey())
    status=HotaArrayStruct(32, lambda: HotaUint8(0))

# Solana instruction
@BaseInstructionDataClass("init_block")
class InitBlockInstruction:
    xyz=XYZ()
    price=HotaUint64(0)
    data=HotaArrayStruct(512, lambda: HotaUint8(0))
    seed_random=HotaUint128(0)

@BaseInstructionDataClass("init_store")
class InitStoreInstruction:
    depth=HotaUint8(0)
    seed_random=HotaUint128(0)

@BaseInstructionDataClass("set_ele_store")
class SetEleStoreInstruction:
    index=HotaUint8(0)

@BaseInstructionDataClass("set_block_store")
class SetBlockStoreInstruction:
    index=HotaUint8(0)

@BaseInstructionDataClass("update_block")
class UpdateBlockInstruction:
    xyz=XYZ()
    price=HotaUint64(0)
    data=HotaArrayStruct(512, lambda: HotaUint8(0))

@BaseInstructionDataClass("trade_block")
class TradeBlockInstruction:
    pass

# Store class
def _init_store_cal(
    depth: int,
):
    # init store instruction
    instruction_data = InitStoreInstruction()
    instruction_data.get("depth").object2struct(depth)
    instruction_data.get("seed_random").random()

    store_pubkey = findProgramAddress(createBytesFromArrayBytes(
        "store".encode("utf-8"),
        bytes(instruction_data.get("depth").serialize()),
        bytes(instruction_data.get("seed_random").serialize())
    ),
    client.program_id)

    transaction_address = client.send_transaction(
        instruction_data,
        [
            makeKeyPair(payerPrivateKey).public_key,
            store_pubkey,
            makePublicKey(sysvar_rent),
            makePublicKey(system_program),
        ],
        [
            makeKeyPair(payerPrivateKey),
        ],
        makeKeyPair(payerPrivateKey).public_key
    )

    return {
        "transaction_address": transaction_address,
        "public_key": bs58.encode(store_pubkey.byte_value),
    }

def _set_ele_store(
    hi_store: str,
    lo_store: str,
    index: int,
):
    hi_store_pubkey = makePublicKey(hi_store)
    lo_store_pubkey = makePublicKey(lo_store)

    # set ele store instruction
    instruction_data = SetEleStoreInstruction()
    instruction_data.get("index").object2struct(index)

    transaction_address = client.send_transaction(
        instruction_data,
        [
            makeKeyPair(payerPrivateKey).public_key,
            hi_store_pubkey,
            lo_store_pubkey,
            makePublicKey(sysvar_rent),
            makePublicKey(system_program),
        ],
        [
            makeKeyPair(payerPrivateKey),
        ],
        makeKeyPair(payerPrivateKey).public_key
    )

    return {
        "transaction_address": transaction_address,
        "public_key": bs58.encode(hi_store_pubkey.byte_value),
    }

def _set_block_store(
    owner_block: Keypair,
    store: str,
    block: str,
    index: int,
):
    store_pubkey = makePublicKey(store)
    block_pubkey = makePublicKey(block)

    # set block store instruction
    instruction_data = SetBlockStoreInstruction()
    instruction_data.get("index").object2struct(index)

    transaction_address = client.send_transaction(
        instruction_data,
        [
            makeKeyPair(payerPrivateKey).public_key,
            owner_block.public_key,
            store_pubkey,
            block_pubkey,
            makePublicKey(sysvar_rent),
            makePublicKey(system_program),
        ],
        [
            makeKeyPair(payerPrivateKey),
            owner_block,
        ],
        makeKeyPair(payerPrivateKey).public_key
    )

    return {
        "transaction_address": transaction_address,
        "public_key": bs58.encode(block_pubkey.byte_value),
    }

@BaseStoreDataClass(
    _depth=6,
    _client_rpg=client,
    _block_class=Block,
    _init_store_cal=_init_store_cal,
    _set_ele_store=_set_ele_store,
    _set_block_store=_set_block_store,
)
class World:
    pass

@BaseStoreDataClass(
    _depth=3,
    _client_rpg=client,
    _block_class=Block,
    _init_store_cal=_init_store_cal,
    _set_ele_store=_set_ele_store,
    _set_block_store=_set_block_store,
)
class Item:
    pass

##### Router
class XYZModel(BaseModel):
    x: int
    y: int
    z: int

class InitBlockModel(BaseModel):
    owner_private_key: str
    xyz: XYZModel
    price: int
    data: list[int] = [0]*512

@app.post("/init-block")
async def init_block(data: InitBlockModel):
    def fun():
        owner_keypair = makeKeyPair(data.owner_private_key)

        instruction_data = InitBlockInstruction()
        instruction_data.get("xyz").get("x").object2struct(data.xyz.x)
        instruction_data.get("xyz").get("y").object2struct(data.xyz.y)
        instruction_data.get("xyz").get("z").object2struct(data.xyz.z)
        instruction_data.get("price").object2struct(data.price)
        instruction_data.get("data").deserialize(data.data)
        instruction_data.get("seed_random").random()

        block_pubkey = findProgramAddress(createBytesFromArrayBytes(
            owner_keypair.public_key.byte_value,
            "block".encode("utf-8"),
            bytes(instruction_data.get("seed_random").serialize())
        ),
        client.program_id)

        transaction_address = client.send_transaction(
            instruction_data,
            [
                makeKeyPair(payerPrivateKey).public_key,
                owner_keypair.public_key,
                block_pubkey,
                makePublicKey(sysvar_rent),
                makePublicKey(system_program),
            ],
            [
                makeKeyPair(payerPrivateKey),
                owner_keypair
            ],
            makeKeyPair(payerPrivateKey).public_key
        )

        return {
            "transaction_address": transaction_address,
            "public_key": bs58.encode(block_pubkey.byte_value),
        }

    return make_response_auto_catch(fun)


# Update block
class UpdateBlockModel(BaseModel):
    owner_private_key: str
    block_public_key: str
    xyz: XYZModel
    price: int
    data: list[int] = [0]*512

@app.post("/update-block")
async def update_block(data: UpdateBlockModel):
    def fun():
        owner_keypair = makeKeyPair(data.owner_private_key)
        block_pubkey = makePublicKey(data.block_public_key)

        instruction_data = UpdateBlockInstruction()
        instruction_data.get("xyz").get("x").object2struct(data.xyz.x)
        instruction_data.get("xyz").get("y").object2struct(data.xyz.y)
        instruction_data.get("xyz").get("z").object2struct(data.xyz.z)
        instruction_data.get("price").object2struct(data.price)
        instruction_data.get("data").deserialize(data.data)

        transaction_address = client.send_transaction(
            instruction_data,
            [
                makeKeyPair(payerPrivateKey).public_key,
                owner_keypair.public_key,
                block_pubkey,
                makePublicKey(sysvar_rent),
                makePublicKey(system_program),
            ],
            [
                makeKeyPair(payerPrivateKey),
                owner_keypair
            ],
            makeKeyPair(payerPrivateKey).public_key
        )

        return {
            "transaction_address": transaction_address,
            "public_key": bs58.encode(block_pubkey.byte_value),
        }

    return make_response_auto_catch(fun)

# Trade block
class TradeBlockModel(BaseModel):
    owner_private_key: str
    buyer_private_key: str
    block_public_key: str

@app.post("/trade-block")
async def trade_block(data: TradeBlockModel):
    def fun():
        owner_keypair = makeKeyPair(data.owner_private_key)
        buyer_keypair = makeKeyPair(data.buyer_private_key)
        block_pubkey = makePublicKey(data.block_public_key)

        transaction_address = client.send_transaction(
            TradeBlockInstruction(),
            [
                makeKeyPair(payerPrivateKey).public_key,
                owner_keypair.public_key,
                buyer_keypair.public_key,
                block_pubkey,
                # makePublicKey(sysvar_rent),
                makePublicKey(system_program),
            ],
            [
                makeKeyPair(payerPrivateKey),
                owner_keypair,
                buyer_keypair
            ],
            makeKeyPair(payerPrivateKey).public_key
        )

        return {
            "transaction_address": transaction_address,
            "public_key": bs58.encode(block_pubkey.byte_value),
        }

    return make_response_auto_catch(fun)

# Init world
@app.post("/init-world")
async def init_world():
    def fun():
        return _init_store_cal(6)

    return make_response_auto_catch(fun)

@app.post("/init-item")
async def init_item():
    def fun():
        return _init_store_cal(3)

    return make_response_auto_catch(fun)

# World
@app.post("/get-block-by-ids-world")
async def get_block_by_ids_world(
    root_store_public_key: str,
    ids: list[int] = [0]*6,
):
    def fun():
        world:World = client.get_account_data_struct(PublicKey(root_store_public_key), World, [8, 0])
        pubkey, block = world.get_block_by_ids(ids)
        return {
            "public_key": bs58.encode(pubkey),
            "data": block.struct2object()
        }

    return make_response_auto_catch(fun)

@app.post("/set-block-by-ids-world")
async def set_block_by_ids_world(
    onwer_block_private_key: str,
    root_store_public_key: str,
    block_public_key: str,
    ids: list[int] = [0]*6,
):
    def fun():
        owner_block = makeKeyPair(onwer_block_private_key)
        root_store_pubkey = makePublicKey(root_store_public_key)
        block_pubkey = makePublicKey(block_public_key)
        world:World = client.get_account_data_struct(root_store_pubkey, World, [8, 0])
        return world.set_block_by_ids(
            owner_block,
            ids,
            block_pubkey,
            root_store_pubkey
        )

    return make_response_auto_catch(fun)

# Item
@app.post("/get-block-by-ids-item")
async def get_block_by_ids_item(
    root_store_public_key: str,
    ids: list[int] = [0]*3,
):
    def fun():
        item:Item = client.get_account_data_struct(PublicKey(root_store_public_key), Item, [8, 0])
        pubkey, block = item.get_block_by_ids(ids)
        return {
            "public_key": bs58.encode(pubkey),
            "data": block.struct2object()
        }

    return make_response_auto_catch(fun)

@app.post("/set-block-by-ids-item")
async def set_block_by_ids_item(
    onwer_block_private_key: str,
    root_store_public_key: str,
    block_public_key: str,
    ids: list[int] = [0]*3,
):
    def fun():
        owner_block = makeKeyPair(onwer_block_private_key)
        root_store_pubkey = makePublicKey(root_store_public_key)
        block_pubkey = makePublicKey(block_public_key)
        item:Item = client.get_account_data_struct(root_store_pubkey, Item, [8, 0])
        return item.set_block_by_ids(
            owner_block,
            ids,
            block_pubkey,
            root_store_pubkey
        )

    return make_response_auto_catch(fun)

#### Common function1
@app.post("/convert-keypair-to-private-key")
async def convert_keypair_to_private_key(file: UploadFile):
    # Bytes to string
    result = file.file.read()
    keypair_json = json.loads(result)
    keypair_bytes = bytes(keypair_json)
    return {
        "public_key": bs58.encode(keypair_bytes[32:]),
        "private_key": bs58.encode(keypair_bytes),
    }

@app.get("/get-info")
async def get_info(public_key: str):
    return make_response_auto_catch(lambda: client.get_account_info(PublicKey(public_key)))

@app.get("/get-store-data")
async def get_store_data(public_key: str):
    def fun():
        res: dict = client.get_account_data(PublicKey(public_key), Store, [8, 0])
        return res
    return make_response_auto_catch(fun)

@app.get("/get-block-data")
async def get_block_data(public_key: str):
    def fun():
        res: dict = client.get_account_data(PublicKey(public_key), Block, [8, 0])
        return res
    return make_response_auto_catch(fun)

@app.get("/get-world-data")
async def get_world_data(public_key: str):
    def fun():
        res: dict = client.get_account_data(PublicKey(public_key), World, [8, 0])
        return res
    return make_response_auto_catch(fun)

@app.get("/get-item-data")
async def get_item_data(public_key: str):
    def fun():
        res: dict = client.get_account_data(PublicKey(public_key), Item, [8, 0])
        return res
    return make_response_auto_catch(fun)

@app.get("/get-balance")
async def get_balance(public_key: str):
    return make_response_auto_catch(client.get_balance(public_key))

@app.post("/airdrop")
async def airdrop(public_key: str, amount: int = 1):
    return make_response_auto_catch(client.drop_sol(public_key, amount))

# Run
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=openPortAPI)
