#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    int k;
    cin >> k;
    
    if (k == 1) {
        cout << 1 << endl;
        cout << "HALT PUSH 1 GOTO 1" << endl;
        return 0;
    }
    
    if (k == 3) {
        cout << 3 << endl;
        cout << "POP 1 GOTO 2 PUSH 1 GOTO 2" << endl;
        cout << "POP 1 GOTO 3 PUSH 1 GOTO 1" << endl;
        cout << "HALT PUSH 1 GOTO 1" << endl;
        return 0;
    }
    
    // k >= 5
    if (k % 4 == 1) {
        int m = (k + 3) / 4;  // m >= 2
        int n = m + 3;
        cout << n << endl;
        // push instructions 1..m
        for (int i = 1; i <= m; ++i) {
            int next = i + 1;
            if (i == m) next = m + 1;
            cout << "POP 2 GOTO " << next << " PUSH 1 GOTO " << next << endl;
        }
        // loop instructions
        cout << "POP 1 GOTO " << m+2 << " PUSH 1 GOTO " << m+1 << endl;
        cout << "POP 1 GOTO " << m+3 << " PUSH 1 GOTO " << m+1 << endl;
        cout << "HALT PUSH 1 GOTO " << m+1 << endl;
    } else { // k % 4 == 3
        int m = (k + 1) / 4;  // m >= 2
        int n = m + 5;
        cout << n << endl;
        // extra pair
        cout << "POP 2 GOTO 2 PUSH 1 GOTO 2" << endl;
        cout << "POP 1 GOTO 3 PUSH 1 GOTO 1" << endl;
        // push instructions 3..(m+2)
        for (int i = 3; i <= m+2; ++i) {
            int next = i + 1;
            if (i == m+2) next = m+3;
            cout << "POP 2 GOTO " << next << " PUSH 1 GOTO " << next << endl;
        }
        // loop instructions
        cout << "POP 1 GOTO " << m+4 << " PUSH 1 GOTO " << m+3 << endl;
        cout << "POP 1 GOTO " << m+5 << " PUSH 1 GOTO " << m+3 << endl;
        cout << "HALT PUSH 1 GOTO " << m+3 << endl;
    }
    
    return 0;
}