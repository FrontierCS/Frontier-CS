#include <bits/stdc++.h>
using namespace std;

struct Instr {
    bool halt; // false = POP, true = HALT
    int a, x, b, y; // for POP: a,x,b,y; for HALT: b,y used
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long k;
    if (!(cin >> k)) return 0;
    
    vector<Instr> prog;
    auto addPop = [&](int a, int x, int b, int y) -> int {
        prog.push_back({false, a, x, b, y});
        return (int)prog.size();
    };
    auto addHalt = [&](int b, int y) -> int {
        prog.push_back({true, 0, 0, b, y});
        return (int)prog.size();
    };
    
    if (k == 1) {
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }
    
    long long R = k - 1; // even
    vector<int> bits;
    for (int j = 1; j <= 30; ++j) {
        if (R & (1LL << j)) bits.push_back(j);
    }
    int t = (int)bits.size();
    
    int sentinel = 1024;
    
    // Initial instruction: push sentinel and goto first block entry (patched later)
    int initIdx = addPop(1, 1, sentinel, 0); // y to be patched
    
    vector<int> entryIdx; entryIdx.reserve(t);
    vector<int> popSIdx;  popSIdx.reserve(t);
    vector<int> pushSIdx; pushSIdx.reserve(max(0, t-1));
    
    for (int i = 0; i < t; ++i) {
        int j = bits[i];
        int m = j - 1; // levels
        
        int entry = (int)prog.size() + 1; // next line index
        vector<int> levelIdx;
        levelIdx.reserve(m);
        for (int l = 1; l <= m; ++l) {
            // POP Tl GOTO next_level, else PUSH Tl GOTO entry
            int Tl = l; // token for level l
            int li = addPop(Tl, 0, Tl, entry); // x to patch
            levelIdx.push_back(li);
        }
        int popS = addPop(sentinel, 0, sentinel, 0); // x and y to patch (y set to same as x later)
        
        // Patch level x targets
        for (int l = 0; l < m; ++l) {
            int xline = (l + 1 < m) ? levelIdx[l + 1] : popS;
            prog[levelIdx[l] - 1].x = xline;
        }
        
        entryIdx.push_back((m > 0) ? entry : popS);
        popSIdx.push_back(popS);
        
        if (i + 1 < t) {
            // Add push sentinel line; y will be patched to next block's entry
            int pushS = addPop(1, 1, sentinel, 0); // unconditional else on empty -> push S; x unused; y patch
            // popS should jump to this pushS
            prog[popS - 1].x = pushS;
            prog[popS - 1].y = pushS; // unreachable else, but keep valid
            pushSIdx.push_back(pushS);
        }
    }
    
    // Add final HALT
    int haltIdx = addHalt(1, 1);
    
    // Patch last block's popS to HALT
    prog[popSIdx.back() - 1].x = haltIdx;
    prog[popSIdx.back() - 1].y = haltIdx; // keep both branches valid
    
    // Patch pushS Y targets to next block entry
    for (int i = 0; i + 1 < t; ++i) {
        prog[pushSIdx[i] - 1].y = entryIdx[i + 1];
    }
    
    // Patch init to first block entry
    prog[initIdx - 1].y = entryIdx[0];
    
    // Output
    cout << prog.size() << "\n";
    for (auto &ins : prog) {
        if (!ins.halt) {
            cout << "POP " << ins.a << " GOTO " << ins.x << " PUSH " << ins.b << " GOTO " << ins.y << "\n";
        } else {
            cout << "HALT PUSH " << ins.b << " GOTO " << ins.y << "\n";
        }
    }
    return 0;
}