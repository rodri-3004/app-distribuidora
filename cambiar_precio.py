import sqlite3
con = sqlite3.connect('base_datos/distribuidora.db')
con.execute("UPDATE productos SET precio = 9999 WHERE codigo = 'ACC-009'")
con.commit()
con.close()
print("¡Precio del Escobillón actualizado a $9.999 con éxito!")