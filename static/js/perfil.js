const i18n = {
    pt: {
        "voltar": "← Voltar para Guildas",
        "ataques-recentes": "Ataques recentes", "comps-fav": "Composições favoritas",
        "time-mais-enfrentado": "Time mais enfrentado", "comps-dificeis": "Composições mais difíceis",
        "def-melhor": "Defesa com melhor desempenho", "lider": "Líder", "vice": "Vice-Líder",
        "nenhum-ataque": "Nenhum ataque recente encontrado.", "nenhuma-defesa": "Nenhum registro de defesa encontrado.",
        "nenhum-dado": "Nenhum dado encontrado.", "vitoria": "VITÓRIA", "derrota": "DERROTA",
        "detalhes": "Detalhes", "ocultar": "Ocultar", "time-atacante": "Time Atacante", "time-defensor": "Time Defensor",
        "total-defesas": "Total de Defesas:", "winrate-def": "Winrate da Defesa", "ataques-sofridos": "Ataques que esta defesa sofreu:",
        "atacante": "Atacante:", "def-venceu": "DEFESA VENCEU", "def-perdeu": "DEFESA PERDEU",
        "usos": "Usos", "vitorias": "Vitórias", "enfrentado": "Enfrentado", "winrate-contra": "Winrate contra",
        "lutas": "lutas", "times-inimigos": "Times Inimigos mais enfrentados",
        "btn-coffee": "Pagar um café"
    },
    en: {
        "voltar": "← Back to Guilds",
        "ataques-recentes": "Recent Attacks", "comps-fav": "Favorite Compositions",
        "time-mais-enfrentado": "Most Faced Team", "comps-dificeis": "Toughest Compositions",
        "def-melhor": "Best Performing Defense", "lider": "Leader", "vice": "Co-Leader",
        "nenhum-ataque": "No recent attacks found.", "nenhuma-defesa": "No defense records found.",
        "nenhum-dado": "No data found.", "vitoria": "VICTORY", "derrota": "DEFEAT",
        "detalhes": "Details", "ocultar": "Hide", "time-atacante": "Attacking Team", "time-defensor": "Defending Team",
        "total-defesas": "Total Defenses:", "winrate-def": "Defense Winrate", "ataques-sofridos": "Attacks suffered by this defense:",
        "atacante": "Attacker:", "def-venceu": "DEFENSE WON", "def-perdeu": "DEFENSE LOST",
        "usos": "Uses", "vitorias": "Wins", "enfrentado": "Faced", "winrate-contra": "Winrate against",
        "lutas": "matches", "times-inimigos": "Most Faced Enemy Teams",
        "btn-coffee": "Buy me a coffee"
    }
};

let currentLang = localStorage.getItem('lang') || 'pt';
function nomeImagemAsset(valor) {
    const nome = String(valor ?? '');
    const normalizado = ['?', 'nocard', 'noncard'].includes(nome.toLowerCase()) ? 'noncard' : nome;
    return encodeURIComponent(normalizado);
}

function aliasesImagemAsset(pasta, nome) {
    const aliases = {
        PersonagensHeadIcon: { HizukiMari: 'Hizuki Mari', MizukiMakoto: 'Mizuki Makoto' },
        PersonagensFullBody: { HizukiMari: 'Hizuki Mari' }
    };
    return aliases[pasta]?.[nome] || null;
}

