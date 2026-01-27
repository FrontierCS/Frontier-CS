#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long k;
    if (!(cin >> k)) return 0;
    
    if (k == 1) {
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
        return 0;
    }
    
    long long S = (k - 1) / 2; // S = sum of (2^m - 1)
    vector<int> blocks;
    for (int m = 30; m >= 1; --m) {
        long long val = (1LL << m) - 1;
        if (val <= S) {
            blocks.push_back(m);
            S -= val;
        }
    }
    
    // Just in case (should always be zero for valid k)
    if (S != 0) {
        // Fallback: use ones (m=1) to fill remaining (shouldn't happen)
        while (S > 0) {
            blocks.push_back(1);
            S -= 1;
        }
    }
    
    int total_pop = 0;
    for (int m : blocks) total_pop += m;
    int n = total_pop + 1; // +1 for final HALT
    cout << n << "\n";
    
    vector<int> base(blocks.size());
    int idx = 1;
    for (size_t i = 0; i < blocks.size(); ++i) {
        base[i] = idx;
        idx += blocks[i];
    }
    int halt_idx = n;
    
    int a_val = 1;
    for (size_t bi = 0; bi < blocks.size(); ++bi) {
        int m = blocks[bi];
        for (int j = 1; j <= m; ++j) {
            int a = a_val++;
            int X, Y;
            Y = base[bi]; // restart at block start on mismatch
            if (j < m) {
                X = base[bi] + j; // next level in this block
            } else {
                if (bi + 1 < blocks.size()) X = base[bi + 1]; // next block start
                else X = halt_idx; // final: proceed to HALT
            }
            cout << "POP " << a << " GOTO " << X << " PUSH " << a << " GOTO " << Y << "\n";
        }
    }
    
    // Final HALT instruction; choose any valid b and y
    int b = 1;
    int y = halt_idx; // self-loop if somehow non-empty (shouldn't happen)
    cout << "HALT PUSH " << b << " GOTO " << y << "\n";
    
    return 0;
}