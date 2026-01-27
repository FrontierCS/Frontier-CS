#include <bits/stdc++.h>
using namespace std;

struct Instr {
    enum Type { POP, HALT } type;
    int a = 1, b = 1;
    int x = 0, y = 0; // label indices (0-based)
    bool set = false;
};

static const int NEVER = 1024; // never pushed
static const int TEMP  = 1023; // pushed/popped as temporary

vector<Instr> prog;
int nextMarker = 1;

int newLabel() {
    prog.push_back(Instr());
    return (int)prog.size() - 1;
}

void setPOP(int lbl, int a, int x, int b, int y) {
    auto &ins = prog[lbl];
    ins.type = Instr::POP;
    ins.a = a;
    ins.x = x;
    ins.b = b;
    ins.y = y;
    ins.set = true;
}

void setHALT(int lbl, int b, int y) {
    auto &ins = prog[lbl];
    ins.type = Instr::HALT;
    ins.b = b;
    ins.y = y;
    ins.set = true;
}

struct Proc {
    int m0, m1;
    int entry;
};

Proc build(long long K, int cont0, int cont1) {
    Proc p;
    p.m0 = nextMarker++;
    p.m1 = nextMarker++;

    // Return dispatcher start label
    int ret_check = newLabel();

    if (K <= 9) {
        int m = (int)((K - 3) / 2); // dummy pairs
        if (m == 0) {
            p.entry = ret_check;
        } else {
            p.entry = newLabel();
            int cur = p.entry;
            for (int i = 0; i < m; i++) {
                int popLbl = newLabel();
                setPOP(cur, NEVER, cur, TEMP, popLbl); // unconditional push TEMP -> popLbl
                int nxt = (i == m - 1) ? ret_check : newLabel();
                setPOP(popLbl, TEMP, nxt, TEMP, nxt); // pop TEMP -> nxt
                cur = nxt;
            }
        }
    } else {
        bool extra = (K % 4 == 1); // need +7 version
        long long u = extra ? (K - 7) / 2 : (K - 5) / 2;

        int entry = newLabel();
        int after1 = newLabel();
        int after2;
        if (extra) after2 = newLabel();
        else after2 = ret_check;

        // Build sub with continuations in parent
        Proc sub = build(u, after1, after2);

        // Call sub twice
        setPOP(entry,  NEVER, entry,  sub.m0, sub.entry);
        setPOP(after1, NEVER, after1, sub.m1, sub.entry);

        // Optional extra dummy pair after second call
        if (extra) {
            int popTemp = newLabel();
            setPOP(after2, NEVER, after2, TEMP, popTemp);          // push TEMP
            setPOP(popTemp, TEMP, ret_check, TEMP, ret_check);     // pop TEMP -> ret_check
        }

        p.entry = entry;
    }

    // Return dispatcher: uniform 3 steps for marker0 or marker1
    int dummyPush = newLabel();
    int dummyPop  = newLabel();
    int failPop   = newLabel();
    int check1    = newLabel();

    setPOP(ret_check, p.m0, dummyPush, p.m0, failPop);
    setPOP(dummyPush, NEVER, dummyPush, TEMP, dummyPop); // unconditional push TEMP
    setPOP(dummyPop, TEMP, cont0, TEMP, cont0);          // pop TEMP -> cont0
    setPOP(failPop, p.m0, check1, p.m0, check1);          // pop the pushed m0
    setPOP(check1, p.m1, cont1, p.m1, cont1);             // pop m1 -> cont1

    return p;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long k;
    cin >> k;

    if (k == 1) {
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }
    if (k == 3) {
        cout << 3 << "\n";
        cout << "POP 1 GOTO 1 PUSH 1 GOTO 2\n";
        cout << "POP 1 GOTO 3 PUSH 1 GOTO 2\n";
        cout << "HALT PUSH 1 GOTO 3\n";
        return 0;
    }

    // General case: k >= 5, odd
    long long K = k - 2; // length of root procedure

    prog.clear();
    nextMarker = 1;

    int start = newLabel();
    int haltLbl = newLabel();
    setHALT(haltLbl, 1, haltLbl);

    Proc root = build(K, haltLbl, haltLbl);
    setPOP(start, NEVER, start, root.m0, root.entry);

    // Validate all instructions set
    for (int i = 0; i < (int)prog.size(); i++) {
        if (!prog[i].set) {
            // Fill unreachable/unset with a harmless self-loop HALT (won't be reached)
            setHALT(i, 1, i);
        }
    }

    int n = (int)prog.size();
    if (n > 512) {
        // Should not happen, but ensure valid output.
        // Fallback to simplest (won't be correct for judge, but constraints guarantee existence).
        n = 1;
        prog.assign(1, Instr());
        setHALT(0, 1, 0);
    }

    cout << n << "\n";
    for (int i = 0; i < n; i++) {
        const auto &ins = prog[i];
        if (ins.type == Instr::HALT) {
            cout << "HALT PUSH " << ins.b << " GOTO " << (ins.y + 1) << "\n";
        } else {
            cout << "POP " << ins.a << " GOTO " << (ins.x + 1)
                 << " PUSH " << ins.b << " GOTO " << (ins.y + 1) << "\n";
        }
    }
    return 0;
}