#![allow(unused_imports)]
#![allow(unused_variables)]
#![allow(unused_mut)]

pub mod dot;

use anchor_lang::prelude::*;
use anchor_spl::{
    associated_token::{self, AssociatedToken},
    token::{self, Mint, Token, TokenAccount},
};

use dot::program::*;
use std::{cell::RefCell, rc::Rc};

declare_id!("FUBn5JHAAgbkgpg7sFA6YxhdrFrCgoyE7eXFtdszSU3b");

pub mod seahorse_util {
    use super::*;

    #[cfg(feature = "pyth-sdk-solana")]
    pub use pyth_sdk_solana::{load_price_feed_from_account_info, PriceFeed};
    use std::{collections::HashMap, fmt::Debug, ops::Deref};

    pub struct Mutable<T>(Rc<RefCell<T>>);

    impl<T> Mutable<T> {
        pub fn new(obj: T) -> Self {
            Self(Rc::new(RefCell::new(obj)))
        }
    }

    impl<T> Clone for Mutable<T> {
        fn clone(&self) -> Self {
            Self(self.0.clone())
        }
    }

    impl<T> Deref for Mutable<T> {
        type Target = Rc<RefCell<T>>;

        fn deref(&self) -> &Self::Target {
            &self.0
        }
    }

    impl<T: Debug> Debug for Mutable<T> {
        fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            write!(f, "{:?}", self.0)
        }
    }

    impl<T: Default> Default for Mutable<T> {
        fn default() -> Self {
            Self::new(T::default())
        }
    }

    impl<T: Clone> Mutable<Vec<T>> {
        pub fn wrapped_index(&self, mut index: i128) -> usize {
            if index >= 0 {
                return index.try_into().unwrap();
            }

            index += self.borrow().len() as i128;

            return index.try_into().unwrap();
        }
    }

    impl<T: Clone, const N: usize> Mutable<[T; N]> {
        pub fn wrapped_index(&self, mut index: i128) -> usize {
            if index >= 0 {
                return index.try_into().unwrap();
            }

            index += self.borrow().len() as i128;

            return index.try_into().unwrap();
        }
    }

    #[derive(Clone)]
    pub struct Empty<T: Clone> {
        pub account: T,
        pub bump: Option<u8>,
    }

    #[derive(Clone, Debug)]
    pub struct ProgramsMap<'info>(pub HashMap<&'static str, AccountInfo<'info>>);

    impl<'info> ProgramsMap<'info> {
        pub fn get(&self, name: &'static str) -> AccountInfo<'info> {
            self.0.get(name).unwrap().clone()
        }
    }

    #[derive(Clone, Debug)]
    pub struct WithPrograms<'info, 'entrypoint, A> {
        pub account: &'entrypoint A,
        pub programs: &'entrypoint ProgramsMap<'info>,
    }

    impl<'info, 'entrypoint, A> Deref for WithPrograms<'info, 'entrypoint, A> {
        type Target = A;

        fn deref(&self) -> &Self::Target {
            &self.account
        }
    }

    pub type SeahorseAccount<'info, 'entrypoint, A> =
        WithPrograms<'info, 'entrypoint, Box<Account<'info, A>>>;

    pub type SeahorseSigner<'info, 'entrypoint> = WithPrograms<'info, 'entrypoint, Signer<'info>>;

    #[derive(Clone, Debug)]
    pub struct CpiAccount<'info> {
        #[doc = "CHECK: CpiAccounts temporarily store AccountInfos."]
        pub account_info: AccountInfo<'info>,
        pub is_writable: bool,
        pub is_signer: bool,
        pub seeds: Option<Vec<Vec<u8>>>,
    }

    #[macro_export]
    macro_rules! seahorse_const {
        ($ name : ident , $ value : expr) => {
            macro_rules! $name {
                () => {
                    $value
                };
            }

            pub(crate) use $name;
        };
    }

    #[macro_export]
    macro_rules! assign {
        ($ lval : expr , $ rval : expr) => {{
            let temp = $rval;

            $lval = temp;
        }};
    }

    #[macro_export]
    macro_rules! index_assign {
        ($ lval : expr , $ idx : expr , $ rval : expr) => {
            let temp_rval = $rval;
            let temp_idx = $idx;

            $lval[temp_idx] = temp_rval;
        };
    }

    pub(crate) use assign;

    pub(crate) use index_assign;

    pub(crate) use seahorse_const;
}