function urlsImagemAsset(pasta, valor, incluirHeadFallback = false) {
    const nomeNormalizado = ['?', 'nocard', 'noncard'].includes(String(valor ?? '').toLowerCase()) ? 'noncard' : String(valor ?? '');
    const alias = aliasesImagemAsset(pasta, nomeNormalizado);
    const nomes = [nomeNormalizado, alias].filter(Boolean);

    const webp = nomes.map(nome => `/static/img/${pasta}/${encodeURIComponent(nome)}.webp`);
    const legado = nomes.flatMap(nome => {
        const base = `/static/img/${pasta}/${encodeURIComponent(nome)}`;
        if (nomeNormalizado.toLowerCase() === 'noncard' && (pasta === 'Pets' || pasta === 'Cards')) {
            return [`${base}.jpg`, `${base}.png`];
        }
        return [`${base}.png`];
    });

    // Em instalação antiga (somente PNG/JPG), o alias legado conhecido vem primeiro.
    if (window.ETHERIA_PREFER_WEBP === false && alias) {
        const aliasEncoded = encodeURIComponent(alias);
        const aliasLegacy = nomeNormalizado.toLowerCase() === 'noncard' && (pasta === 'Pets' || pasta === 'Cards')
            ? [`/static/img/${pasta}/${aliasEncoded}.jpg`, `/static/img/${pasta}/${aliasEncoded}.png`]
            : [`/static/img/${pasta}/${aliasEncoded}.png`];
        const restoLegado = legado.filter(url => !aliasLegacy.includes(url));
        legado.splice(0, legado.length, ...aliasLegacy, ...restoLegado);
    }

    const urls = window.ETHERIA_PREFER_WEBP === false ? [...legado, ...webp] : [...webp, ...legado];

    if (incluirHeadFallback && pasta === 'PersonagensFullBody') {
        const headUrls = urlsImagemAsset('PersonagensHeadIcon', nomeNormalizado, false);
        urls.push(...headUrls.filter(url => !urls.includes(url)));
    }
    return [...new Set(urls)];
}

function atributosImagemAsset(pasta, valor, incluirHeadFallback = false) {
    const urls = urlsImagemAsset(pasta, valor, incluirHeadFallback);
    return `src="${urls[0]}" data-fallbacks="${urls.slice(1).join('|')}" onerror="usarProximoFallbackImagem(this)"`;
}

function usarProximoFallbackImagem(img) {
    const fila = String(img.dataset.fallbacks || '').split('|').filter(Boolean);
    const proxima = fila.shift();
    img.dataset.fallbacks = fila.join('|');
    if (proxima) {
        img.src = proxima;
    } else {
        img.onerror = null;
    }
}
function t(key) { return i18n[currentLang][key] || key; }

function toggleLanguage() {
    currentLang = currentLang === 'pt' ? 'en' : 'pt';
    localStorage.setItem('lang', currentLang);
    location.reload(); 
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-i18n]").forEach(el => {
        el.innerHTML = t(el.getAttribute("data-i18n"));
    });
    document.getElementById('btn-lang').innerHTML = currentLang === 'pt' ? '🇺🇸 EN' : '🇧🇷 PT-BR';
});

// -------------------------

const pathArray = window.location.pathname.split('/');
const idMembro = pathArray[pathArray.length - 1];
let nomeJogadorAtual = ""; let historicoBatalhas = [];

fetch(`/api/perfil/${idMembro}`)
    .then(response => response.json())
    .then(dados => {
        nomeJogadorAtual = dados.nickname;
        const iconeJogador = document.getElementById('icone-jogador');
        const avatarNome = dados.icone.split('/').pop().replace(/\.(webp|png|jpg)$/i, '');
        const avatarUrls = urlsImagemAsset('PersonagensHeadIcon', decodeURIComponent(avatarNome));
        iconeJogador.dataset.fallbacks = avatarUrls.slice(1).join('|');
        iconeJogador.onerror = function() { usarProximoFallbackImagem(this); };
        iconeJogador.src = avatarUrls[0];
        document.getElementById('nick-jogador').firstChild.textContent = dados.nickname + " ";
        document.getElementById('guilda-jogador').innerText = dados.guilda;
        document.getElementById('winrate-jogador').innerText = dados.winrate_geral;

        const iconeCargo = document.getElementById('icone-cargo');
        const tagCargo = document.getElementById('tag-cargo');
        
        if (dados.cargo === 'lider') {
            iconeCargo.innerHTML = '👑'; iconeCargo.className = 'coroa-lider'; tagCargo.style.display = 'flex'; tagCargo.innerHTML = '👑';
        } else if (dados.cargo === 'vice') {
            iconeCargo.innerHTML = '👑'; iconeCargo.className = 'coroa-vice'; tagCargo.style.display = 'flex'; tagCargo.innerHTML = '🥈';
        }
        return fetch(`/api/batalhas/${nomeJogadorAtual}`);
    })
    .then(response => response.json())
    .then(batalhas => {
        historicoBatalhas = batalhas;
        document.querySelector('.tab-btn.active').click(); 
    });

