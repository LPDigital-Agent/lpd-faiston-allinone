/**
 * Blog Mock Data - Faiston One
 *
 * Articles imported from faiston.com/blogs/ and reformatted
 * for the internal portal. Content based on original posts.
 */

import { BlogPost } from "@/lib/blog/types";

/**
 * All blog posts sorted by publication date (newest first).
 * Featured article is marked for hero display.
 */
export const BLOG_POSTS: BlogPost[] = [
  {
    id: "1",
    slug: "como-maximizar-roi-outsourcing-ti",
    title: "Como Maximizar o ROI com Outsourcing de TI",
    excerpt:
      "Descubra estrategias comprovadas para aumentar o retorno sobre investimento ao terceirizar servicos de tecnologia da informacao. Aprenda a escolher o parceiro certo e otimizar custos.",
    content: `
# Como Maximizar o ROI com Outsourcing de TI

O outsourcing de TI tem se tornado uma estrategia cada vez mais adotada por empresas que buscam otimizar custos e focar em suas competencias principais. Neste artigo, exploramos como maximizar o retorno sobre investimento (ROI) ao terceirizar servicos de tecnologia.

## Por que Outsourcing de TI?

A terceirizacao de servicos de TI permite que as empresas:
- **Reduzam custos operacionais** em ate 40%
- **Acessem talentos especializados** sem custos de contratacao
- **Escalem recursos** conforme a demanda
- **Foquem no core business** enquanto especialistas cuidam da tecnologia

## Estrategias para Maximizar o ROI

### 1. Escolha o Parceiro Certo
Avalie a experiencia, certificacoes e cases de sucesso do fornecedor. Um parceiro alinhado com seus objetivos e fundamental para o sucesso.

### 2. Defina SLAs Claros
Estabeleca acordos de nivel de servico mensuráveis e relevantes para o negocio. Isso garante responsabilidade e transparencia.

### 3. Monitore e Otimize Continuamente
Implemente dashboards de acompanhamento e revisoes periodicas para identificar oportunidades de melhoria.

## Conclusao

O outsourcing de TI, quando bem planejado e executado, pode ser um diferencial competitivo significativo. A chave esta em escolher parceiros de confianca e manter uma gestao ativa do relacionamento.
    `,
    category: "blog-news",
    categoryLabel: "Blog & News",
    publishedAt: "2025-08-15",
    readTime: 6,
    featured: true,
    externalUrl: "https://faiston.com/blogs/como-maximizar-roi-outsourcing-ti",
    tags: ["outsourcing", "ROI", "gestao de TI", "terceirizacao"],
  },
  {
    id: "2",
    slug: "servicos-gerenciados-infraestrutura",
    title: "Servicos Gerenciados de Infraestrutura: O Guia Completo",
    excerpt:
      "Entenda como os servicos gerenciados de infraestrutura podem transformar a operacao de TI da sua empresa, reduzindo custos e aumentando a disponibilidade.",
    content: `
# Servicos Gerenciados de Infraestrutura: O Guia Completo

Os servicos gerenciados de infraestrutura representam uma evolucao na forma como as empresas administram seus recursos de TI. Neste guia, exploramos os principais aspectos dessa modalidade de servico.

## O que sao Servicos Gerenciados?

Servicos gerenciados de infraestrutura envolvem a terceirizacao da gestao, monitoramento e manutencao de recursos de TI para um provedor especializado. Isso inclui:

- Servidores e storage
- Redes e conectividade
- Seguranca de perimetro
- Backup e recuperacao

## Beneficios Principais

### Reducao de Custos
Converta custos fixos em variaveis e elimine investimentos em infraestrutura proprio.

### Maior Disponibilidade
Monitoramento 24x7 e resposta rapida a incidentes garantem uptime superior.

### Acesso a Especialistas
Equipes certificadas com conhecimento atualizado nas melhores praticas do mercado.

## Como Escolher um Provedor

1. **Verifique certificacoes** (ISO 27001, SOC 2, etc.)
2. **Avalie a infraestrutura** do datacenter
3. **Analise os SLAs** oferecidos
4. **Solicite referencias** de clientes similares
    `,
    category: "blog-news",
    categoryLabel: "Blog & News",
    publishedAt: "2025-08-06",
    readTime: 5,
    featured: false,
    externalUrl: "https://faiston.com/blogs/servicos-gerenciados-infraestrutura",
    tags: ["infraestrutura", "servicos gerenciados", "datacenter"],
  },
  {
    id: "3",
    slug: "crescimento-ciberataques-agentes-ia",
    title: "O Crescimento de Ciberataques por Agentes de IA",
    excerpt:
      "Analise o cenario alarmante de ataques ciberneticos potencializados por inteligencia artificial e saiba como proteger sua organizacao.",
    content: `
# O Crescimento de Ciberataques por Agentes de IA

A inteligencia artificial esta revolucionando nao apenas os negocios, mas tambem o cenario de ameacas ciberneticas. Atacantes estao utilizando IA para criar ataques mais sofisticados e dificeis de detectar.

## O Novo Cenario de Ameacas

### Phishing Potencializado por IA
Agentes de IA podem gerar e-mails de phishing altamente personalizados, imitando perfeitamente o estilo de comunicacao de colegas ou executivos.

### Ataques Automatizados
Bots inteligentes podem identificar vulnerabilidades e explora-las em escala, 24 horas por dia.

### Deepfakes e Engenharia Social
Vozes e videos sinteticos estao sendo usados para fraudes e manipulacao.

## Estatisticas Preocupantes

- **300%** de aumento em ataques com IA em 2024
- **78%** das empresas reportam ataques mais sofisticados
- **US$ 10.5 trilhoes** em danos projetados ate 2025

## Como se Proteger

1. **Implemente Zero Trust** - Nunca confie, sempre verifique
2. **Use IA defensivamente** - Combata fogo com fogo
3. **Treine sua equipe** - O fator humano continua crucial
4. **Atualize sistemas** - Patches em dia reduzem superficie de ataque
    `,
    category: "seguranca",
    categoryLabel: "Seguranca",
    publishedAt: "2025-07-31",
    readTime: 7,
    featured: false,
    externalUrl: "https://faiston.com/blogs/crescimento-ciberataques-agentes-ia",
    tags: ["ciberseguranca", "IA", "ameacas", "phishing"],
  },
  {
    id: "4",
    slug: "ti-saude-tecnologia-futuro",
    title: "TI na Saude: Como a Tecnologia Esta Mudando o Futuro",
    excerpt:
      "Explore as inovacoes tecnologicas que estao transformando o setor de saude, desde telemedicina ate inteligencia artificial no diagnostico.",
    content: `
# TI na Saude: Como a Tecnologia Esta Mudando o Futuro

O setor de saude passa por uma transformacao digital sem precedentes. A tecnologia esta redefinindo como cuidamos da saude, desde o diagnostico ate o tratamento.

## Principais Inovacoes

### Telemedicina
A pandemia acelerou a adocao da telemedicina, que hoje e parte essencial do atendimento medico. Consultas remotas aumentaram 3.000% desde 2020.

### IA no Diagnostico
Algoritmos de machine learning conseguem detectar doencas em exames de imagem com precisao superior a especialistas humanos em alguns casos.

### Prontuario Eletronico
A digitalizacao de registros medicos melhora a continuidade do cuidado e reduz erros.

### IoT Medico
Dispositivos conectados monitoram pacientes em tempo real, permitindo intervencoes proativas.

## Desafios e Oportunidades

### Seguranca de Dados
Dados de saude sao extremamente sensiveis e exigem protecao robusta (LGPD, HIPAA).

### Interoperabilidade
Sistemas precisam se comunicar para entregar valor real aos pacientes.

### Capacitacao
Profissionais de saude precisam de treinamento para aproveitar as novas tecnologias.
    `,
    category: "infraestrutura",
    categoryLabel: "Infraestrutura",
    publishedAt: "2025-07-10",
    readTime: 6,
    featured: false,
    externalUrl: "https://faiston.com/blogs/ti-saude-tecnologia-futuro",
    tags: ["saude", "telemedicina", "inovacao", "IA"],
  },
  {
    id: "5",
    slug: "threat-intelligence-dados-decisoes",
    title: "Threat Intelligence: Transformando Dados em Decisoes",
    excerpt:
      "Aprenda como inteligencia de ameacas pode fortalecer sua postura de seguranca, antecipando ataques e protegendo ativos criticos.",
    content: `
# Threat Intelligence: Transformando Dados em Decisoes

Threat Intelligence e a coleta, analise e disseminacao de informacoes sobre ameacas ciberneticas. E fundamental para uma postura de seguranca proativa.

## Niveis de Threat Intelligence

### Tatico
Indicadores de comprometimento (IoCs) como IPs maliciosos, hashes de malware e URLs de phishing.

### Operacional
Informacoes sobre TTPs (Taticas, Tecnicas e Procedimentos) usados por atacantes.

### Estrategico
Visao de alto nivel sobre tendencias de ameacas e atores de ameaca relevantes para o negocio.

## Beneficios da Threat Intelligence

1. **Antecipacao** - Identifique ameacas antes que impactem o negocio
2. **Priorizacao** - Foque recursos nas ameacas mais relevantes
3. **Contexto** - Entenda o "porque" por tras dos ataques
4. **Colaboracao** - Compartilhe inteligencia com a comunidade

## Implementando um Programa de TI

- Defina requisitos de inteligencia
- Estabeleca fontes confiaveis
- Implemente plataforma de TI (TIP)
- Integre com ferramentas de seguranca (SIEM, SOAR)
- Mensure e melhore continuamente
    `,
    category: "seguranca",
    categoryLabel: "Seguranca",
    publishedAt: "2025-07-03",
    readTime: 8,
    featured: false,
    externalUrl: "https://faiston.com/blogs/threat-intelligence-dados-decisoes",
    tags: ["threat intelligence", "ciberseguranca", "SIEM", "SOC"],
  },
  {
    id: "6",
    slug: "gestao-vulnerabilidades-proativa",
    title: "Gestao de Vulnerabilidades: Abordagem Proativa",
    excerpt:
      "Descubra como implementar um programa eficaz de gestao de vulnerabilidades, priorizando riscos e protegendo sua infraestrutura.",
    content: `
# Gestao de Vulnerabilidades: Abordagem Proativa

A gestao de vulnerabilidades e um processo continuo de identificacao, avaliacao, tratamento e relatorio de vulnerabilidades de seguranca.

## O Ciclo de Gestao de Vulnerabilidades

### 1. Descoberta
Mapeie todos os ativos de TI, incluindo shadow IT. Voce nao pode proteger o que nao conhece.

### 2. Escaneamento
Realize varreduras regulares com ferramentas como Nessus, Qualys ou OpenVAS.

### 3. Analise
Avalie a criticidade de cada vulnerabilidade considerando CVSS e contexto de negocio.

### 4. Priorizacao
Foque primeiro nas vulnerabilidades com maior risco real, nao apenas maior score.

### 5. Remediacao
Aplique patches, configure controles compensatorios ou aceite o risco documentadamente.

### 6. Verificacao
Confirme que as remediacoes foram efetivas atraves de re-escaneamento.

## Metricas Importantes

- **MTTR** (Mean Time to Remediate)
- **Cobertura de escaneamento**
- **Vulnerabilidades criticas abertas**
- **SLA de remediacao**

## Ferramentas Recomendadas

| Ferramenta | Tipo | Destaques |
|------------|------|-----------|
| Nessus | Scanner | Lider de mercado |
| Qualys | SaaS | Integracao cloud |
| Rapid7 | Suite | Insight completo |
    `,
    category: "seguranca",
    categoryLabel: "Seguranca",
    publishedAt: "2025-06-26",
    readTime: 7,
    featured: false,
    externalUrl: "https://faiston.com/blogs/gestao-vulnerabilidades-proativa",
    tags: ["vulnerabilidades", "patch management", "seguranca"],
  },
  {
    id: "7",
    slug: "internet-satelite-transporte-publico",
    title: "Internet via Satelite no Transporte Publico",
    excerpt:
      "Explore como a conectividade via satelite esta revolucionando o transporte publico, oferecendo internet de alta velocidade em movimento.",
    content: `
# Internet via Satelite no Transporte Publico

A conectividade em movimento deixou de ser luxo para se tornar necessidade. Internet via satelite esta transformando a experiencia de passageiros e a operacao de frotas.

## A Revolucao Starlink e Concorrentes

### Starlink
SpaceX lidera com milhares de satelites em orbita baixa, oferecendo latencia de 20-40ms.

### OneWeb
Foco em conectividade B2B e governamental com cobertura global.

### Project Kuiper
Amazon entrando no mercado com planos ambiciosos.

## Beneficios para o Transporte Publico

### Para Passageiros
- Wi-Fi de alta velocidade durante viagens
- Entretenimento e produtividade em transito
- Maior satisfacao com o servico

### Para Operadores
- Telemetria em tempo real
- Manutencao preditiva
- Otimizacao de rotas
- Seguranca aprimorada com cameras IP

## Casos de Uso

1. **Onibus intermunicipais** - Viagens longas com streaming
2. **Trens** - Conectividade em areas rurais
3. **Balsas** - Cobertura em alto mar
4. **Aviacao** - Wi-Fi a bordo com baixa latencia

## Desafios de Implementacao

- Custo de hardware e instalacao
- Assinatura mensal por veiculo
- Manutencao de antenas
- Regulamentacao de frequencias
    `,
    category: "inovacao",
    categoryLabel: "Inovacao",
    publishedAt: "2025-06-25",
    readTime: 5,
    featured: false,
    externalUrl: "https://faiston.com/blogs/internet-satelite-transporte-publico",
    tags: ["satelite", "conectividade", "transporte", "Starlink"],
  },
  {
    id: "8",
    slug: "mdr-managed-detection-response",
    title: "MDR - Managed Detection and Response: O que Voce Precisa Saber",
    excerpt:
      "Entenda como servicos de MDR combinam tecnologia e expertise humana para detectar e responder a ameacas em tempo real.",
    content: `
# MDR - Managed Detection and Response

MDR (Managed Detection and Response) e um servico de seguranca que combina tecnologia avancada com analistas especializados para detectar e responder a ameacas.

## O que Diferencia o MDR?

### EDR vs MDR
- **EDR** (Endpoint Detection and Response) e a tecnologia
- **MDR** adiciona o servico gerenciado com analistas 24x7

### MSSP vs MDR
- **MSSP** tradicionalmente foca em alertas e compliance
- **MDR** prioriza deteccao avancada e resposta a incidentes

## Componentes do MDR

1. **Tecnologia** - EDR, SIEM, SOAR integrados
2. **Pessoas** - SOC com analistas experientes
3. **Processos** - Playbooks e procedimentos maduros
4. **Threat Intelligence** - Inteligencia de ameacas atualizada

## Beneficios do MDR

| Beneficio | Descricao |
|-----------|-----------|
| Deteccao 24x7 | Monitoramento continuo por especialistas |
| Resposta rapida | Contencao em minutos, nao horas |
| Expertise | Acesso a talentos escassos no mercado |
| Custo previsivel | Modelo de assinatura |

## Quando Considerar MDR?

- Equipe de seguranca limitada
- Falta de expertise em resposta a incidentes
- Necessidade de cobertura 24x7
- Budget para SOC proprio inviavel
    `,
    category: "seguranca",
    categoryLabel: "Seguranca",
    publishedAt: "2025-06-19",
    readTime: 6,
    featured: false,
    externalUrl: "https://faiston.com/blogs/mdr-managed-detection-response",
    tags: ["MDR", "SOC", "seguranca", "EDR"],
  },
  {
    id: "9",
    slug: "vpns-ipsec-ssl-diferencas",
    title: "VPNs IPsec vs SSL: Entendendo as Diferencas",
    excerpt:
      "Compare as duas principais tecnologias de VPN e descubra qual e a melhor escolha para diferentes cenarios de conectividade segura.",
    content: `
# VPNs IPsec vs SSL: Entendendo as Diferencas

VPNs sao essenciais para conectividade segura. Mas qual protocolo escolher? IPsec e SSL tem caracteristicas distintas que os tornam ideais para diferentes cenarios.

## VPN IPsec

### Como Funciona
Opera na camada 3 (rede) do modelo OSI, criptografando todo o trafego IP entre dois pontos.

### Vantagens
- Suporte nativo em roteadores e firewalls
- Excelente para site-to-site
- Baixa latencia
- Suporta qualquer protocolo IP

### Desvantagens
- Configuracao mais complexa
- Problemas com NAT traversal
- Requer cliente especifico

## VPN SSL

### Como Funciona
Opera na camada 7 (aplicacao), geralmente atraves de HTTPS (porta 443).

### Vantagens
- Funciona atraves de firewalls facilmente
- Acesso via navegador possivel
- Ideal para acesso remoto individual
- Configuracao mais simples

### Desvantagens
- Overhead maior
- Limitado a protocolos suportados

## Comparativo

| Criterio | IPsec | SSL |
|----------|-------|-----|
| Caso de uso | Site-to-site | Acesso remoto |
| Configuracao | Complexa | Simples |
| Performance | Alta | Moderada |
| Atravessa NAT | Dificil | Facil |
| Cliente | Obrigatorio | Opcional |

## Recomendacoes

- **Site-to-site**: Use IPsec
- **Acesso remoto**: Use SSL VPN
- **Hibrido**: Combine ambos conforme necessidade
    `,
    category: "infraestrutura",
    categoryLabel: "Infraestrutura",
    publishedAt: "2025-06-12",
    readTime: 5,
    featured: false,
    externalUrl: "https://faiston.com/blogs/vpns-ipsec-ssl-diferencas",
    tags: ["VPN", "IPsec", "SSL", "redes", "seguranca"],
  },
  {
    id: "10",
    slug: "maiores-ameacas-ciberneticas-2025",
    title: "As 10 Maiores Ameacas Ciberneticas de 2025",
    excerpt:
      "Conheca as principais ameacas que estao afetando organizacoes em 2025 e prepare sua defesa contra ransomware, phishing e muito mais.",
    content: `
# As 10 Maiores Ameacas Ciberneticas de 2025

O cenario de ameacas evolui constantemente. Conhecer os riscos e o primeiro passo para uma defesa eficaz.

## Top 10 Ameacas

### 1. Ransomware-as-a-Service (RaaS)
Grupos criminosos vendem ransomware como servico, democratizando o crime cibernetico.

### 2. Ataques a Supply Chain
Comprometer um fornecedor para atingir multiplos alvos simultaneamente.

### 3. Phishing com IA
E-mails altamente personalizados gerados por inteligencia artificial.

### 4. Ataques a APIs
APIs mal configuradas sao portas de entrada para vazamento de dados.

### 5. Deepfakes para Fraude
Vozes e videos sinteticos usados em golpes financeiros.

### 6. Cryptojacking
Mineracao de criptomoedas usando recursos computacionais das vitimas.

### 7. IoT Botnets
Dispositivos IoT inseguros formando exercitos de bots.

### 8. Ataques a Nuvem
Misconfigurações em ambientes cloud expondo dados sensiveis.

### 9. Zero-Day Exploits
Vulnerabilidades desconhecidas exploradas antes de patches.

### 10. Insider Threats
Ameacas internas, intencionais ou acidentais, de funcionarios.

## Como se Proteger

1. Implemente Zero Trust Architecture
2. Realize backups imutaveis
3. Treine funcionarios continuamente
4. Mantenha sistemas atualizados
5. Monitore com SIEM/MDR
    `,
    category: "seguranca",
    categoryLabel: "Seguranca",
    publishedAt: "2025-05-29",
    readTime: 8,
    featured: false,
    externalUrl: "https://faiston.com/blogs/maiores-ameacas-ciberneticas-2025",
    tags: ["ameacas", "ransomware", "phishing", "seguranca"],
  },
  {
    id: "11",
    slug: "servicos-gerenciados-ti-essenciais",
    title: "Servicos Gerenciados de TI: Por que Sao Essenciais",
    excerpt:
      "Descubra por que empresas de todos os tamanhos estao adotando servicos gerenciados para otimizar operacoes e reduzir riscos.",
    content: `
# Servicos Gerenciados de TI: Por que Sao Essenciais

Servicos gerenciados de TI evoluiram de "nice to have" para essenciais. Entenda por que essa modalidade de contratacao faz sentido para sua organizacao.

## O Modelo de Servicos Gerenciados

### Break-Fix vs Managed Services
- **Break-Fix**: Pagamento por incidente, reativo
- **Managed Services**: Mensalidade fixa, proativo

### Escopo Tipico
- Monitoramento 24x7
- Gestao de patches
- Backup e recuperacao
- Suporte helpdesk
- Seguranca gerenciada

## Beneficios Comprovados

### Reducao de Custos
Estudos mostram economia de 25-45% em custos de TI.

### Previsibilidade Financeira
Custos fixos mensais facilitam planejamento orcamentario.

### Acesso a Expertise
Equipe de especialistas por uma fracao do custo de contratacao.

### Foco no Core Business
TI deixa de ser preocupacao para ser habilitador de negocios.

## Metricas de Sucesso

| KPI | Meta | Beneficio |
|-----|------|-----------|
| Uptime | 99.9% | Disponibilidade |
| MTTR | < 4h | Agilidade |
| Satisfacao | > 90% | Experiencia |
| Incidentes/mes | Decrescente | Maturidade |

## Escolhendo um MSP

1. Avalie experiencia no seu setor
2. Verifique certificacoes (ISO, SOC)
3. Analise SLAs e garantias
4. Solicite POC ou piloto
5. Entenda modelo de pricing
    `,
    category: "blog-news",
    categoryLabel: "Blog & News",
    publishedAt: "2025-05-22",
    readTime: 6,
    featured: false,
    externalUrl: "https://faiston.com/blogs/servicos-gerenciados-ti-essenciais",
    tags: ["MSP", "servicos gerenciados", "outsourcing"],
  },
  {
    id: "12",
    slug: "estrategia-cloud-first-empresa",
    title: "Estrategia Cloud-First: Transformando sua Empresa",
    excerpt:
      "Aprenda a implementar uma estrategia cloud-first que impulsione a inovacao, reduza custos e aumente a agilidade do seu negocio.",
    content: `
# Estrategia Cloud-First: Transformando sua Empresa

Cloud-first significa priorizar a nuvem em todas as decisoes de TI. Nao e apenas sobre tecnologia, mas sobre uma mudanca de mentalidade organizacional.

## O que e Cloud-First?

### Definicao
Sempre considerar solucoes em nuvem como primeira opcao antes de alternativas on-premises.

### Principios
- Escalabilidade elastica
- Pay-as-you-go
- Automacao e DevOps
- Resiliencia built-in

## Pilares de uma Estrategia Cloud-First

### 1. Assessment e Planejamento
Avalie seu portfolio de aplicacoes: 6 Rs (Rehost, Refactor, Rearchitect, Rebuild, Replace, Retain).

### 2. Governanca Cloud
Estabeleca politicas de seguranca, custos e compliance.

### 3. Capacitacao de Times
Invista em treinamento e certificacoes cloud.

### 4. Finops
Gerencie custos de forma proativa e otimize gastos.

## Beneficios Empresariais

- **Agilidade**: Deploy em minutos, nao meses
- **Inovacao**: Acesso a servicos avancados (AI, IoT, Analytics)
- **Resiliencia**: Alta disponibilidade e disaster recovery
- **Sustentabilidade**: Datacenters mais eficientes

## Desafios Comuns

1. **Skills gap** - Falta de profissionais qualificados
2. **Legacy systems** - Aplicacoes dificeis de migrar
3. **Custos nao gerenciados** - Bill shock no final do mes
4. **Vendor lock-in** - Dependencia de um unico provedor

## Roadmap de Implementacao

| Fase | Duracao | Foco |
|------|---------|------|
| Discovery | 1-2 meses | Assessment |
| Pilot | 2-3 meses | POC com workloads |
| Migration | 6-12 meses | Migracao em ondas |
| Optimization | Continuo | Finops e melhoria |
    `,
    category: "cloud",
    categoryLabel: "Cloud",
    publishedAt: "2025-05-15",
    readTime: 7,
    featured: false,
    externalUrl: "https://faiston.com/blogs/estrategia-cloud-first-empresa",
    tags: ["cloud", "AWS", "Azure", "transformacao digital"],
  },
];

/**
 * Get featured post for hero section.
 */
export function getFeaturedPost(): BlogPost | undefined {
  return BLOG_POSTS.find((post) => post.featured);
}

/**
 * Get posts excluding featured, for grid display.
 */
export function getNonFeaturedPosts(): BlogPost[] {
  return BLOG_POSTS.filter((post) => !post.featured);
}

/**
 * Get post by slug.
 */
export function getPostBySlug(slug: string): BlogPost | undefined {
  return BLOG_POSTS.find((post) => post.slug === slug);
}

/**
 * Get posts by category.
 */
export function getPostsByCategory(category: string): BlogPost[] {
  if (category === "all") return BLOG_POSTS;
  return BLOG_POSTS.filter((post) => post.category === category);
}

/**
 * Get unique categories from posts.
 */
export function getUniqueCategories(): string[] {
  const categories = new Set(BLOG_POSTS.map((post) => post.category));
  return Array.from(categories);
}

/**
 * Get all post slugs for static generation.
 */
export function getAllPostSlugs(): string[] {
  return BLOG_POSTS.map((post) => post.slug);
}
