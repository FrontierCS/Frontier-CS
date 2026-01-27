#include <bits/stdc++.h>
using namespace std;

struct Instr {
    bool isHalt;
    int a = 1, b = 1, x = 1, y = 1; // if isHalt: b,y used; else: a,x,b,y
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long k;
    if (!(cin >> k)) return 0;

    const int T = 1024;

    vector<Instr> prog;

    auto addPow2 = [&](int p, int nextIndex) {
        int old = (int)prog.size();
        int start = old + 1; // 1-based
        if (p == 1) {
            // 2-step balanced block
            Instr i1; i1.isHalt = false; i1.a = T; i1.x = nextIndex; i1.b = T; i1.y = start + 1;
            Instr i2; i2.isHalt = false; i2.a = T; i2.x = nextIndex; i2.b = T; i2.y = start + 1;
            prog.push_back(i1);
            prog.push_back(i2);
        } else {
            int m = p - 1;
            int afterCycle = start + m; // first instruction of 2-step block
            // cycle instructions
            for (int i = 1; i <= m; i++) {
                Instr in;
                in.isHalt = false;
                in.a = i;
                in.b = i;
                in.y = start;
                if (i < m) in.x = start + i; // next check
                else in.x = afterCycle;       // overflow -> after cycle
                prog.push_back(in);
            }
            // 2-step balanced block
            Instr i1; i1.isHalt = false; i1.a = T; i1.x = nextIndex; i1.b = T; i1.y = afterCycle + 1;
            Instr i2; i2.isHalt = false; i2.a = T; i2.x = nextIndex; i2.b = T; i2.y = afterCycle + 1;
            prog.push_back(i1);
            prog.push_back(i2);
        }
    };

    if (k == 1) {
        prog.push_back(Instr{true, 1, 1, 1, 1});
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }

    long long nEven = k - 1; // even
    vector<int> powers;
    for (int p = 30; p >= 1; p--) {
        if (nEven & (1LL << p)) powers.push_back(p);
    }

    for (int idx = 0; idx < (int)powers.size(); idx++) {
        int p = powers[idx];
        int old = (int)prog.size();
        int blockSize = (p == 1 ? 2 : p + 1);
        int nextIndex = old + blockSize + 1; // next block start (or HALT)
        addPow2(p, nextIndex);
    }

    int haltIndex = (int)prog.size() + 1;
    Instr h; h.isHalt = true; h.b = 1; h.y = haltIndex;
    prog.push_back(h);

    cout << prog.size() << "\n";
    for (int i = 0; i < (int)prog.size(); i++) {
        const auto &in = prog[i];
        if (in.isHalt) {
            cout << "HALT PUSH " << in.b << " GOTO " << in.y << "\n";
        } else {
            cout << "POP " << in.a << " GOTO " << in.x << " PUSH " << in.b << " GOTO " << in.y << "\n";
        }
    }

    return 0;
}