function gerarSlotHeroi(nomeHeroi, nomePet, nomeCarta) {
    return `
        <div class="hero-build-slot">
            <div class="hero-main-row"><img ${atributosImagemAsset('PersonagensHeadIcon', nomeHeroi)} class="avatar-hero" loading="lazy" decoding="async"></div>
            <div class="hero-sub-row">
                <img ${atributosImagemAsset('Pets', nomePet)} class="avatar-pet" loading="lazy" decoding="async">
                <img ${atributosImagemAsset('Cards', nomeCarta)} class="avatar-card" loading="lazy" decoding="async">
            </div>
        </div>`;
}

function gerarTimeHTML(composicaoArray) {
    let html = '<div class="team-group">';
    composicaoArray.forEach(slot => { html += gerarSlotHeroi(slot.heroi, slot.pet, slot.carta); });
    html += '</div>'; return html;
}

function gerarGridFullBody(composicaoArray) {
    let html = '<div class="drawer-grid">';
    composicaoArray.forEach(slot => {
        html += `
            <div class="drawer-heroi-card">
                <img ${atributosImagemAsset('PersonagensFullBody', slot.heroi, true)} class="drawer-fullbody" loading="lazy" decoding="async">
                <div style="font-weight: 600; font-size: 13px;">${slot.heroi}</div>
                <div class="drawer-sub-items">
                    <div class="drawer-sub-item"><img ${atributosImagemAsset('Pets', slot.pet)} loading="lazy" decoding="async"> ${slot.pet}</div>
                    <div class="drawer-sub-item"><img ${atributosImagemAsset('Cards', slot.carta)} loading="lazy" decoding="async"> ${slot.carta}</div>
                </div>
            </div>`;
    });
    html += '</div>'; return html;
}

function renderizarAtaquesRecentes() {
    const ataques = historicoBatalhas.filter(b => b.atacante.nome === nomeJogadorAtual).reverse();
    if (ataques.length === 0) return `<p style="text-align: center; color: var(--text-secondary); margin-top: 40px;">${t('nenhum-ataque')}</p>`;

    let html = '';
    ataques.forEach((batalha, index) => {
        const meuTime = batalha.atacante; const inimigoTime = batalha.defensor;
        const isWin = batalha.resultado.toLowerCase().includes('vitória');

        html += `
        <div class="comp-card-wrapper">
            <div class="comp-card">
                ${gerarTimeHTML(meuTime.composicao)}
                <div class="vs-container">
                    <div class="vs-names"><span style="color: var(--text-primary);">${meuTime.nome}</span> <span style="color: var(--text-secondary); font-weight: normal; margin: 0 4px;">x</span> <span style="color: var(--loss);">${inimigoTime.nome}</span></div>
                    <div class="vs-badge">VS</div>
                </div>
                ${gerarTimeHTML(inimigoTime.composicao)}
                <div class="right-action-group">
                    <div class="comp-stats">
                        <div class="${isWin ? 'result-win' : 'result-loss'}">${isWin ? t('vitoria') : t('derrota')}</div>
                        <div class="stat-label">${batalha.data}</div>
                    </div>
                    <button class="btn-details" onclick="toggleDetalhes('atk-${index}', this)">${t('detalhes')}</button>
                </div>
            </div>
            <div class="comp-drawer" id="drawer-atk-${index}">
                <div class="drawer-section">
                    <h4>${t('time-atacante')}: ${batalha.atacante.nome}</h4>
                    ${gerarGridFullBody(batalha.atacante.composicao)}
                </div>
                <div class="drawer-section" style="margin-top: 20px;">
                    <h4>${t('time-defensor')}: ${batalha.defensor.nome}</h4>
                    ${gerarGridFullBody(batalha.defensor.composicao)}
                </div>
            </div>
        </div>`;
    });
    return html;
}

