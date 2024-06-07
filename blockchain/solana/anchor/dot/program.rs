#![allow(unused_imports)]
#![allow(unused_variables)]
#![allow(unused_mut)]
use crate::{id, seahorse_util::*};
use anchor_lang::{prelude::*, solana_program};
use anchor_spl::token::{self, Mint, Token, TokenAccount};
use std::{cell::RefCell, rc::Rc};

#[account]
#[derive(Debug)]
pub struct Block {
    pub owner: Pubkey,
    pub xyz: XYZ,
    pub price: u64,
    pub data: [u8; 512],
}

impl<'info, 'entrypoint> Block {
    pub fn load(
        account: &'entrypoint mut Box<Account<'info, Self>>,
        programs_map: &'entrypoint ProgramsMap<'info>,
    ) -> Mutable<LoadedBlock<'info, 'entrypoint>> {
        let owner = account.owner.clone();
        let xyz = Mutable::new(account.xyz.clone());
        let price = account.price;
        let data = Mutable::new(account.data.clone());

        Mutable::new(LoadedBlock {
            __account__: account,
            __programs__: programs_map,
            owner,
            xyz,
            price,
            data,
        })
    }

    pub fn store(loaded: Mutable<LoadedBlock>) {
        let mut loaded = loaded.borrow_mut();
        let owner = loaded.owner.clone();

        loaded.__account__.owner = owner;

        let xyz = loaded.xyz.borrow().clone();

        loaded.__account__.xyz = xyz;

        let price = loaded.price;

        loaded.__account__.price = price;

        let data = loaded.data.borrow().clone();

        loaded.__account__.data = data;
    }
}

#[derive(Debug)]
pub struct LoadedBlock<'info, 'entrypoint> {
    pub __account__: &'entrypoint mut Box<Account<'info, Block>>,
    pub __programs__: &'entrypoint ProgramsMap<'info>,
    pub owner: Pubkey,
    pub xyz: Mutable<XYZ>,
    pub price: u64,
    pub data: Mutable<[u8; 512]>,
}

#[account]
#[derive(Debug)]
pub struct HotaStore {
    pub depth: u8,
    pub pubkeys: [Pubkey; 32],
    pub status: [u8; 32],
}

impl<'info, 'entrypoint> HotaStore {
    pub fn load(
        account: &'entrypoint mut Box<Account<'info, Self>>,
        programs_map: &'entrypoint ProgramsMap<'info>,
    ) -> Mutable<LoadedHotaStore<'info, 'entrypoint>> {
        let depth = account.depth;
        let pubkeys = Mutable::new(account.pubkeys.clone());
        let status = Mutable::new(account.status.clone());

        Mutable::new(LoadedHotaStore {
            __account__: account,
            __programs__: programs_map,
            depth,
            pubkeys,
            status,
        })
    }

    pub fn store(loaded: Mutable<LoadedHotaStore>) {
        let mut loaded = loaded.borrow_mut();
        let depth = loaded.depth;

        loaded.__account__.depth = depth;

        let pubkeys = loaded.pubkeys.borrow().clone();

        loaded.__account__.pubkeys = pubkeys;

        let status = loaded.status.borrow().clone();

        loaded.__account__.status = status;
    }
}

#[derive(Debug)]
pub struct LoadedHotaStore<'info, 'entrypoint> {
    pub __account__: &'entrypoint mut Box<Account<'info, HotaStore>>,
    pub __programs__: &'entrypoint ProgramsMap<'info>,
    pub depth: u8,
    pub pubkeys: Mutable<[Pubkey; 32]>,
    pub status: Mutable<[u8; 32]>,
}

#[derive(Clone, AnchorSerialize, AnchorDeserialize, Debug, Default)]
pub struct XYZ {
    pub x: u64,
    pub y: u64,
    pub z: u64,
}

pub fn init_block_handler<'info>(
    mut payer: SeahorseSigner<'info, '_>,
    mut owner: SeahorseSigner<'info, '_>,
    mut block: Empty<Mutable<LoadedBlock<'info, '_>>>,
    mut xyz: XYZ,
    mut price: u64,
    mut data: [u8; 512],
    mut seed_random: u128,
) -> () {
    let mut block = block.account.clone();

    assign!(block.borrow_mut().owner, owner.key());

    assign!(block.borrow_mut().xyz, Mutable::<XYZ>::new(xyz));

    assign!(block.borrow_mut().price, price);

    assign!(block.borrow_mut().data, Mutable::<[u8; 512]>::new(data));
}

