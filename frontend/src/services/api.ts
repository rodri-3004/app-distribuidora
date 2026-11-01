const API_URL = "http://127.0.0.1:8001";

export async function loginUsuario(email: string, clave: string) {
  const response = await fetch(`${API_URL}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, clave }),
  });

  if (!response.ok) {
    throw new Error("Error al iniciar sesión. Verificá tus credenciales.");
  }

  return await response.json();
}