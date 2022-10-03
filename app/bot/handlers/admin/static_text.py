command_start = '/stats'
only_for_admins = 'К сожалению, эта функция доступна только для администраторов. Установить флаг «админ» в админ панели'
secret_admin_commands = f"⚠️ Команды администратора\n" \
                        f"{command_start} - статистика\n" \
                        "/export_users - экспорт пользователей\n" \

users_amount_stat = "<b>Пользователи</b>: {user_count}\n" \
                    "<b>активных за последние 24 часа</b>: {active_24}"

proxy_balance = """
<b>Куплено {count} IPv{version} прокси на сумму {price}</b>\n
Текущий баланс акаунта <b>{accautn_balance}</b>\n
<a href='https://proxy6.net/en/user/balance'>Пополнить баланс</a>
"""
balance_error = """
<b>СРОЧНО ПОПОЛНИТЕ БАЛАНС!!</b>
Текущий баланс акаунта <b>{accautn_balance}</b>\n\n
<b>Пользователь {user_id} не смог купить прокси на сумму {price}</b>
<a href='https://proxy6.net/en/user/balance'>Пополнить баланс</a>
"""