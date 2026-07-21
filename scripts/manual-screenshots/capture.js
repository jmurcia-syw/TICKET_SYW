/**
 * Herramienta de documentacion (NO es parte de backend/frontend): navega SyWork Tickets en el
 * entorno de desarrollo local con Puppeteer y guarda capturas reales de los modulos clave en
 * docs/screenshots/, para insertarlas en docs/Manual_de_Usuario.docx.
 *
 * Requiere el stack de desarrollo corriendo (docker compose) y las credenciales semilla de
 * docs/credenciales_dev.txt (SOLO entorno de desarrollo). No usar contra un entorno productivo.
 *
 * Uso:
 *   pnpm install
 *   BASE_URL=http://localhost:5173 pnpm run capture
 */
const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const OUT_DIR = path.resolve(__dirname, '..', '..', 'docs', 'screenshots');
const CREDENTIALS = {
  user: process.env.SYWORK_USER || 'admin',
  pass: process.env.SYWORK_PASS || 'SyWork_Dev2026!',
};
const VIEWPORT = { width: 1440, height: 900 };

fs.mkdirSync(OUT_DIR, { recursive: true });

const results = [];

async function shot(page, name, opts = {}) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: !!opts.fullPage });
  console.log(`  guardado: ${name}.png`);
}

async function step(label, fn) {
  process.stdout.write(`- ${label} ... `);
  try {
    await fn();
    console.log('OK');
    results.push({ label, ok: true });
  } catch (err) {
    console.log(`FALLÓ (${err.message})`);
    results.push({ label, ok: false, error: err.message });
  }
}

async function goto(page, routePath) {
  await page.goto(`${BASE_URL}${routePath}`, { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 400)); // deja asentar animaciones/spinners de Ant Design
}

/** Click en el elemento cuyo texto propio coincide EXACTO (trim) dentro de un scope opcional. */
async function clickExactText(page, text, { scope, tag = '*' } = {}) {
  const clicked = await page.evaluate((txt, scopeSel, tagSel) => {
    // Si hay varios contenedores que matchean el scope (p.ej. un modal que se está cerrando
    // y otro que se está abriendo, ambos ".ant-modal" a la vez), usar solo los visibles.
    const roots = scopeSel ? Array.from(document.querySelectorAll(scopeSel)) : [document];
    const visibleRoots = roots.filter(r => !r.getClientRects || r.getClientRects().length > 0);
    const searchRoots = visibleRoots.length ? visibleRoots : roots;
    const els = searchRoots.flatMap(root => Array.from(root.querySelectorAll(tagSel)));
    const el = els.find(e => e.childElementCount === 0 && e.textContent.trim() === txt)
      || els.find(e => e.textContent.trim() === txt);
    if (!el) return false;
    (el.closest('button,a,[role="tab"],[role="menuitem"]') || el).click();
    return true;
  }, text, scope || null, tag);
  if (!clicked) throw new Error(`texto no encontrado: "${text}"`);
}

/** Click en el botón N-esimo (0-indexed) de la columna Acciones de la fila que contiene rowText. */
async function clickRowAction(page, rowText, actionIndex) {
  const clicked = await page.evaluate((txt, idx) => {
    const rows = Array.from(document.querySelectorAll('tr'));
    const row = rows.find(r => r.textContent.includes(txt));
    if (!row) return false;
    const buttons = row.querySelectorAll('button');
    if (!buttons[idx]) return false;
    buttons[idx].click();
    return true;
  }, rowText, actionIndex);
  if (!clicked) throw new Error(`fila/acción no encontrada: "${rowText}" [${actionIndex}]`);
}

async function login(page) {
  await goto(page, '/login');
  await shot(page, '00-login');
  await page.type('input[placeholder="usuario o correo@sywork.net"]', CREDENTIALS.user, { delay: 20 });
  await page.type('input[placeholder="Contraseña"]', CREDENTIALS.pass, { delay: 20 });
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {}),
    page.click('button[type="submit"]'),
  ]);
  await page.waitForSelector('text/Panel de Asignación', { timeout: 15000 });
}

/** Inicia sesión con credenciales arbitrarias (usada para el Usuario/cliente recién creado,
 * cuyo menú no incluye "Panel de Asignación" por lo que no puede reutilizar login()). */
async function loginAs(page, user, pass) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 400));
  await page.type('input[placeholder="usuario o correo@sywork.net"]', user, { delay: 20 });
  await page.type('input[placeholder="Contraseña"]', pass, { delay: 20 });
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 15000 }).catch(() => {}),
    page.click('button[type="submit"]'),
  ]);
  await page.waitForFunction(() => window.location.pathname === '/tickets', { timeout: 15000 });
  await new Promise(r => setTimeout(r, 400));
}

