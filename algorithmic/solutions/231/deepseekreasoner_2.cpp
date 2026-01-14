#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m, T;
    cin >> n >> m >> T;
    
    // Read edges (not used in this naive approach)
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
    }
    
    // No graph modifications
    cout << 0 << endl;
    cout.flush();
    
    for (int round = 0; round < T; round++) {
        int found = -1;
        for (int i = 1; i <= n; i++) {
            cout << "? 1 " << i << endl;
            cout.flush();
            string res;
            cin >> res;
            if (res == "Lose") {
                found = i;
                break;
            }
        }
        cout << "! " << found << endl;
        cout.flush();
        string verdict;
        cin >> verdict;
        if (verdict == "Wrong") {
            return 0;
        }
    }
    
    return 0;
}