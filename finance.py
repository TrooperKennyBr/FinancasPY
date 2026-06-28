import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, date
import calendar

# ── Banco de dados ──────────────────────────────────────────────────────────
DB_PATH = "gastos.db"

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT    NOT NULL,
            valor     REAL    NOT NULL,
            tipo      TEXT    NOT NULL CHECK(tipo IN ('Fixa','Variável','Investimento','Receita')),
            data      TEXT    NOT NULL,
            mes       TEXT    NOT NULL
        )
    """)
    con.commit()
    con.close()

def db_inserir(descricao, valor, tipo, data_str, mes):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO lancamentos(descricao,valor,tipo,data,mes) VALUES(?,?,?,?,?)",
                (descricao, valor, tipo, data_str, mes))
    con.commit(); con.close()

def db_deletar(id_):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM lancamentos WHERE id=?", (id_,))
    con.commit(); con.close()

def db_listar(mes_filtro=None):
    con = sqlite3.connect(DB_PATH)
    if mes_filtro:
        rows = con.execute(
            "SELECT id,descricao,valor,tipo,data FROM lancamentos WHERE mes=? ORDER BY data DESC",
            (mes_filtro,)).fetchall()
    else:
        rows = con.execute(
            "SELECT id,descricao,valor,tipo,data FROM lancamentos ORDER BY data DESC").fetchall()
    con.close()
    return rows

def db_resumo(mes_filtro):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    totais = {}
    for tipo in ("Receita","Fixa","Variável","Investimento"):
        r = cur.execute(
            "SELECT COALESCE(SUM(valor),0) FROM lancamentos WHERE tipo=? AND mes=?",
            (tipo, mes_filtro)).fetchone()
        totais[tipo] = r[0]
    con.close()
    return totais

# ── Paleta ──────────────────────────────────────────────────────────────────
BG       = "#111318"
SURFACE  = "#1C1F27"
BORDER   = "#2A2D38"
ACCENT   = "#C0C0C0"   # prata
GREEN    = "#4CAF82"
RED      = "#E05252"
YELLOW   = "#E0B352"
BLUE     = "#5287E0"
FG       = "#E8E8EE"
FG_DIM   = "#7A7D8C"
FONT     = ("Segoe UI", 10)
FONT_B   = ("Segoe UI", 10, "bold")
FONT_LG  = ("Segoe UI", 14, "bold")
FONT_XL  = ("Segoe UI", 22, "bold")

TIPO_COR = {
    "Receita":     GREEN,
    "Fixa":        BLUE,
    "Variável":    YELLOW,
    "Investimento":ACCENT,
}

# ── App principal ────────────────────────────────────────────────────────────
class FinanceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("💰 Controle Financeiro")
        self.geometry("1050x680")
        self.minsize(900, 600)
        self.configure(bg=BG)

        # mês atual
        hoje = date.today()
        self.mes_var = tk.StringVar(value=f"{hoje.year}-{hoje.month:02d}")

        self._build_ui()
        self.atualizar()

    # ── Layout ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # cabeçalho
        hdr = tk.Frame(self, bg=BG, pady=12)
        hdr.pack(fill="x", padx=24)

        tk.Label(hdr, text="Controle Financeiro", font=FONT_XL,
                 bg=BG, fg=ACCENT).pack(side="left")

        nav = tk.Frame(hdr, bg=BG)
        nav.pack(side="right")
        tk.Button(nav, text="◀", command=self._mes_anterior,
                  bg=SURFACE, fg=FG, bd=0, padx=8, pady=4,
                  activebackground=BORDER, activeforeground=FG,
                  cursor="hand2").pack(side="left")
        self.lbl_mes = tk.Label(nav, textvariable=self.mes_var,
                                font=FONT_B, bg=BG, fg=FG, width=10)
        self.lbl_mes.pack(side="left", padx=6)
        tk.Button(nav, text="▶", command=self._mes_proximo,
                  bg=SURFACE, fg=FG, bd=0, padx=8, pady=4,
                  activebackground=BORDER, activeforeground=FG,
                  cursor="hand2").pack(side="left")

        # divisor
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # corpo
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=16)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        # cards de resumo
        self.card_frame = tk.Frame(body, bg=BG)
        self.card_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,16))

        # formulário
        self._build_form(body)

        # tabela
        self._build_table(body)

    def _card(self, parent, col, titulo, cor):
        f = tk.Frame(parent, bg=SURFACE, padx=16, pady=14,
                     highlightbackground=cor, highlightthickness=1)
        f.grid(row=0, column=col, sticky="ew", padx=(0,12) if col<3 else (0,0))
        parent.columnconfigure(col, weight=1)

        tk.Label(f, text=titulo, font=("Segoe UI",9), bg=SURFACE, fg=FG_DIM).pack(anchor="w")
        lbl = tk.Label(f, text="R$ 0,00", font=("Segoe UI",16,"bold"),
                       bg=SURFACE, fg=cor)
        lbl.pack(anchor="w", pady=(4,0))
        return lbl

    def _build_form(self, parent):
        frm = tk.Frame(parent, bg=SURFACE, padx=20, pady=16,
                       highlightbackground=BORDER, highlightthickness=1)
        frm.grid(row=1, column=0, sticky="nsew", padx=(0,16))

        tk.Label(frm, text="Novo Lançamento", font=FONT_LG,
                 bg=SURFACE, fg=FG).grid(row=0, column=0, columnspan=2,
                                          sticky="w", pady=(0,14))

        fields = [("Descrição","desc"), ("Valor (R$)","valor"),
                  ("Data","data"), ("Tipo","tipo")]
        self.entries = {}
        for i,(label,key) in enumerate(fields):
            tk.Label(frm, text=label, font=FONT, bg=SURFACE, fg=FG_DIM
                     ).grid(row=i+1, column=0, sticky="w", pady=4)
            if key == "tipo":
                var = tk.StringVar(value="Variável")
                w = ttk.Combobox(frm, textvariable=var, state="readonly",
                                 values=["Receita","Fixa","Variável","Investimento"],
                                 font=FONT, width=22)
                w.grid(row=i+1, column=1, sticky="ew", pady=4, padx=(8,0))
                self.entries[key] = var
            elif key == "data":
                var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
                w = tk.Entry(frm, textvariable=var, font=FONT,
                             bg=BORDER, fg=FG, insertbackground=FG,
                             relief="flat", bd=4)
                w.grid(row=i+1, column=1, sticky="ew", pady=4, padx=(8,0))
                self.entries[key] = var
            else:
                var = tk.StringVar()
                w = tk.Entry(frm, textvariable=var, font=FONT,
                             bg=BORDER, fg=FG, insertbackground=FG,
                             relief="flat", bd=4)
                w.grid(row=i+1, column=1, sticky="ew", pady=4, padx=(8,0))
                self.entries[key] = var

        frm.columnconfigure(1, weight=1)

        tk.Button(frm, text="＋  Adicionar", font=FONT_B,
                  bg=ACCENT, fg=BG, relief="flat", padx=16, pady=8,
                  activebackground="#E8E8E8", cursor="hand2",
                  command=self._adicionar).grid(row=6, column=0, columnspan=2,
                                                sticky="ew", pady=(16,0))

        # saldo líquido
        self.lbl_saldo_form = tk.Label(frm, text="", font=FONT_B,
                                       bg=SURFACE, fg=GREEN)
        self.lbl_saldo_form.grid(row=7, column=0, columnspan=2,
                                  sticky="w", pady=(12,0))

    def _build_table(self, parent):
        wrap = tk.Frame(parent, bg=SURFACE,
                        highlightbackground=BORDER, highlightthickness=1)
        wrap.grid(row=1, column=1, sticky="nsew")

        tk.Label(wrap, text="Lançamentos", font=FONT_LG,
                 bg=SURFACE, fg=FG, pady=14, padx=16).pack(anchor="w")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Treeview",
                        background=SURFACE, foreground=FG,
                        fieldbackground=SURFACE, rowheight=30,
                        borderwidth=0, font=FONT)
        style.configure("Dark.Treeview.Heading",
                        background=BORDER, foreground=FG_DIM,
                        borderwidth=0, font=FONT_B)
        style.map("Dark.Treeview",
                  background=[("selected","#2E3245")],
                  foreground=[("selected",FG)])

        cols = ("desc","valor","tipo","data")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings",
                                  style="Dark.Treeview", selectmode="browse")
        self.tree.heading("desc",  text="Descrição")
        self.tree.heading("valor", text="Valor")
        self.tree.heading("tipo",  text="Tipo")
        self.tree.heading("data",  text="Data")
        self.tree.column("desc",  width=220, minwidth=120)
        self.tree.column("valor", width=110, anchor="e")
        self.tree.column("tipo",  width=110, anchor="center")
        self.tree.column("data",  width=90,  anchor="center")

        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8,0), pady=(0,8))
        sb.pack(side="right", fill="y", pady=(0,8))

        tk.Button(wrap, text="🗑  Excluir selecionado",
                  font=FONT, bg=BORDER, fg=RED, relief="flat",
                  padx=10, pady=6, activebackground=SURFACE,
                  cursor="hand2", command=self._excluir).pack(pady=(0,10))

    # ── Navegação de mês ────────────────────────────────────────────────────
    def _parse_mes(self):
        y, m = self.mes_var.get().split("-")
        return int(y), int(m)

    def _mes_anterior(self):
        y, m = self._parse_mes()
        m -= 1
        if m == 0: m, y = 12, y-1
        self.mes_var.set(f"{y}-{m:02d}")
        self.atualizar()

    def _mes_proximo(self):
        y, m = self._parse_mes()
        m += 1
        if m == 13: m, y = 1, y+1
        self.mes_var.set(f"{y}-{m:02d}")
        self.atualizar()

    # ── CRUD ────────────────────────────────────────────────────────────────
    def _adicionar(self):
        desc  = self.entries["desc"].get().strip()
        valor_str = self.entries["valor"].get().strip().replace(",",".")
        tipo  = self.entries["tipo"].get()
        data_str  = self.entries["data"].get().strip()

        if not desc:
            messagebox.showwarning("Campo vazio","Preencha a descrição."); return
        try:
            valor = float(valor_str)
            assert valor > 0
        except:
            messagebox.showwarning("Valor inválido","Digite um valor numérico positivo."); return
        try:
            dt = datetime.strptime(data_str, "%d/%m/%Y")
        except:
            messagebox.showwarning("Data inválida","Use o formato DD/MM/AAAA."); return

        mes = f"{dt.year}-{dt.month:02d}"
        db_inserir(desc, valor, tipo, dt.strftime("%Y-%m-%d"), mes)
        self.entries["desc"].set("")
        self.entries["valor"].set("")
        self.atualizar()

    def _excluir(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Nada selecionado","Clique em um lançamento primeiro."); return
        id_ = self.tree.item(sel[0])["tags"][0]
        if messagebox.askyesno("Confirmar","Excluir este lançamento?"):
            db_deletar(id_)
            self.atualizar()

    # ── Atualizar tela ──────────────────────────────────────────────────────
    def atualizar(self):
        mes = self.mes_var.get()

        # cards
        totais = db_resumo(mes)
        receita  = totais["Receita"]
        fixa     = totais["Fixa"]
        variavel = totais["Variável"]
        invest   = totais["Investimento"]
        gasto_total = fixa + variavel
        saldo = receita - gasto_total - invest

        # recria cards
        for w in self.card_frame.winfo_children():
            w.destroy()
        dados_cards = [
            ("Receitas",      GREEN,  receita),
            ("Gastos Fixos",  BLUE,   fixa),
            ("Gastos Variáveis",YELLOW,variavel),
            ("Investimentos", ACCENT, invest),
        ]
        for i,(titulo,cor,val) in enumerate(dados_cards):
            f = tk.Frame(self.card_frame, bg=SURFACE, padx=16, pady=12,
                         highlightbackground=cor, highlightthickness=1)
            f.grid(row=0, column=i, sticky="ew",
                   padx=(0,12) if i<3 else (0,0))
            self.card_frame.columnconfigure(i, weight=1)
            tk.Label(f, text=titulo, font=("Segoe UI",9),
                     bg=SURFACE, fg=FG_DIM).pack(anchor="w")
            tk.Label(f, text=f"R$ {val:,.2f}".replace(",","X").replace(".",",").replace("X","."),
                     font=("Segoe UI",15,"bold"), bg=SURFACE, fg=cor).pack(anchor="w", pady=(4,0))

        # saldo no form
        cor_saldo = GREEN if saldo >= 0 else RED
        self.lbl_saldo_form.config(
            text=f"Saldo do mês: R$ {saldo:,.2f}".replace(",","X").replace(".",",").replace("X","."),
            fg=cor_saldo)

        # tabela
        for row in self.tree.get_children():
            self.tree.delete(row)

        for row in db_listar(mes):
            id_, desc, valor, tipo, data = row
            val_fmt = f"R$ {valor:,.2f}".replace(",","X").replace(".",",").replace("X",".")
            dt_fmt = datetime.strptime(data,"%Y-%m-%d").strftime("%d/%m/%Y")
            sinal = "-" if tipo != "Receita" else "+"
            cor = TIPO_COR.get(tipo, FG)
            self.tree.insert("", "end",
                             values=(desc, f"{sinal} {val_fmt}", tipo, dt_fmt),
                             tags=(id_, tipo))

        for tipo, cor in TIPO_COR.items():
            self.tree.tag_configure(tipo, foreground=cor)


# ── Entrada ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app = FinanceApp()
    app.mainloop()