/** Click en la opción visible de un <Select> de Ant Design cuyo texto contiene `substring`. */
async function selectAntOption(page, substring) {
  const clicked = await page.evaluate((txt) => {
    const opts = Array.from(document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option'));
    const opt = opts.find(o => o.textContent.includes(txt));
    if (!opt) return false;
    opt.click();
    return true;
  }, substring);
  if (!clicked) throw new Error(`opción de select no encontrada: "${substring}"`);
}

/** Da de alta un Usuario/cliente demo desde Maestros > Usuarios/cliente (requiere sesión Admin
 * activa) y devuelve sus credenciales, incluida la contraseña provisional que la UI solo muestra
 * una vez. Falla explícitamente si el contacto demo ya existe (evita duplicados en reejecuciones;
 * la contraseña de una ejecución anterior queda documentada en docs/credenciales_dev.txt). */
async function createDemoClientUser(page) {
  const EMAIL = 'contacto.demo@clienteexterno.com';
  const USERNAME = 'contacto.demo';

  await goto(page, '/client-contacts');
  const already = await page.evaluate((email) => document.body.innerText.includes(email), EMAIL);
  if (already) {
    throw new Error(`el contacto demo (${EMAIL}) ya existe; usa la contraseña ya documentada en docs/credenciales_dev.txt`);
  }

  await clickExactText(page, 'Nuevo Usuario/cliente', { tag: 'button, span' });
  await page.waitForSelector('.ant-modal', { timeout: 10000 });
  await page.type('input[placeholder="contacto@clienteexterno.com"]', EMAIL, { delay: 15 });
  await page.type('input[placeholder="nombre.apellido"]', USERNAME, { delay: 15 });

  await page.click('.ant-modal .ant-select-selector');
  await page.waitForSelector('.ant-select-dropdown:not(.ant-select-dropdown-hidden)', { timeout: 5000 });
  await selectAntOption(page, 'Aris Mining');
  await page.keyboard.press('Escape');
  await new Promise(r => setTimeout(r, 200));

  await clickExactText(page, 'Crear', { scope: '.ant-modal', tag: 'button, span' });
  await page.waitForSelector('text/Contraseña provisional generada', { timeout: 10000 });
  const password = await page.evaluate(() => {
    const codeEl = document.querySelector('.ant-modal code');
    return codeEl ? codeEl.textContent.trim() : null;
  });
  if (!password) throw new Error('no se pudo leer la contraseña provisional en el modal');

  await clickExactText(page, 'Ya la copié, cerrar', { scope: '.ant-modal', tag: 'button, span' });
  return { email: EMAIL, username: USERNAME, password };
}

async function main() {
  console.log(`SyWork Tickets — captura de manual (${BASE_URL})\n`);
  const browser = await puppeteer.launch({ headless: true, defaultViewport: VIEWPORT });
  const page = await browser.newPage();

  await step('Login', () => login(page));

  const simpleRoutes = [
    ['/tickets', '01-tickets'],
    ['/kanban', '02-kanban'],
    ['/my-tasks', '03-mis-tareas'],
    ['/assignment-panel', '04-panel-asignacion'],
    ['/registro-tiempos', '12-registro-tiempos'],
    ['/reporte-tiempos', '13-reporte-tiempos'],
    ['/rrhh/franjas-horarias', '11-franjas-horarias'],
    ['/clients', '14-clientes'],
    ['/projects', '15-proyectos'],
    ['/team', '17-equipo'],
    ['/skills', '18-skills'],
    ['/roles', '19-roles-permisos'],
    ['/client-contacts', '20-usuarios-cliente'],
    ['/sla-rules', '21-sla'],
    ['/catalogs', '22-catalogos'],
    ['/me', '23-mi-perfil'],
  ];

  for (const [route, name] of simpleRoutes) {
    await step(`${name} (${route})`, async () => {
      await goto(page, route);
      await shot(page, name, { fullPage: true });
    });
  }

  await step('10-permisos (/absence-requests, pestaña Mis solicitudes)', async () => {
    await goto(page, '/absence-requests');
    await shot(page, '10-permisos', { fullPage: true });
  });

  await step('08-calendario-cliente (/calendar)', async () => {
    await goto(page, '/calendar');
    await shot(page, '08-calendario-cliente');
  });

  await step('09-calendario-equipo (/calendar, pestaña Equipo)', async () => {
    await clickExactText(page, 'Equipo', { tag: '[role="tab"]' });
    await new Promise(r => setTimeout(r, 300));
    await clickExactText(page, 'Seleccionar todo', { tag: 'button' });
    await new Promise(r => setTimeout(r, 600));
    await shot(page, '09-calendario-equipo', { fullPage: true });
  });

  await step('16-proyecto-personal (Proyectos › Aris Mining › Personal)', async () => {
    await goto(page, '/projects');
    await clickRowAction(page, 'Aris Mining', 1);
    await new Promise(r => setTimeout(r, 500));
    await shot(page, '16-proyecto-personal');
  });

  await step('06-detalle-ticket + 07-reasignar-modal (Kanban → TK-000004)', async () => {
    await goto(page, '/kanban');
    await page.waitForSelector('text/Tablero Kanban', { timeout: 15000 });

    let found = false;
    for (let attempt = 0; attempt < 8 && !found; attempt++) {
      found = await page.evaluate(() => {
        // Las tarjetas del Kanban son divs role="button" (drag-and-drop @hello-pangea/dnd), no <button>.
        const candidates = Array.from(document.querySelectorAll('button, [role="button"]'));
        const el = candidates.find(b => b.textContent.includes('TK-000004'));
        if (!el) return false;
        el.scrollIntoView({ block: 'center' });
        el.click();
        return true;
      });
      if (!found) await new Promise(r => setTimeout(r, 500));
    }
    if (!found) throw new Error('tarjeta TK-000004 no encontrada en el Kanban');
    await page.waitForSelector('text/Historial de estados', { timeout: 10000 });
    await new Promise(r => setTimeout(r, 300));
    await shot(page, '06-detalle-ticket', { fullPage: true });

    // Recorte de la tarjeta SLA sola, para la sección 2.3 (regla de SLA)
    const slaBox = await page.evaluate(() => {
      const titles = Array.from(document.querySelectorAll('.ant-card-head-title'));
      const titleEl = titles.find(t => t.textContent.trim() === 'SLA');
      const card = titleEl && titleEl.closest('.ant-card');
      if (!card) return null;
      const r = card.getBoundingClientRect();
      return { x: r.x, y: r.y, width: r.width, height: r.height };
    });
    if (slaBox && slaBox.width > 0) {
      await page.screenshot({
        path: path.join(OUT_DIR, '05b-sla-card.png'),
        clip: { x: Math.max(0, slaBox.x - 8), y: Math.max(0, slaBox.y - 8), width: slaBox.width + 16, height: slaBox.height + 16 },
      });
      console.log('  guardado: 05b-sla-card.png');
    }

    const swapClicked = await page.evaluate(() => {
      const icon = document.querySelector('span[aria-label="swap"]');
      const btn = icon && icon.closest('button');
      if (!btn) return false;
      btn.click();
      return true;
    });
    if (!swapClicked) throw new Error('ícono Reasignar (swap) no encontrado');
    await page.waitForSelector('text/Reasignar ticket', { timeout: 10000 });
    await new Promise(r => setTimeout(r, 400));
    await shot(page, '07-reasignar-modal');

    // Cerrar sin guardar: botón "Cancelar" exacto dentro del modal
    await clickExactText(page, 'Cancelar', { scope: '.ant-modal', tag: 'button, span' });
  });

  let demoClientUser = null;
  await step('Alta Usuario/cliente demo (Maestros > Usuarios/cliente)', async () => {
    demoClientUser = await createDemoClientUser(page);
    const passB64 = Buffer.from(demoClientUser.password, 'utf8').toString('base64');
    const credFile = path.resolve(__dirname, '..', '..', 'docs', 'credenciales_dev.txt');
    const sep = fs.readFileSync(credFile, 'utf8').endsWith('\n') ? '' : '\n';
    fs.appendFileSync(
      credFile,
      `${sep}${demoClientUser.username} / ${demoClientUser.email} | Usuario/cliente | ${passB64}\n`,
    );
    console.log(`  usuario creado: ${demoClientUser.username} (contraseña guardada en docs/credenciales_dev.txt)`);
  });

  await step('24-vista-usuario-cliente (login como Usuario/cliente demo)', async () => {
    if (!demoClientUser) throw new Error('no hay usuario demo disponible (el paso de alta falló)');
    await loginAs(page, demoClientUser.username, demoClientUser.password);
    await shot(page, '24-vista-usuario-cliente', { fullPage: true });
  });

  await browser.close();

  console.log('\nResumen:');
  for (const r of results) {
    console.log(`  ${r.ok ? '✔' : '✘'} ${r.label}${r.ok ? '' : ' — ' + r.error}`);
  }
  const failed = results.filter(r => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} capturas OK. Guardadas en ${OUT_DIR}`);
  if (failed > 0) process.exitCode = 1;
}

main().catch(err => {
  console.error('Error fatal:', err);
  process.exit(1);
});
