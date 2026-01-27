#include <bits/stdc++.h>
using namespace std;

struct Label {
    int pos = -1;
};

enum class InstrType { POP, HALT };

struct Instr {
    InstrType type;
    int a = 1, b = 1;
    Label *x = nullptr, *y = nullptr;
};

struct Builder {
    static constexpr int A_ALWAYS_MISMATCH = 1024;
    static constexpr int TEMP_NOP = 1023;
    static constexpr int TEMP_EXIT = 1022;

    vector<Instr> prog;
    vector<unique_ptr<Label>> labels;
    int nextMarker = 1; // markers: 1..1021

    Label* newLabel() {
        labels.emplace_back(make_unique<Label>());
        return labels.back().get();
    }

    void bind(Label* l) {
        if (!l) return;
        if (l->pos != -1) {
            // Already bound; should not happen in this construction.
            return;
        }
        l->pos = (int)prog.size() + 1;
    }

    void emitPopGoto(int a, Label* x, int b, Label* y) {
        Instr in;
        in.type = InstrType::POP;
        in.a = a;
        in.b = b;
        in.x = x;
        in.y = y;
        prog.push_back(in);
    }

    void emitHalt(int b, Label* y) {
        Instr in;
        in.type = InstrType::HALT;
        in.b = b;
        in.y = y;
        prog.push_back(in);
    }

    void emitPush(int v, Label* go) {
        // Unconditional: a=1024 never appears on stack.
        emitPopGoto(A_ALWAYS_MISMATCH, go, v, go);
    }

    void emitPopExpected(int v, Label* go) {
        emitPopGoto(v, go, TEMP_NOP, go); // mismatch should never happen
    }

    void emitNOP(Label* cont) {
        Label* afterPush = newLabel();
        emitPush(TEMP_NOP, afterPush);
        bind(afterPush);
        emitPopExpected(TEMP_NOP, cont);
    }

    Label* buildEven(uint64_t E, Label* cont, Label* start = nullptr) {
        if (E == 0) {
            if (start != nullptr) {
                // Not expected in this construction.
                // Fall back: treat it as no-op by jumping to cont isn't possible without extra instruction.
            }
            return cont;
        }

        if (!start) start = newLabel();
        bind(start);

        if (E == 2) {
            emitNOP(cont);
            return start;
        }
        if (E == 4) {
            Label* mid = newLabel();
            emitNOP(mid);
            buildEven(2, cont, mid);
            return start;
        }

        if (E % 4 == 2) { // E >= 6
            Label* rest = newLabel();
            emitNOP(rest);
            buildEven(E - 2, cont, rest);
            return start;
        }

        // E % 4 == 0 and E >= 8
        int marker = nextMarker++;
        if (marker >= TEMP_EXIT) marker = 1; // should never happen
        Label* bodyStart = newLabel();
        Label* check = newLabel();
        Label* popExit = newLabel();

        emitPush(marker, bodyStart);

        uint64_t L = E / 2 - 2;
        buildEven(L, check, bodyStart);

        bind(check);
        // If top is marker, pop and repeat body; else push TEMP_EXIT and go popExit.
        emitPopGoto(marker, bodyStart, TEMP_EXIT, popExit);

        bind(popExit);
        emitPopExpected(TEMP_EXIT, cont);

        return start;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long k_in;
    if (!(cin >> k_in)) return 0;
    uint64_t k = (uint64_t)k_in;
    uint64_t E = k - 1; // even

    Builder b;
    Label* halt = b.newLabel();

    if (E > 0) {
        Label* entry = b.newLabel();
        b.buildEven(E, halt, entry);
    }
    // If E == 0, program starts at HALT.

    b.bind(halt);
    b.emitHalt(1, halt);

    int n = (int)b.prog.size();
    // Sanity: bind check
    for (auto &lp : b.labels) {
        if (lp->pos == -1) {
            // Should not happen; bind to 1 to keep output valid.
            lp->pos = 1;
        }
    }
    if (n < 1) n = 1;
    if (n > 512) {
        // Should not happen with this construction; still output a trivial valid program.
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }

    cout << n << "\n";
    for (int i = 0; i < n; i++) {
        const auto &in = b.prog[i];
        if (in.type == InstrType::HALT) {
            cout << "HALT PUSH " << in.b << " GOTO " << in.y->pos << "\n";
        } else {
            cout << "POP " << in.a << " GOTO " << in.x->pos
                 << " PUSH " << in.b << " GOTO " << in.y->pos << "\n";
        }
    }
    return 0;
}