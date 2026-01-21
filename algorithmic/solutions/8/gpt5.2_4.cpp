#include <bits/stdc++.h>
using namespace std;

struct Instr {
    bool isHalt;
    int a = 1, b = 1, x = 1, y = 1; // for HALT: use b,y
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long k;
    cin >> k;

    const int MARK = 1024;
    const int DUMMY_A = 1023;

    vector<Instr> inst;

    if (k == 1) {
        inst.push_back(Instr{true, 1, 1, 1, 1}); // HALT PUSH 1 GOTO 1
        cout << inst.size() << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }

    long long m = k - 1; // even
    vector<int> bits;
    for (int p = 1; p <= 60; p++) {
        if ((m >> p) & 1LL) bits.push_back(p);
    }
    sort(bits.rbegin(), bits.rend());

    for (int p : bits) {
        int nDigits = p - 1;
        int base = (int)inst.size() + 1;
        int d1 = base + 1;
        int popMarkerIdx = base + nDigits + 1;
        int nextIdx = base + nDigits + 2;

        // Call instruction: with empty stack, always pushes MARK and goes to d1/popMarker
        Instr call;
        call.isHalt = false;
        call.a = DUMMY_A;
        call.x = base;                 // never taken
        call.b = MARK;
        call.y = (nDigits > 0) ? d1 : popMarkerIdx;
        inst.push_back(call);

        // Digit instructions
        for (int i = 1; i <= nDigits; i++) {
            int idx = base + i;
            Instr di;
            di.isHalt = false;
            di.a = i;
            di.b = i;
            di.x = (i < nDigits) ? (idx + 1) : popMarkerIdx;
            di.y = d1;
            inst.push_back(di);
        }

        // Pop marker and continue
        Instr popM;
        popM.isHalt = false;
        popM.a = MARK;
        popM.b = 1;       // unreachable else-branch
        popM.x = nextIdx;
        popM.y = nextIdx;
        inst.push_back(popM);
    }

    int haltIdx = (int)inst.size() + 1;
    inst.push_back(Instr{true, 1, 1, 1, haltIdx}); // HALT PUSH 1 GOTO haltIdx

    cout << inst.size() << "\n";
    for (int i = 1; i <= (int)inst.size(); i++) {
        const auto &in = inst[i - 1];
        if (in.isHalt) {
            cout << "HALT PUSH " << in.b << " GOTO " << in.y << "\n";
        } else {
            cout << "POP " << in.a << " GOTO " << in.x << " PUSH " << in.b << " GOTO " << in.y << "\n";
        }
    }
    return 0;
}