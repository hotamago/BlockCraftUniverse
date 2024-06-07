# Built with Seahorse v0.2.0

from seahorse.prelude import *

# This is your program's public key and it will update
# automatically when you build the project.
declare_id('FUBn5JHAAgbkgpg7sFA6YxhdrFrCgoyE7eXFtdszSU3b')

class XYZ:
    x: u64
    y: u64
    z: u64

class Block(Account):
    owner: Pubkey
    xyz_XYZ_class: XYZ
    price: u64
    data_u8_512_array: Array[u8, 512]

class HotaStore(Account):
    depth: u8
    pubkeys_Pubkey_32_array: Array[Pubkey, 32]
    status_u8_32_array: Array[u8, 32]

@instruction
def init_store(
    payer: Signer,
    hota_store: Empty[HotaStore],
    depth: u8,
    seed_random: u128
):
    assert depth > 0, "depth of store much > 0"
    hota_store = hota_store.init(payer = payer, seeds = ["store", depth, seed_random])
    hota_store.depth = depth

@instruction
def init_block(
    payer: Signer,
    owner: Signer,
    block: Empty[Block],
    xyz_XYZ_class: XYZ,
    price: u64,
    data_u8_512_array: Array[u8, 512],
    seed_random: u128
):
    block = block.init(payer = payer, seeds = [owner, "block", seed_random])
    block.owner = owner.key()
    block.xyz_XYZ_class = xyz_XYZ_class
    block.price = price
    block.data_u8_512_array = data_u8_512_array

@instruction
def set_ele_store(
    payer: Signer,
    hi_store: HotaStore,
    lo_store: HotaStore,
    index: u8
):
    assert index < 32, "Index much be < 32"
    assert lo_store.depth > 0, "low node much have depth > 0"
    assert hi_store.depth == lo_store.depth + 1, "high node much have depth = low node depth + 1"
    assert hi_store.status_u8_32_array[index] == 0, "High node with given index not available"
    hi_store.pubkeys_Pubkey_32_array[index] = lo_store.key()
    hi_store.status_u8_32_array[index] = 1
    
@instruction
def set_block_store(
    payer: Signer,
    owner_block: Signer,
    hota_store: HotaStore,
    block: Block,
    index: u8
):
    assert index < 32, "Index much be < 32"
    assert owner_block.key() == block.owner, "Owner of block much be signer"
    assert hota_store.depth == 1, "Store much have depth = 1"
    assert hota_store.status_u8_32_array[index] == 0, "Store with given index not available"
    hota_store.pubkeys_Pubkey_32_array[index] = block.key()
    hota_store.status_u8_32_array[index] = 1

@instruction
def update_block(
    payer: Signer,
    owner_block: Signer,
    block: Block,
    xyz_XYZ_class: XYZ,
    price: u64,
    data_u8_512_array: Array[u8, 512],
):
    assert owner_block.key() == block.owner, "Owner of block much be signer"
    block.xyz_XYZ_class = xyz_XYZ_class
    block.price = price
    block.data_u8_512_array = data_u8_512_array

@instruction
def trade_block(
    payer: Signer,
    old_onwer: Signer,
    new_owner: Signer,
    block: Block,
):
    assert block.price > 0, "Block not for sale"
    assert old_onwer.key() == block.owner, "Owner of block much be signer"
    # Check if user have enough money
    # Transfer money to owner
    new_owner.transfer_lamports(old_onwer, block.price)
    block.owner = new_owner.key()