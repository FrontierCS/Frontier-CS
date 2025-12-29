#include <iostream>
#include <vector>
using namespace std;

const long long MOD = 1000000007;

int main() {
    int n;
    cin >> n;
    
    vector<long long> T(n + 1); // T[i] for i = 1..n-1
    long long R;
    
    // reference query: a0 = 2, all a_i = 1
    cout << "? 2";
    for (int i = 1; i <= n; ++i) cout << " 1";
    cout << endl;
    cin >> R;
    
    // queries for operators 1..n-1
    for (int i = 1; i <= n - 1; ++i) {
        cout << "? 2";
        for (int j = 1; j <= n; ++j) {
            if (j == i) cout << " 2";
            else cout << " 1";
        }
        cout << endl;
        cin >> T[i];
    }
    
    vector<int> ops(n + 1); // 0 -> '+', 1 -> '*'
    long long C = 2; // value after 0 operators (just a0)
    
    for (int i = 1; i <= n - 1; ++i) {
        long long diff = (T[i] - R + MOD) % MOD;
        
        if (i == 1) {
            if (diff == 1) ops[1] = 0;
            else ops[1] = 1; // diff must be 2
        } else {
            if (diff == 1) ops[i] = 0;
            else if (diff == C) ops[i] = 1;
            // According to the problem, one of these must hold
        }
        
        // update C for the next operator (apply op_i with operand 1)
        if (ops[i] == 0) C = (C + 1) % MOD;
        // for multiplication by 1, C remains unchanged
    }
    
    // determine the last operator
    if (R == (C + 1) % MOD) ops[n] = 0;
    else ops[n] = 1; // R must equal C
    
    // output the answer
    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << ops[i];
    cout << endl;
    
    return 0;
}