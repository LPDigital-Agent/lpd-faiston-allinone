import { redirect } from "next/navigation";

/**
 * Asset Management Root Page
 *
 * Redirects to the dashboard as the default landing page
 * for the Gestão de Ativos platform.
 */
export default function AssetManagementPage() {
  redirect("/ferramentas/ativos/dashboard");
}