pub fn init_store_handler<'info>(
    mut payer: SeahorseSigner<'info, '_>,
    mut hota_store: Empty<Mutable<LoadedHotaStore<'info, '_>>>,
    mut depth: u8,
    mut seed_random: u128,
) -> () {
    if !(depth > 0) {
        panic!("depth of store much > 0");
    }

    let mut hota_store = hota_store.account.clone();

    assign!(hota_store.borrow_mut().depth, depth);
}

pub fn set_block_store_handler<'info>(
    mut payer: SeahorseSigner<'info, '_>,
    mut owner_block: SeahorseSigner<'info, '_>,
    mut hota_store: Mutable<LoadedHotaStore<'info, '_>>,
    mut block: Mutable<LoadedBlock<'info, '_>>,
    mut index: u8,
) -> () {
    if !(index < 32) {
        panic!("Index much be < 32");
    }

    if !(owner_block.key() == block.borrow().owner) {
        panic!("Owner of block much be signer");
    }

    if !(hota_store.borrow().depth == 1) {
        panic!("Store much have depth = 1");
    }

    if !(hota_store.borrow().status.borrow()[hota_store
        .borrow()
        .status
        .wrapped_index((index as i128) as i128)]
        == 0)
    {
        panic!("Store with given index not available");
    }

    index_assign!(
        hota_store.borrow_mut().pubkeys.borrow_mut(),
        hota_store
            .borrow_mut()
            .pubkeys
            .wrapped_index((index as i128) as i128),
        block.borrow().__account__.key()
    );

    index_assign!(
        hota_store.borrow_mut().status.borrow_mut(),
        hota_store
            .borrow_mut()
            .status
            .wrapped_index((index as i128) as i128),
        1
    );
}

pub fn set_ele_store_handler<'info>(
    mut payer: SeahorseSigner<'info, '_>,
    mut hi_store: Mutable<LoadedHotaStore<'info, '_>>,
    mut lo_store: Mutable<LoadedHotaStore<'info, '_>>,
    mut index: u8,
) -> () {
    if !(index < 32) {
        panic!("Index much be < 32");
    }

    if !(lo_store.borrow().depth > 0) {
        panic!("low node much have depth > 0");
    }

    if !(hi_store.borrow().depth == (lo_store.borrow().depth + 1)) {
        panic!("high node much have depth = low node depth + 1");
    }

    if !(hi_store.borrow().status.borrow()[hi_store
        .borrow()
        .status
        .wrapped_index((index as i128) as i128)]
        == 0)
    {
        panic!("High node with given index not available");
    }

    index_assign!(
        hi_store.borrow_mut().pubkeys.borrow_mut(),
        hi_store
            .borrow_mut()
            .pubkeys
            .wrapped_index((index as i128) as i128),
        lo_store.borrow().__account__.key()
    );

    index_assign!(
        hi_store.borrow_mut().status.borrow_mut(),
        hi_store
            .borrow_mut()
            .status
            .wrapped_index((index as i128) as i128),
        1
    );
}

pub fn trade_block_handler<'info>(
    mut payer: SeahorseSigner<'info, '_>,
    mut old_onwer: SeahorseSigner<'info, '_>,
    mut new_owner: SeahorseSigner<'info, '_>,
    mut block: Mutable<LoadedBlock<'info, '_>>,
) -> () {
    if !(block.borrow().price > 0) {
        panic!("Block not for sale");
    }

    if !(old_onwer.key() == block.borrow().owner) {
        panic!("Owner of block much be signer");
    }

    solana_program::program::invoke(
        &solana_program::system_instruction::transfer(
            &new_owner.key(),
            &old_onwer.clone().key(),
            block.borrow().price.clone(),
        ),
        &[
            new_owner.to_account_info(),
            old_onwer.clone().to_account_info(),
            new_owner.programs.get("system_program").clone(),
        ],
    )
    .unwrap();

    assign!(block.borrow_mut().owner, new_owner.key());
}

pub fn update_block_handler<'info>(
    mut payer: SeahorseSigner<'info, '_>,
    mut owner_block: SeahorseSigner<'info, '_>,
    mut block: Mutable<LoadedBlock<'info, '_>>,
    mut xyz: XYZ,
    mut price: u64,
    mut data: [u8; 512],
) -> () {
    if !(owner_block.key() == block.borrow().owner) {
        panic!("Owner of block much be signer");
    }

    assign!(block.borrow_mut().xyz, Mutable::<XYZ>::new(xyz));

    assign!(block.borrow_mut().price, price);

    assign!(block.borrow_mut().data, Mutable::<[u8; 512]>::new(data));
}
