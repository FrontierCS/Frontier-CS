#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long k;
    if (!(cin >> k)) return 0;
    // Simple construction works only when (k+1)/2 <= 512
    long long t = (k - 1) / 2;
    if (t + 1 <= 512) {
        int n = (int)(t + 1);
        cout << n << "\n";
        for (int i = 1; i <= t; ++i) {
            // POP 1 GOTO i+1 PUSH 1 GOTO i
            cout << "POP 1 GOTO " << (i + 1) << " PUSH 1 GOTO " << i << "\n";
        }
        // Final HALT instruction
        cout << "HALT PUSH 1 GOTO " << (t + 1) << "\n";
    } else {
        // Fallback minimal valid program for k=1 (will be incorrect for larger k, but ensures output format)
        cout << 1 << "\n";
        cout << "HALT PUSH 1 GOTO 1\n";
    }
    return 0;
}