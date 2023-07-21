import re
import asyncio
from typing import Dict, List, Literal, Optional

from sqlalchemy.sql import text
from sqlmodel import SQLModel, col
from sqlalchemy.future import select
from sqlalchemy import delete, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from .utils import SERVER, SR_SERVER
from .models import GsBind, GsPush, GsUser, GsCache


class SQLA:
    def __init__(self, url: str, bot_id: str, is_sr: bool = False):
        self.bot_id = bot_id
        self.is_sr = is_sr
        self.url = f'sqlite+aiosqlite:///{url}'
        self.engine = create_async_engine(self.url, pool_recycle=1500)
        self.async_session = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    def create_all(self):
        try:
            asyncio.create_task(self._create_all())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._create_all())
            loop.close()

    async def _create_all(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            await self.sr_adapter()

    async def sr_adapter(self):
        exec_list = [
            'ALTER TABLE GsBind ADD COLUMN group_id TEXT',
            'ALTER TABLE GsBind ADD COLUMN sr_uid TEXT',
            'ALTER TABLE GsUser ADD COLUMN sr_uid TEXT',
            'ALTER TABLE GsUser ADD COLUMN sr_region TEXT',
            'ALTER TABLE GsUser ADD COLUMN fp TEXT',
            'ALTER TABLE GsUser ADD COLUMN device_id TEXT',
            'ALTER TABLE GsUser ADD COLUMN sr_sign_switch TEXT DEFAULT "off"',
            'ALTER TABLE GsUser ADD COLUMN sr_push_switch TEXT DEFAULT "off"',
            'ALTER TABLE GsUser ADD COLUMN draw_switch TEXT DEFAULT "off"',
            'ALTER TABLE GsCache ADD COLUMN sr_uid TEXT',
        ]
        async with self.async_session() as session:
            for _t in exec_list:
                try:
                    await session.execute(text(_t))
                    await session.commit()
                except:  # noqa: E722
                    pass

    #####################
    # GsBind 部分 #
    #####################
    async def select_bind_data(self, user_id: str) -> Optional[GsBind]:
        async with self.async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(GsBind).where(
                        GsBind.user_id == user_id, GsBind.bot_id == self.bot_id
                    )
                )
                data = result.scalars().all()
                return data[0] if data else None

    async def insert_bind_data(self, user_id: str, **data) -> int:
        async with self.async_session() as session:
            async with session.begin():
                new_uid: str = data['uid'] if 'uid' in data else ''
                new_uid = new_uid.strip()
                new_sr_uid: str = data['sr_uid'] if 'sr_uid' in data else ''
                new_sr_uid = new_sr_uid.strip()
                if len(new_uid) != 9 and len(new_sr_uid) != 9:
                    return -1
                elif not new_uid.isdigit() and not new_sr_uid.isdigit():
                    return -3
                if new_uid and await self.bind_exists(user_id):
                    uid_list = await self.get_bind_uid_list(user_id)
                    if new_uid not in uid_list:
                        uid_list.append(new_uid)
                    else:
                        return -2
                    data['uid'] = '_'.join(uid_list)
                    await self.update_bind_data(user_id, data)
                elif new_sr_uid and await self.bind_exists(user_id):
                    sr_uid_list = await self.get_bind_sruid_list(user_id)
                    if new_sr_uid not in sr_uid_list:
                        sr_uid_list.append(new_sr_uid)
                    else:
                        return -2
                    data['sr_uid'] = '_'.join(sr_uid_list)
                    await self.update_bind_data(user_id, data)
                else:
                    new_data = GsBind(
                        user_id=user_id, bot_id=self.bot_id, **data
                    )
                    session.add(new_data)
                await session.commit()
                return 0

    async def delete_bind_data(self, user_id: str, **data) -> int:
        async with self.async_session() as session:
            async with session.begin():
                _uid = data['uid'] if 'uid' in data else ''
                _sr_uid = data['sr_uid'] if 'sr_uid' in data else ''
                if _uid and await self.bind_exists(user_id):
                    uid_list = await self.get_bind_uid_list(user_id)
                    if uid_list and _uid in uid_list:
                        uid_list.remove(_uid)
                    else:
                        return -1
                    data['uid'] = '_'.join(uid_list)
                    await self.update_bind_data(user_id, data)
                    await session.commit()
                    return 0
                elif _sr_uid and await self.bind_exists(user_id):
                    uid_list = await self.get_bind_sruid_list(user_id)
                    if uid_list and _sr_uid in uid_list:
                        uid_list.remove(_sr_uid)
                    else:
                        return -1
                    data['sr_uid'] = '_'.join(uid_list)
                    await self.update_bind_data(user_id, data)
                    await session.commit()
                    return 0
                else:
                    return -1

    async def update_bind_data(self, user_id: str, data: Optional[Dict]):
        async with self.async_session() as session:
            async with session.begin():
                sql = update(GsBind).where(
                    GsBind.user_id == user_id, GsBind.bot_id == self.bot_id
                )
                if data is not None:
                    query = sql.values(**data)
                    query.execution_options(synchronize_session='fetch')
                    await session.execute(query)

    async def bind_exists(self, user_id: str) -> bool:
        return bool(await self.select_bind_data(user_id))

    async def get_all_uid_list(self) -> List[str]:
        async with self.async_session() as session:
            async with session.begin():
                sql = select(GsBind).where(GsBind.bot_id == self.bot_id)
                result = await session.execute(sql)
                data: List[GsBind] = result.scalars().all()
                uid_list: List[str] = []
                for item in data:
                    uid_list.extend(item.uid.split("_") if item.uid else [])
                return uid_list

    async def get_bind_group_list(self, user_id: str) -> List[str]:
        data = await self.select_bind_data(user_id)
        return data.group_id.split("_") if data and data.group_id else []

    async def get_bind_group(self, user_id: str) -> Optional[str]:
        data = await self.get_bind_group_list(user_id)
        return data[0] if data else None

    async def get_group_all_uid(self, group_id: str):
        async with self.async_session() as session:
            async with session.begin():
                result = await session.scalars(
                    select(GsBind).where(
                        col(GsBind.group_id).contains(group_id)
                    )
                )
                data = result.all()
                return data[0] if data else None

    async def get_bind_uid_list(self, user_id: str) -> List[str]:
        data = await self.select_bind_data(user_id)
        return data.uid.split("_") if data and data.uid else []

    async def get_bind_uid(self, user_id: str) -> Optional[str]:
        data = await self.get_bind_uid_list(user_id)
        return data[0] if data else None

    async def get_bind_sruid_list(self, user_id: str) -> List[str]:
        data = await self.select_bind_data(user_id)
        return data.sr_uid.split("_") if data and data.sr_uid else []

    async def get_bind_sruid(self, user_id: str) -> Optional[str]:
        data = await self.get_bind_sruid_list(user_id)
        return data[0] if data else None

    async def switch_uid(
        self, user_id: str, uid: Optional[str] = None
    ) -> Optional[List]:
        uid_list = (
            await self.get_bind_sruid_list(user_id)
            if self.is_sr
            else await self.get_bind_uid_list(user_id)
        )
        id_type = 'sr_uid' if self.is_sr else 'uid'
        if uid_list and len(uid_list) >= 1:
            if uid and uid not in uid_list:
                return None
            elif uid:
                pass
            else:
                uid = uid_list[1]
            uid_list.remove(uid)
            uid_list.insert(0, uid)
            await self.update_bind_data(user_id, {id_type: '_'.join(uid_list)})
            return uid_list
        else:
            return None

    #####################
    # GsUser、GsCache 部分 #
    #####################

    async def select_user_data(self, uid: str) -> Optional[GsUser]:
        async with self.async_session() as session:
            async with session.begin():
                sql = (
                    select(GsUser).where(GsUser.sr_uid == uid)
                    if self.is_sr
                    else select(GsUser).where(GsUser.uid == uid)
                )
                result = await session.execute(sql)
                return data[0] if (data := result.scalars().all()) else None

    async def select_user_all_data_by_user_id(
        self, user_id: str
    ) -> Optional[List[GsUser]]:
        async with self.async_session() as session:
            async with session.begin():
                sql = select(GsUser).where(GsUser.user_id == user_id)
                result = await session.execute(sql)
                data = result.scalars().all()
                return data if data else None

    async def select_user_data_by_user_id(
        self, user_id: str
    ) -> Optional[GsUser]:
        data = await self.select_user_all_data_by_user_id(user_id)
        return data[0] if data else None

    async def select_cache_cookie(self, uid: str) -> Optional[str]:
        async with self.async_session() as session:
            async with session.begin():
                sql = (
                    select(GsCache).where(GsCache.sr_uid == uid)
                    if self.is_sr
                    else select(GsCache).where(GsCache.uid == uid)
                )
                result = await session.execute(sql)
                data: List[GsCache] = result.scalars().all()
                return data[0].cookie if len(data) >= 1 else None

    async def delete_error_cache(self) -> bool:
        async with self.async_session() as session:
            async with session.begin():
                data = await self.get_all_error_cookie()
                for cookie in data:
                    sql = delete(GsCache).where(GsCache.cookie == cookie)
                    await session.execute(sql)
                return True

    async def get_user_fp(self, uid: str) -> Optional[str]:
        data = await self.select_user_data(uid)
        return data.fp if data else None

    async def get_user_device_id(self, uid: str) -> Optional[str]:
        data = await self.select_user_data(uid)
        return data.device_id if data else None

    async def insert_cache_data(
        self,
        cookie: str,
        uid: Optional[str] = None,
        sr_uid: Optional[str] = None,
        mys_id: Optional[str] = None,
    ) -> bool:
        async with self.async_session() as session:
            async with session.begin():
                new_data = GsCache(
                    cookie=cookie, uid=uid, sr_uid=sr_uid, mys_id=mys_id
                )
                session.add(new_data)
                await session.commit()
                return True

    async def insert_user_data(
        self,
        user_id: str,
        uid: Optional[str] = None,
        sr_uid: Optional[str] = None,
        cookie: Optional[str] = None,
        stoken: Optional[str] = None,
        fp: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> bool:
        async with self.async_session() as session:
            async with session.begin():
                if uid and await self.user_exists(uid):
                    sql = (
                        update(GsUser)
                        .where(GsUser.uid == uid)
                        .values(
                            cookie=cookie,
                            status=None,
                            stoken=stoken,
                            bot_id=self.bot_id,
                            user_id=user_id,
                            sr_uid=sr_uid,
                            fp=fp,
                        )
                    )
                    await session.execute(sql)
                elif sr_uid and await self.user_exists(sr_uid):
                    sql = (
                        update(GsUser)
                        .where(GsUser.sr_uid == sr_uid)
                        .values(
                            cookie=cookie,
                            status=None,
                            stoken=stoken,
                            bot_id=self.bot_id,
                            user_id=user_id,
                            uid=uid,
                            fp=fp,
                        )
                    )
                    await session.execute(sql)
                else:
                    if cookie is None:
                        return False

                    account_id = re.search(r'account_id=(\d*)', cookie)
                    assert account_id is not None
                    account_id = str(account_id.group(1))

                    user_data = GsUser(
                        uid=uid,
                        sr_uid=sr_uid,
                        mys_id=account_id,
                        cookie=cookie,
                        stoken=stoken if stoken else None,
                        user_id=user_id,
                        bot_id=self.bot_id,
                        sign_switch='off',
                        push_switch='off',
                        bbs_switch='off',
                        draw_switch='off',
                        region=SERVER.get(uid[0], 'cn_gf01') if uid else None,
                        sr_region=SR_SERVER.get(sr_uid[0], None)
                        if sr_uid
                        else None,
                        fp=fp,
                        device_id=device_id,
                        sr_push_switch='off',
                        sr_sign_switch='off',
                    )
                    session.add(user_data)
                await session.commit()
                return True

    async def update_user_data(self, uid: str, data: Optional[Dict]):
        async with self.async_session() as session:
            async with session.begin():
                sql = (
                    update(GsUser).where(GsUser.sr_uid == uid)
                    if self.is_sr
                    else update(GsUser).where(GsUser.uid == uid)
                )
                if data is not None:
                    query = sql.values(**data)
                    query.execution_options(synchronize_session='fetch')
                    await session.execute(query)
                    await session.commit()

    async def delete_user_data(self, uid: str):
        async with self.async_session() as session:
            async with session.begin():
                if await self.user_exists(uid):
                    sql = (
                        delete(GsUser).where(GsUser.sr_uid == uid)
                        if self.is_sr
                        else delete(GsUser).where(GsUser.uid == uid)
                    )
                    await session.execute(sql)
                    await session.commit()
                    return True
                return False

    async def delete_cache(self):
        async with self.async_session() as session:
            async with session.begin():
                sql = (
                    update(GsUser)
                    .where(GsUser.status == 'limit30')
                    .values(status=None)
                )
                empty_sql = delete(GsCache)
                await session.execute(sql)
                await session.execute(empty_sql)
                await session.commit()

    async def mark_invalid(self, cookie: str, mark: str):
        async with self.async_session() as session:
            async with session.begin():
                sql = (
                    update(GsUser)
                    .where(GsUser.cookie == cookie)
                    .values(status=mark)
                )
                await session.execute(sql)
                await session.commit()

    async def user_exists(self, uid: str) -> bool:
        data = await self.select_user_data(uid)
        return True if data else False

    async def update_user_stoken(
        self, uid: str, stoken: Optional[str]
    ) -> bool:
        async with self.async_session() as session:
            async with session.begin():
                if await self.user_exists(uid):
                    sql = (
                        (
                            update(GsUser)
                            .where(GsUser.sr_uid == uid)
                            .values(stoken=stoken)
                        )
                        if self.is_sr
                        else (
                            update(GsUser)
                            .where(GsUser.uid == uid)
                            .values(stoken=stoken)
                        )
                    )
                    await session.execute(sql)
                    await session.commit()
                    return True
                return False

    async def update_user_cookie(
        self, uid: str, cookie: Optional[str]
    ) -> bool:
        async with self.async_session() as session:
            async with session.begin():
                if await self.user_exists(uid):
                    sql = (
                        (
                            update(GsUser)
                            .where(GsUser.sr_uid == uid)
                            .values(cookie=cookie)
                        )
                        if self.is_sr
                        else (
                            update(GsUser)
                            .where(GsUser.uid == uid)
                            .values(cookie=cookie)
                        )
                    )
                    await session.execute(sql)
                    await session.commit()
                    return True
                return False

    async def update_switch_status(self, uid: str, data: Dict) -> bool:
        async with self.async_session() as session:
            async with session.begin():
                if await self.user_exists(uid):
                    sql = (
                        (
                            update(GsUser)
                            .where(GsUser.sr_uid == uid)
                            .values(**data)
                        )
                        if self.is_sr
                        else (
                            update(GsUser)
                            .where(GsUser.uid == uid)
                            .values(**data)
                        )
                    )
                    await session.execute(sql)
                    await session.commit()
                    return True
                return False

    async def update_error_status(self, cookie: str, err: str) -> bool:
        async with self.async_session() as session:
            async with session.begin():
                sql = (
                    update(GsUser)
                    .where(GsUser.cookie == cookie)
                    .values(status=err)
                )
                await session.execute(sql)
                await session.commit()
                return True

    async def get_user_cookie(self, uid: str) -> Optional[str]:
        data = await self.select_user_data(uid)
        return data.cookie if data else None

    async def get_user_cookie_by_user_id(self, user_id: str) -> Optional[str]:
        data = await self.select_user_data_by_user_id(user_id)
        return data.cookie if data else None

    async def cookie_validate(self, uid: str) -> bool:
        data = await self.select_user_data(uid)
        return True if data and data.status is None else False

    async def get_user_stoken_by_user_id(self, user_id: str) -> Optional[str]:
        data = await self.select_user_data_by_user_id(user_id)
        return data.stoken if data and data.stoken else None

    async def get_user_stoken(self, uid: str) -> Optional[str]:
        data = await self.select_user_data(uid)
        return data.stoken if data and data.stoken else None

    async def get_all_user(self) -> List[GsUser]:
        async with self.async_session() as session:
            async with session.begin():
                sql = select(GsUser).where(
                    GsUser.cookie is not None, GsUser.cookie != ''
                )
                result = await session.execute(sql)
                data: List[GsUser] = result.scalars().all()
                return data

    async def get_all_cookie(self) -> List[str]:
        data = await self.get_all_user()
        return [_u.cookie for _u in data if _u.cookie]

    async def get_all_stoken(self) -> List[str]:
        data = await self.get_all_user()
        return [_u.stoken for _u in data if _u.stoken]

    async def get_all_error_cookie(self) -> List[str]:
        data = await self.get_all_user()
        return [_u.cookie for _u in data if _u.cookie and _u.status]

    async def get_all_push_user_list(self) -> List[GsUser]:
        data = await self.get_all_user()
        return [user for user in data if user.push_switch != 'off']

    async def get_random_cookie(self, uid: str) -> Optional[str]:
        async with self.async_session() as session:
            async with session.begin():
                # 有绑定自己CK 并且该CK有效的前提下，优先使用自己CK
                if await self.user_exists(uid) and await self.cookie_validate(
                    uid
                ):
                    return await self.get_user_cookie(uid)
                # 自动刷新缓存
                await self.delete_error_cache()
                # 获得缓存库Ck
                cache_data = await self.select_cache_cookie(uid)
                if cache_data is not None:
                    return cache_data
                # 随机取CK
                server = SERVER.get(uid[0], 'cn_gf01')
                sql = (
                    select(GsUser)
                    .where(GsUser.region == server)
                    .order_by(func.random())
                )
                data = await session.execute(sql)
                user_list: List[GsUser] = data.scalars().all()
                for user in user_list:
                    if not user.status and user.cookie:
                        # 进入缓存
                        if self.is_sr:
                            await self.insert_cache_data(
                                user.cookie, sr_uid=uid
                            )
                        else:
                            await self.insert_cache_data(user.cookie, uid)
                        return user.cookie
                    continue
                else:
                    return None

    async def get_switch_status_list(
        self, switch: Literal['push', 'sign', 'bbs', 'sr_push', 'sr_sign']
    ) -> List[GsUser]:
        async with self.async_session() as session:
            async with session.begin():
                _switch = getattr(GsUser, switch, GsUser.push_switch)
                sql = select(GsUser).filter(_switch != 'off')
                data = await session.execute(sql)
                data_list: List[GsUser] = data.scalars().all()
                return [user for user in data_list]

    #####################
    # GsPush 部分 #
    #####################
    async def insert_push_data(self, uid: str):
        async with self.async_session() as session:
            async with session.begin():
                push_data = GsPush(
                    bot_id=self.bot_id,
                    uid=uid,
                    coin_push='off',
                    coin_value=2100,
                    coin_is_push='off',
                    resin_push='on',
                    resin_value=140,
                    resin_is_push='off',
                    go_push='off',
                    go_value=120,
                    go_is_push='off',
                    transform_push='off',
                    transform_value=140,
                    transform_is_push='off',
                )
                session.add(push_data)
                await session.commit()

    async def update_push_data(self, uid: str, data: dict) -> bool:
        async with self.async_session() as session:
            async with session.begin():
                await self.push_exists(uid)
                sql = update(GsPush).where(GsPush.uid == uid).values(**data)
                await session.execute(sql)
                await session.commit()
                return True

    async def change_push_status(
        self,
        mode: Literal['coin', 'resin', 'go', 'transform'],
        uid: str,
        status: str,
    ):
        await self.update_push_data(uid, {f'{mode}_is_push': status})

    async def select_push_data(self, uid: str) -> Optional[GsPush]:
        async with self.async_session() as session:
            async with session.begin():
                await self.push_exists(uid)
                sql = select(GsPush).where(GsPush.uid == uid)
                result = await session.execute(sql)
                data = result.scalars().all()
                return data[0] if len(data) >= 1 else None

    async def push_exists(self, uid: str) -> bool:
        async with self.async_session() as session:
            async with session.begin():
                sql = select(GsPush).where(GsPush.uid == uid)
                result = await session.execute(sql)
                data = result.scalars().all()
                if not data:
                    await self.insert_push_data(uid)
                return True

    #####################
    # 杂项部分 #
    #####################

    async def refresh_cache(self, uid: str):
        async with self.async_session() as session:
            async with session.begin():
                sql = (
                    delete(GsCache).where(GsCache.sr_uid == uid)
                    if self.is_sr
                    else delete(GsCache).where(GsCache.uid == uid)
                )
                await session.execute(sql)
                return True

    async def close(self):
        async with self.async_session() as session:
            async with session.begin():
                await session.close()

    async def insert_new_bind(self, **kwargs):
        async with self.async_session() as session:
            async with session.begin():
                new_data = GsBind(**kwargs)
                session.add(new_data)
                await session.commit()

    async def insert_new_user(self, **kwargs):
        async with self.async_session() as session:
            async with session.begin():
                new_data = GsUser(**kwargs)
                session.add(new_data)
                await session.commit()
