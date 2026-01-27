#include <bits/stdc++.h>
using namespace std;

struct Instr {
    bool isPop; // true = POP, false = HALT
    int a, b, x, y; // For POP: a, b, x, y; For HALT: b, y (a,x unused)
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long k;
    if (!(cin >> k)) return 0;
    long long K = k + 1; // even, up to 2^31

    // Collect bit positions (>=1) set in K
    vector<int> base_m;
    for (int i = 1; i <= 31; ++i) {
        if ((K >> i) & 1LL) base_m.push_back(i);
    }
    int s = (int)base_m.size();

    // Build final list of blocks: base_m plus (s-1) extra blocks of m=2
    vector<int> mlist = base_m;
    for (int i = 0; i < s - 1; ++i) mlist.push_back(2);

    // Keep only blocks with m>=2 for actual POP instructions
    vector<int> coded;
    for (int m : mlist) if (m >= 2) coded.push_back(m);

    int C = (int)coded.size();
    vector<int> start(C);
    int sum_d = 0;
    for (int i = 0; i < C; ++i) {
        start[i] = sum_d + 1;            // global index of first instr in this block
        sum_d += coded[i] - 1;           // depth d = m-1
    }
    int haltIndex = sum_d + 1; // Index of HALT instruction (always at the end)

    vector<Instr> insns(haltIndex);

    if (C == 0) {
        // Only HALT instruction
        insns[0].isPop = false;
        insns[0].b = 1;
        insns[0].y = 1;
    } else {
        // Generate POP instructions for each coded block
        for (int bi = 0; bi < C; ++bi) {
            int m = coded[bi];
            int d = m - 1; // number of POP levels in this block
            int sidx = start[bi];

            for (int i = 1; i <= d; ++i) {
                int g = sidx + (i - 1);
                insns[g - 1].isPop = true;
                insns[g - 1].a = i;
                insns[g - 1].b = i;
                insns[g - 1].y = sidx;
                if (i < d) {
                    insns[g - 1].x = sidx + i;
                } else {
                    // last level of this block
                    insns[g - 1].x = (bi + 1 < C) ? start[bi + 1] : haltIndex;
                }
            }
        }
        // HALT instruction at the end
        insns[haltIndex - 1].isPop = false;
        insns[haltIndex - 1].b = 1;
        insns[haltIndex - 1].y = start.back();
    }

    cout << insns.size() << '\n';
    for (size_t i = 0; i < insns.size(); ++i) {
        if (insns[i].isPop) {
            cout << "POP " << insns[i].a << " GOTO " << insns[i].x
                 << " PUSH " << insns[i].b << " GOTO " << insns[i].y << '\n';
        } else {
            cout << "HALT PUSH " << insns[i].b << " GOTO " << insns[i].y << '\n';
        }
    }
    return 0;
}