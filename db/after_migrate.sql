-- Correr después de copiar datos, para que los ID autonuméricos sigan desde el máximo.

select setval(pg_get_serial_sequence('cuentas_usuario', 'id'), coalesce((select max(id) from cuentas_usuario), 1));
select setval(pg_get_serial_sequence('cuentas_usuarioarea', 'id'), coalesce((select max(id) from cuentas_usuarioarea), 1));
select setval(pg_get_serial_sequence('indicadores_areadireccion', 'id'), coalesce((select max(id) from indicadores_areadireccion), 1));
select setval(pg_get_serial_sequence('indicadores_dimension', 'id'), coalesce((select max(id) from indicadores_dimension), 1));
select setval(pg_get_serial_sequence('indicadores_responsable', 'id'), coalesce((select max(id) from indicadores_responsable), 1));
select setval(pg_get_serial_sequence('indicadores_periodo', 'id'), coalesce((select max(id) from indicadores_periodo), 1));
select setval(pg_get_serial_sequence('indicadores_indicador', 'id'), coalesce((select max(id) from indicadores_indicador), 1));
select setval(pg_get_serial_sequence('indicadores_indicadorversion', 'id'), coalesce((select max(id) from indicadores_indicadorversion), 1));
select setval(pg_get_serial_sequence('indicadores_metaperiodo', 'id'), coalesce((select max(id) from indicadores_metaperiodo), 1));
select setval(pg_get_serial_sequence('indicadores_medicion', 'id'), coalesce((select max(id) from indicadores_medicion), 1));
