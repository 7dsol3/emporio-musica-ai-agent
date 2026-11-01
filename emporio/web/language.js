"use strict";
window.EmporioLanguage = (() => {
  let locale = "en";
  try { locale = localStorage.getItem("emporio-language") === "pt" ? "pt" : "en"; } catch (_) { /* Storage is optional. */ }
  const terms = {
    ready: ["Your music desk is ready", "Seu atendimento está pronto"], connecting: ["Connecting to your music desk…", "Conectando ao atendimento…"], offline: ["Connection unavailable", "Conexão indisponível"],
    verify: ["Verify order", "Verificar pedido"], verified: ["Order verified ✓", "Pedido verificado ✓"], customer: ["YOU", "VOCÊ"], assistant: ["EMPÓRIO ASSISTANT", "ASSISTENTE EMPÓRIO"],
    checking: ["Checking the store information…", "Consultando as informações da loja…"], checked: ["How this answer was checked", "Como a resposta foi conferida"],
    noFacts: ["No store facts were needed for this reply.", "Esta resposta não precisou consultar dados da loja."], refs: ["References will appear here when we consult store information.", "As referências aparecerão aqui após uma consulta aos dados da loja."],
    local: ["KONAET · LOCAL PLANNER", "KONAET · PLANEJADOR LOCAL"], fallback: ["KONAET · LOCAL FALLBACK", "KONAET · RESPOSTA LOCAL DE RESERVA"], model: ["MODEL PLANNER · CHECKED TOOLS", "PLANEJADOR DE LINGUAGEM · DADOS CONFERIDOS"], configured: ["CONFIGURED MODEL PLANNER", "MODELO DE LINGUAGEM CONFIGURADO"],
    catalogLoading: ["Checking the catalog…", "Consultando o catálogo…"], noProducts: ["No matching instruments in the supplied catalog. Try a different brand or category.", "Nenhum instrumento corresponde à busca. Tente outra marca ou categoria."],
    inStock: ["● In stock", "● Em estoque"], off: ["% off", "% de desconto"], unavailable: ["out of stock", "sem estoque"], askProduct: ["Ask about this instrument ↗", "Perguntar sobre este instrumento ↗"],
    readManual: ["Read the original manual · p. ", "Ler o manual original · p. "], verifiedToast: ["Order verified for this session.", "Pedido verificado nesta sessão."], verifyFailed: ["Could not verify those details. Please check the order number and purchase email.", "Não foi possível verificar. Confira o número do pedido e o e-mail da compra."],
    cleared: ["Conversation and verification cleared.", "Conversa e verificação apagadas."], noExport: ["Start a conversation to export it.", "Inicie uma conversa para exportar."], genericError: ["Please check your input and try again.", "Confira os dados e tente novamente."],
    humanReturns: ["Human team returns ", "Equipe retorna "], cityTime: [" · Campo Grande", " · Campo Grande"],
  };
  const originals = new Map();
  function text(key) { return (terms[key] || [key, key])[locale === "pt" ? 1 : 0]; }
  function html(selector, pt) {
    const element = document.querySelector(selector); if (!element) return;
    if (!originals.has(selector)) originals.set(selector, element.innerHTML);
    element.innerHTML = locale === "pt" ? pt : originals.get(selector);
  }
  function apply() {
    document.documentElement.lang = locale === "pt" ? "pt-BR" : "en";
    document.querySelector("#language-select").value = locale;
    const changes = {
      ".new-chat": "<span>＋</span> Nova conversa", ".nav-label": "SEU BALCÃO MUSICAL",
      '[data-view="chat"]': '<span>◈</span> Assistente da loja <span class="nav-dot"></span>',
      '[data-view="catalog"]': "<span>♫</span> Explorar instrumentos", '[data-view="policies"]': "<span>▤</span> Informações da loja",
      ".sidebar-note p": "Uma boa orientação.<br>Música de sobra.", ".sidebar-note small": "Instrumentos para sua primeira nota<br>e tudo o que vem depois.",
      "#about-button": "Sobre esta demonstração <span>↗</span>", "#welcome .eyebrow": '<span class="small-rule"></span> SUA MÚSICA COMEÇA AQUI',
      ".intro": "Um novo instrumento. Uma dúvida rápida. Uma ajuda com seu pedido. <br>Vamos simplificar.",
      ".composer-foot>span": '<span class="mini-dot"></span> Respostas baseadas nos dados da loja', "#export-button": "Exportar conversa ↓",
      "#catalog-view .eyebrow": "A SALA DE INSTRUMENTOS", "#catalog-view h2": "Um som para <em>cada história.</em>",
      "#catalog-view>.muted": "Explore o catálogo fornecido. A equipe confirma a disponibilidade antes da compra.", "#catalog-form .primary": "Buscar",
      "#policies-view .eyebrow": "BOM SABER", "#policies-view h2": "Respostas claras.<br><em>Sem adivinhação.</em>", "#policies-view>.muted": "Um guia do manual fornecido, com referências às páginas originais.",
      ".evidence-panel>.desk-label": "A LOJA EM RESUMO <span>↗</span>", ".evidence-panel h3": "Instrumentos de verdade.<br>Respostas úteis.", ".panel-copy": "Uma loja especializada com um atendimento acolhedor, aqui em Campo Grande.",
      ".stat-row:nth-of-type(3)>span": "Instrumentos no catálogo", ".stat-row:nth-of-type(4)>span": "Páginas de políticas", ".protected": "Protegidos",
      ".stat-row:nth-of-type(5)>span": "Dados de pedidos", "#latest-sources .muted": "As referências aparecerão aqui quando consultarmos o catálogo ou o manual.",
      ".hours-card>div": '<span class="status-dot"></span> HORÁRIO DA EQUIPE', ".hours-card p": "Seg–Sex <strong>09:00–18:00</strong><br>Sábado <strong>09:00–13:00</strong>", ".hours-card small": "Campo Grande · UTC−04:00<br>Domingos e feriados: fechado",
      ".evidence-box>.desk-label": "FONTES MAIS RECENTES", ".snapshot-note": "Demonstração com os dados fornecidos. Não executa compras, reembolsos ou atualizações de transportadoras.",
      "#verify-form .eyebrow": "SEU PEDIDO, SUAS INFORMAÇÕES", "#verify-form h2": "Uma rápida <em>conferência.</em>", "#verify-form>.muted": "Confirme o número do pedido e o e-mail da compra. Esses dados ficam neste aplicativo local.",
      'label[for="order-id"]': "Número do pedido", 'label[for="purchase-email"]': "E-mail da compra", "#verify-form .primary": "Verificar com segurança", ".dialog-note": "Verificação de demonstração. Em produção, é necessário autenticar a conta ou usar um código de uso único.",
      "#about-dialog h2": "Evidências antes<br><em>das respostas.</em>", "#about-dialog p:nth-of-type(1)": "Este protótipo consulta as tabelas CSV e o manual da loja. O planejador local Konaet escolhe ferramentas restritas; preços e decisões de política são montados a partir de resultados conferidos.",
      "#about-dialog p:nth-of-type(2)": "Um modelo de linguagem opcional pode selecionar as mesmas ferramentas quando configurado. O planejador local também funciona sem um modelo externo.",
      "#about-dialog p:nth-of-type(3)": "Os pedidos exigem verificação da sessão. As conversas expiram após 24 horas; Nova conversa apaga a sessão atual. E-mails e telefones reconhecíveis são ocultados do histórico.",
      "#about-dialog p:nth-of-type(4)": "Políticas ambíguas exigem revisão humana. Esta demonstração não envia chamados, processa pagamentos nem autoriza reembolsos.", "#about-dialog .text-link": "Explorar a documentação da API ↗",
    };
    Object.entries(changes).forEach(([selector, value]) => html(selector, value));
    const heading = document.querySelector("#welcome h1");
    if (!originals.has("hero")) originals.set("hero", heading.innerHTML);
    const wave = heading.querySelector("svg").outerHTML;
    heading.innerHTML = locale === "pt" ? "Encontre seu<br>próximo <em>som.</em>" + wave : originals.get("hero");
    const prompts = [
      ["Encontre meu instrumento", "Violões de até R$ 1.000", "Quais violões estão disponíveis até R$ 1.000?"],
      ["Consulte um preço", "Vamos conferir um modelo específico", "Quanto custa o Takamine GD20?"],
      ["Devoluções mais claras", "Entenda os próximos passos", "Quero devolver minha compra online. O que preciso informar?"],
      ["Venha nos visitar", "Endereço e horário de atendimento", "Qual é o endereço e o horário da loja?"],
    ];
    document.querySelectorAll(".prompt").forEach((button, index) => {
      const key = "prompt" + index; if (!originals.has(key)) originals.set(key, { html: button.innerHTML, prompt: button.dataset.prompt });
      if (locale === "pt") { button.querySelector("strong").textContent = prompts[index][0]; button.querySelector("span:not(.prompt-icon)").textContent = prompts[index][1]; button.dataset.prompt = prompts[index][2]; }
      else { button.innerHTML = originals.get(key).html; button.dataset.prompt = originals.get(key).prompt; }
    });
    const placeholders = { "#message-input": ["Ask about an instrument, a policy, or your order…", "Pergunte sobre um instrumento, uma política ou seu pedido…"], "#catalog-query": ["Search a model or brand…", "Busque um modelo ou marca…"], "#order-id": ["e.g. 8", "ex.: 8"], "#purchase-email": ["you@example.com", "voce@exemplo.com"] };
    Object.entries(placeholders).forEach(([selector, values]) => { document.querySelector(selector).placeholder = values[locale === "pt" ? 1 : 0]; });
    const categories = ["Todos os instrumentos", "Violões", "Guitarras", "Baixos", "Baterias e percussão", "Teclados e pianos", "Sopros de madeira", "Sopros de metal", "Cordas orquestrais", "Ukuleles"];
    document.querySelectorAll("#catalog-category option").forEach((option, index) => { const key = "category" + index; if (!originals.has(key)) originals.set(key, option.textContent); option.textContent = locale === "pt" ? categories[index] : originals.get(key); });
    document.querySelectorAll(".message").forEach(m => { m.querySelector(".role span").textContent = text(m.classList.contains("user") ? "customer" : "assistant"); });
  }
  function set(value) { locale = value === "pt" ? "pt" : "en"; try { localStorage.setItem("emporio-language", locale); } catch (_) {} apply(); }
  return { text, apply, set, get locale() { return locale; } };
})();
