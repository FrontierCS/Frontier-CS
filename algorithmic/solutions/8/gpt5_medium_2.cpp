#include <bits/stdc++.h>
using namespace std;

struct Instr {
    int type; // 0 = POP, 1 = HALT
    int a, x, b, y; // for POP: a,x,b,y; for HALT: b,y (a,x unused)
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long k;
    if (!(cin >> k)) return 0;

    vector<Instr> prog;

    auto add_pop = [&](int a, int x, int b, int y) {
        Instr ins;
        ins.type = 0;
        ins.a = a; ins.x = x; ins.b = b; ins.y = y;
        prog.push_back(ins);
        return (int)prog.size(); // 1-based index
    };
    auto add_halt = [&](int b, int y) {
        Instr ins;
        ins.type = 1;
        ins.b = b; ins.y = y;
        prog.push_back(ins);
        return (int)prog.size(); // 1-based index
    };

    if (k == 1) {
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }
    if (k == 3) {
        cout << 2 << "\n";
        cout << "POP 2 GOTO 2 PUSH 2 GOTO 1\n";
        cout << "HALT PUSH 1 GOTO 2\n";
        return 0;
    }

    // General construction for k >= 5
    // Tokens:
    // S = 1 (base stack token)
    int S = 1;
    int nextSym = 2;

    // Initial push S
    int init_idx = add_pop(S, 0, S, 0); // placeholders to patch

    // Determine blocks and extra HALT filler
    long long T = (k - 5) / 2; // T >= 0
    int H = (int)(T & 1);      // extra HALT fillers (0 or 1)
    // For each i >= 1 where bit i in T is set, add block of length 2^(i+1)-1
    // We will add in ascending order i = 1..30
    vector<pair<int,int>> segments; // pair<entry_idx, halt_idx>
    int prev_halt = 0;

    auto add_block_i = [&](int i) {
        int entry = (int)prog.size() + 1;
        int cur_entry = entry;
        // POP lines
        vector<int> tokens;
        for (int j = 0; j < i; ++j) {
            int tok = nextSym++;
            tokens.push_back(tok);
        }
        for (int j = 0; j < i; ++j) {
            int a = tokens[j];
            int x = entry + j + 1; // next line in block
            int y = entry;         // goto entry on push
            add_pop(a, x, a, y);
        }
        // HALT to transition (counts as +1 step and pushes S)
        int halt_idx = add_halt(S, 0); // y to be patched
        // link previous segment's halt to this entry
        if (prev_halt != 0) {
            prog[prev_halt - 1].y = entry;
        }
        prev_halt = halt_idx;
        segments.push_back({entry, halt_idx});
    };

    for (int i = 1; i <= 30; ++i) {
        if ((T >> i) & 1LL) {
            add_block_i(i);
        }
    }

    // Extra HALT filler if H == 1
    if (H == 1) {
        int entry = (int)prog.size() + 1;
        int halt_idx = add_halt(S, 0); // y to be patched
        if (prev_halt != 0) {
            prog[prev_halt - 1].y = entry;
        }
        prev_halt = halt_idx;
    }

    // Cleanup: pop all S then HALT
    int cleanup_start = (int)prog.size() + 1;
    int c1 = add_pop(S, cleanup_start, S, cleanup_start + 1); // POP S GOTO c1, else PUSH S GOTO c2
    int c2 = add_pop(S, cleanup_start + 2, S, cleanup_start + 1); // POP S GOTO c3, else PUSH S GOTO c2
    int c3 = add_halt(S, cleanup_start + 2); // final HALT (y arbitrary valid)

    // Patch links
    if (!segments.empty() || H == 1) {
        // Link last segment/filler to cleanup
        prog[prev_halt - 1].y = cleanup_start;
        // Initial goto to first segment
        int first_entry = segments.empty() ? ((int)prog.size() >= cleanup_start ? cleanup_start - 2 : cleanup_start) : segments.front().first;
        prog[init_idx - 1].x = first_entry;
        prog[init_idx - 1].y = first_entry;
    } else {
        // No segments/fillers: initial goes directly to cleanup start
        prog[init_idx - 1].x = cleanup_start;
        prog[init_idx - 1].y = cleanup_start;
    }

    // Output
    cout << (int)prog.size() << "\n";
    for (int i = 0; i < (int)prog.size(); ++i) {
        if (prog[i].type == 0) {
            cout << "POP " << prog[i].a << " GOTO " << prog[i].x
                 << " PUSH " << prog[i].b << " GOTO " << prog[i].y << "\n";
        } else {
            cout << "HALT PUSH " << prog[i].b << " GOTO " << prog[i].y << "\n";
        }
    }
    return 0;
}