function renderizarDefesas() {
    const defesasDoJogador = historicoBatalhas.filter(b => b.defensor.nome === nomeJogadorAtual);
    if (defesasDoJogador.length === 0) return `<p style="text-align: center; color: var(--text-secondary); margin-top: 40px;">${t('nenhuma-defesa')}</p>`;

    const mapaDefesas = {};
    defesasDoJogador.forEach(batalha => {
        const defComp = batalha.defensor.composicao;
        const assinatura = defComp.map(s => `${s.heroi}-${s.carta}-${s.pet}`).sort().join('|');
        
        if (!mapaDefesas[assinatura]) { mapaDefesas[assinatura] = { composicao: defComp, total: 0, vitorias: 0, ataquesSofridos: [] }; }
        mapaDefesas[assinatura].total++;
        const defesaVenceu = !batalha.resultado.toLowerCase().includes('vitória');
        if (defesaVenceu) mapaDefesas[assinatura].vitorias++;
        mapaDefesas[assinatura].ataquesSofridos.push({ atacanteNome: batalha.atacante.nome, atacanteComposicao: batalha.atacante.composicao, venceuDefesa: defesaVenceu, data: batalha.data });
    });

    const listaDefesas = Object.values(mapaDefesas).map(def => { def.winrate = (def.vitorias / def.total) * 100; return def; }).sort((a, b) => b.winrate - a.winrate);

    let html = '';
    listaDefesas.forEach((def, index) => {
        html += `
        <div class="comp-card-wrapper">
            <div class="comp-card">
                ${gerarTimeHTML(def.composicao)}
                <div class="vs-container" style="width: auto;">
                    <div class="vs-names" style="color: var(--text-secondary); font-size: 13px;">
                        ${t('total-defesas')} <span style="color: var(--text-primary); font-weight: bold;">${def.total}</span>
                    </div>
                </div>
                <div class="right-action-group">
                    <div class="comp-stats">
                        <div class="stat-value" style="color: var(--win);">${def.winrate.toFixed(1)}%</div>
                        <div class="stat-label">${t('winrate-def')}</div>
                    </div>
                    <button class="btn-details" onclick="toggleDetalhes('def-${index}', this)">${t('detalhes')}</button>
                </div>
            </div>
            <div class="comp-drawer" id="drawer-def-${index}">
                <div class="drawer-section">
                    <h4>${t('ataques-sofridos')}</h4>
                    <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">`;

        def.ataquesSofridos.reverse().forEach(atk => {
            html += `
                        <div style="background-color: var(--bg-base); border: 1px solid var(--border); border-radius: 8px; padding: 12px; display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <span style="font-size: 13px; font-weight: bold; color: var(--text-primary); width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${t('atacante')} ${atk.atacanteNome}</span>
                                ${gerarTimeHTML(atk.atacanteComposicao)}
                            </div>
                            <div class="right-action-group">
                                <div class="${atk.venceuDefesa ? 'result-win' : 'result-loss'}">${atk.venceuDefesa ? t('def-venceu') : t('def-perdeu')}</div>
                                <div class="stat-label">${atk.data}</div>
                            </div>
                        </div>`;
        });
        html += `</div></div></div></div>`;
    });
    return html;
}