#[program]
mod electra_chain {
    use super::*;
    use seahorse_util::*;
    use std::collections::HashMap;

    #[derive(Accounts)]
    # [instruction (xyz: XYZ , price : u64 , data: [u8; 512] , seed_random : u128)]
    pub struct InitBlock<'info> {
        #[account(mut)]
        pub payer: Signer<'info>,
        #[account(mut)]
        pub owner: Signer<'info>,
        # [account (init , space = std :: mem :: size_of :: < dot :: program :: Block > () + 8 , payer = payer , seeds = [owner . key () . as_ref () , "block" . as_bytes () . as_ref () , seed_random . to_le_bytes () . as_ref ()] , bump)]
        pub block: Box<Account<'info, dot::program::Block>>,
        pub rent: Sysvar<'info, Rent>,
        pub system_program: Program<'info, System>,
    }

    pub fn init_block(
        ctx: Context<InitBlock>,
        xyz: XYZ,
        price: u64,
        data: [u8; 512],
        seed_random: u128,
    ) -> Result<()> {
        let mut programs = HashMap::new();

        programs.insert(
            "system_program",
            ctx.accounts.system_program.to_account_info(),
        );

        let programs_map = ProgramsMap(programs);
        let payer = SeahorseSigner {
            account: &ctx.accounts.payer,
            programs: &programs_map,
        };

        let owner = SeahorseSigner {
            account: &ctx.accounts.owner,
            programs: &programs_map,
        };

        let block = Empty {
            account: dot::program::Block::load(&mut ctx.accounts.block, &programs_map),
            bump: Some(ctx.bumps.block),
        };

        init_block_handler(
            payer.clone(),
            owner.clone(),
            block.clone(),
            xyz,
            price,
            data,
            seed_random,
        );

        dot::program::Block::store(block.account);

        return Ok(());
    }

    #[derive(Accounts)]
    # [instruction (depth : u8 , seed_random : u128)]
    pub struct InitStore<'info> {
        #[account(mut)]
        pub payer: Signer<'info>,
        # [account (init , space = std :: mem :: size_of :: < dot :: program :: HotaStore > () + 8 , payer = payer , seeds = ["store" . as_bytes () . as_ref () , depth . to_le_bytes () . as_ref () , seed_random . to_le_bytes () . as_ref ()] , bump)]
        pub hota_store: Box<Account<'info, dot::program::HotaStore>>,
        pub rent: Sysvar<'info, Rent>,
        pub system_program: Program<'info, System>,
    }

    pub fn init_store(ctx: Context<InitStore>, depth: u8, seed_random: u128) -> Result<()> {
        let mut programs = HashMap::new();

        programs.insert(
            "system_program",
            ctx.accounts.system_program.to_account_info(),
        );

        let programs_map = ProgramsMap(programs);
        let payer = SeahorseSigner {
            account: &ctx.accounts.payer,
            programs: &programs_map,
        };

        let hota_store = Empty {
            account: dot::program::HotaStore::load(&mut ctx.accounts.hota_store, &programs_map),
            bump: Some(ctx.bumps.hota_store),
        };

        init_store_handler(payer.clone(), hota_store.clone(), depth, seed_random);

        dot::program::HotaStore::store(hota_store.account);

        return Ok(());
    }

    #[derive(Accounts)]
    # [instruction (index : u8)]
    pub struct SetBlockStore<'info> {
        #[account(mut)]
        pub payer: Signer<'info>,
        #[account(mut)]
        pub owner_block: Signer<'info>,
        #[account(mut)]
        pub hota_store: Box<Account<'info, dot::program::HotaStore>>,
        #[account(mut)]
        pub block: Box<Account<'info, dot::program::Block>>,
    }

    pub fn set_block_store(ctx: Context<SetBlockStore>, index: u8) -> Result<()> {
        let mut programs = HashMap::new();
        let programs_map = ProgramsMap(programs);
        let payer = SeahorseSigner {
            account: &ctx.accounts.payer,
            programs: &programs_map,
        };

        let owner_block = SeahorseSigner {
            account: &ctx.accounts.owner_block,
            programs: &programs_map,
        };

        let hota_store = dot::program::HotaStore::load(&mut ctx.accounts.hota_store, &programs_map);
        let block = dot::program::Block::load(&mut ctx.accounts.block, &programs_map);

        set_block_store_handler(
            payer.clone(),
            owner_block.clone(),
            hota_store.clone(),
            block.clone(),
            index,
        );

        dot::program::HotaStore::store(hota_store);

        dot::program::Block::store(block);

        return Ok(());
    }

    #[derive(Accounts)]
    # [instruction (index : u8)]
    pub struct SetEleStore<'info> {
        #[account(mut)]
        pub payer: Signer<'info>,
        #[account(mut)]
        pub hi_store: Box<Account<'info, dot::program::HotaStore>>,
        #[account(mut)]
        pub lo_store: Box<Account<'info, dot::program::HotaStore>>,
    }

    pub fn set_ele_store(ctx: Context<SetEleStore>, index: u8) -> Result<()> {
        let mut programs = HashMap::new();
        let programs_map = ProgramsMap(programs);
        let payer = SeahorseSigner {
            account: &ctx.accounts.payer,
            programs: &programs_map,
        };

        let hi_store = dot::program::HotaStore::load(&mut ctx.accounts.hi_store, &programs_map);
        let lo_store = dot::program::HotaStore::load(&mut ctx.accounts.lo_store, &programs_map);

        set_ele_store_handler(payer.clone(), hi_store.clone(), lo_store.clone(), index);

        dot::program::HotaStore::store(hi_store);

        dot::program::HotaStore::store(lo_store);

        return Ok(());
    }

    #[derive(Accounts)]
    pub struct TradeBlock<'info> {
        #[account(mut)]
        pub payer: Signer<'info>,
        #[account(mut)]
        pub old_onwer: Signer<'info>,
        #[account(mut)]
        pub new_owner: Signer<'info>,
        #[account(mut)]
        pub block: Box<Account<'info, dot::program::Block>>,
        pub system_program: Program<'info, System>,
    }

    pub fn trade_block(ctx: Context<TradeBlock>) -> Result<()> {
        let mut programs = HashMap::new();

        programs.insert(
            "system_program",
            ctx.accounts.system_program.to_account_info(),
        );

        let programs_map = ProgramsMap(programs);
        let payer = SeahorseSigner {
            account: &ctx.accounts.payer,
            programs: &programs_map,
        };

        let old_onwer = SeahorseSigner {
            account: &ctx.accounts.old_onwer,
            programs: &programs_map,
        };

        let new_owner = SeahorseSigner {
            account: &ctx.accounts.new_owner,
            programs: &programs_map,
        };

        let block = dot::program::Block::load(&mut ctx.accounts.block, &programs_map);

        trade_block_handler(
            payer.clone(),
            old_onwer.clone(),
            new_owner.clone(),
            block.clone(),
        );

        dot::program::Block::store(block);

        return Ok(());
    }

    #[derive(Accounts)]
    # [instruction (xyz: XYZ , price : u64 , data: [u8; 512])]
    pub struct UpdateBlock<'info> {
        #[account(mut)]
        pub payer: Signer<'info>,
        #[account(mut)]
        pub owner_block: Signer<'info>,
        #[account(mut)]
        pub block: Box<Account<'info, dot::program::Block>>,
    }

    pub fn update_block(
        ctx: Context<UpdateBlock>,
        xyz: XYZ,
        price: u64,
        data: [u8; 512],
    ) -> Result<()> {
        let mut programs = HashMap::new();
        let programs_map = ProgramsMap(programs);
        let payer = SeahorseSigner {
            account: &ctx.accounts.payer,
            programs: &programs_map,
        };

        let owner_block = SeahorseSigner {
            account: &ctx.accounts.owner_block,
            programs: &programs_map,
        };

        let block = dot::program::Block::load(&mut ctx.accounts.block, &programs_map);

        update_block_handler(
            payer.clone(),
            owner_block.clone(),
            block.clone(),
            xyz,
            price,
            data,
        );

        dot::program::Block::store(block);

        return Ok(());
    }
}
