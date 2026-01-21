#include <bits/stdc++.h>
using namespace std;

struct Inst {
    bool isHalt = false;
    int a = 0, b = 0, x = 0, y = 0; // for POP: a,x,b,y ; for HALT: b,y
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long k;
    if (!(cin >> k)) return 0;

    const int MARK = 1024;
    const int DUMMY_A = 1023;

    if (k == 1) {
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }

    long long m = k - 1; // even
    vector<int> blocks;  // each element is mBits = p-1, block cost = 2^p
    for (int p = 30; p >= 1; --p) {
        if ((m >> p) & 1LL) blocks.push_back(p - 1);
    }

    vector<int> startIdx(blocks.size());
    int cur = 1;
    for (size_t i = 0; i < blocks.size(); ++i) {
        startIdx[i] = cur;
        cur += blocks[i] + 2; // push marker + mBits bit-insts + return
    }
    int haltIdx = cur;
    int n = haltIdx;

    vector<Inst> inst(n + 1);

    for (size_t bi = 0; bi < blocks.size(); ++bi) {
        int mBits = blocks[bi];
        int start = startIdx[bi];
        int firstBit = start + 1;
        int retIdx = start + mBits + 1;
        int after = (bi + 1 < blocks.size()) ? startIdx[bi + 1] : haltIdx;

        // Unconditional push marker -> firstBit
        inst[start] = Inst{false, DUMMY_A, MARK, firstBit, firstBit};

        // Bit instructions
        for (int j = 1; j <= mBits; ++j) {
            int idx = start + j;
            inst[idx] = Inst{false, j, j, idx + 1, firstBit};
        }

        // Return: pop marker -> after
        inst[retIdx] = Inst{false, MARK, 1, after, retIdx};
    }

    inst[haltIdx] = Inst{true, 0, 1, 0, haltIdx};

    if (n > 512) {
        // Guaranteed solvable; this should never happen with the construction.
        return 0;
    }

    cout << n << "\n";
    for (int i = 1; i <= n; ++i) {
        if (inst[i].isHalt) {
            cout << "HALT PUSH " << inst[i].b << " GOTO " << inst[i].y << "\n";
        } else {
            cout << "POP " << inst[i].a << " GOTO " << inst[i].x
                 << " PUSH " << inst[i].b << " GOTO " << inst[i].y << "\n";
        }
    }

    return 0;
}