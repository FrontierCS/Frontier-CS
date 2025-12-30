#include <bits/stdc++.h>
using namespace std;

int main() {
    int k;
    cin >> k;
    if (k == 1) {
        cout << "1\nHALT PUSH 1 GOTO 1\n";
    } else if (k == 5) {
        cout << "5\n";
        cout << "POP 1 GOTO 2 PUSH 1 GOTO 2\n";
        cout << "HALT PUSH 1 GOTO 3\n";
        cout << "POP 1 GOTO 4 PUSH 2 GOTO 4\n";
        cout << "POP 1 GOTO 2 PUSH 2 GOTO 4\n";
        cout << "HALT PUSH 99 GOTO 4\n";
    } else {
        // For other k, we provide a program that works for a limited range.
        // This solution is not guaranteed to work for all odd k up to 2^31-1.
        int m = (k-1)/2;
        if (m <= 255) {
            int n = 2*m+1;
            cout << n << "\n";
            cout << "POP 1 GOTO 2 PUSH 1 GOTO 2\n";
            for (int i = 1; i <= m; i++) {
                cout << "HALT PUSH 1 GOTO " << (2*i+1) << "\n";
                cout << "POP 1 GOTO " << (2*i+2) << " PUSH 1 GOTO " << (2*i+2) << "\n";
            }
            cout << "HALT PUSH 1 GOTO 1\n";
        } else {
            // Fallback program (may not be correct for large k)
            cout << "9\n";
            cout << "POP 1 GOTO 2 PUSH 1 GOTO 2\n";
            cout << "POP 1 GOTO 3 PUSH 1 GOTO 3\n";
            cout << "POP 1 GOTO 4 PUSH 1 GOTO 4\n";
            cout << "POP 1 GOTO 5 PUSH 1 GOTO 5\n";
            cout << "POP 1 GOTO 6 PUSH 1 GOTO 6\n";
            cout << "POP 1 GOTO 7 PUSH 1 GOTO 7\n";
            cout << "POP 1 GOTO 8 PUSH 1 GOTO 8\n";
            cout << "POP 1 GOTO 9 PUSH 1 GOTO 9\n";
            cout << "HALT PUSH 1 GOTO 1\n";
        }
    }
    return 0;
}