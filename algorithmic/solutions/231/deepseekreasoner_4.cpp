#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m, T;
    cin >> n >> m >> T;
    
    // Read and ignore edges
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
    }
    
    // No modifications
    cout << "0" << endl;
    cout.flush();
    
    // Process each round
    for (int round = 0; round < T; round++) {
        int guess = 1;
        for (int i = 1; i <= n; i++) {
            cout << "? 1 " << i << endl;
            cout.flush();
            string res;
            cin >> res;
            if (res == "Lose") {
                guess = i;
                break;
            }
        }
        cout << "! " << guess << endl;
        cout.flush();
        string verdict;
        cin >> verdict;
        if (verdict == "Wrong") {
            return 0;
        }
    }
    
    return 0;
}