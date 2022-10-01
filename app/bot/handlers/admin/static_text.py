command_start = '/stats'
only_for_admins = 'К сожалению, эта функция доступна только для администраторов. Установить флаг «админ» в админ панели'
secret_admin_commands = f"⚠️ Команды администратора\n" \
                        f"{command_start} - статистика\n" \
                        "/export_users - экспорт пользователей\n" \

users_amount_stat = "<b>Пользователи</b>: {user_count}\n" \
                    "<b>активных за последние 24 часа</b>: {active_24}"