// Um único agrupador atende aos três rankings do perfil.
function rankingComposicoes(lado, totalKey, winsKey, ordenacao) {
    const ataques = historicoBatalhas.filter(b => b.atacante.nome === nomeJogadorAtual);
    if (!ataques.length) return null;
    const mapa = {};
    ataques.forEach(b => {
        const comp = b[lado].composicao;
        const sig = comp.map(s => `${s.heroi}-${s.carta}-${s.pet}`).sort().join('|');
        const item = mapa[sig] ||= { composicao: comp, [totalKey]: 0, [winsKey]: 0 };
        item[totalKey]++;
        if (b.resultado.toLowerCase().includes('vitória')) item[winsKey]++;
    });
    return Object.values(mapa)
        .map(item => ({ ...item, winrate: item[winsKey] / item[totalKey] * 100 }))
        .sort(ordenacao);
}

function montarRanking(titulo, itens, estatistica) {
    if (!itens) return `<p style="text-align: center; color: var(--text-secondary); margin-top: 40px;">${t('nenhum-dado')}</p>`;
    return `<h3 style="margin: 0 0 15px 5px; color: var(--text-primary); font-weight: 500;">${t(titulo)}</h3>` +
        itens.map(item => `
        <div class="comp-card-wrapper" style="margin-bottom: 12px;">
            <div class="comp-card">
                ${gerarTimeHTML(item.composicao)}
                <div class="right-action-group">
                    <div class="comp-stats">
                        <div class="stat-value"${estatistica.cor ? ` style="color: var(--${estatistica.cor});"` : ''}>${estatistica.valor(item)}</div>
                        <div class="stat-label">${estatistica.legenda(item)}</div>
                    </div>
                </div>
            </div>
        </div>`).join('');
}

function renderizarComposicoesFavoritas() {
    return montarRanking('comps-fav', rankingComposicoes('atacante', 'usos', 'vitorias',
        (a, b) => b.usos - a.usos), {
        cor: 'win', valor: i => `${i.winrate.toFixed(1)}%`,
        legenda: i => `${i.usos} ${t('usos')} (${i.vitorias} ${t('vitorias')})`
    });
}

function renderizarTimeMaisEnfrentado() {
    return montarRanking('times-inimigos', rankingComposicoes('defensor', 'enfrentamentos', 'vitoriasContra',
        (a, b) => b.enfrentamentos - a.enfrentamentos), {
        valor: i => `${i.enfrentamentos}x`,
        legenda: i => `${t('enfrentado')} (${i.winrate.toFixed(1)}% ${t('winrate-contra')})`
    });
}

function renderizarComposicoesMaisDificeis() {
    return montarRanking('comps-dificeis', rankingComposicoes('defensor', 'total', 'vitorias',
        (a, b) => a.winrate - b.winrate), {
        cor: 'loss', valor: i => `${i.winrate.toFixed(1)}%`,
        legenda: i => `${t('winrate-contra')} (${i.total} ${t('lutas')})`
    });
}

function toggleDetalhes(idDrawer, botao) {
    const drawer = document.getElementById(`drawer-${idDrawer}`);
    if (drawer.style.display === 'block') { drawer.style.display = 'none'; botao.innerText = t('detalhes');
    } else { drawer.style.display = 'block'; botao.innerText = t('ocultar'); }
}

function mudarAba(nomeAba, elementoBotao) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    elementoBotao.classList.add('active');

    const area = document.getElementById('area-conteudo');
    if (nomeAba === 'ataques-recentes') area.innerHTML = renderizarAtaquesRecentes();
    else if (nomeAba === 'def-melhor') area.innerHTML = renderizarDefesas();
    else if (nomeAba === 'comps-fav') area.innerHTML = renderizarComposicoesFavoritas();
    else if (nomeAba === 'time-mais-enfrentado') area.innerHTML = renderizarTimeMaisEnfrentado();
    else if (nomeAba === 'comps-dificeis') area.innerHTML = renderizarComposicoesMaisDificeis();
}
