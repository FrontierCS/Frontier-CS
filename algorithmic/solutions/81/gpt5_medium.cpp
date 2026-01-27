#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if(!(cin >> N)) return 0;
    string S;
    S.reserve(N);
    
    for (int k = 0; k < N; ++k) {
        int m = k + 3;
        int sink0 = k + 1;
        int sink1 = k + 2;
        vector<int> a(m, sink0), b(m, sink0);
        
        for (int i = 0; i < k; ++i) {
            if (S[i] == '0') {
                a[i] = i + 1;
                b[i] = sink0;
            } else {
                b[i] = i + 1;
                a[i] = sink0;
            }
        }
        // At position k
        a[k] = sink0;
        b[k] = sink1;
        // Make sinks absorbing
        a[sink0] = sink0; b[sink0] = sink0;
        a[sink1] = sink1; b[sink1] = sink1;

        cout << 1 << "\n";
        cout << m;
        for (int i = 0; i < m; ++i) cout << " " << a[i];
        for (int i = 0; i < m; ++i) cout << " " << b[i];
        cout << "\n";
        cout.flush();

        int x;
        if(!(cin >> x)) return 0;
        if (x == sink1) S.push_back('1');
        else S.push_back('0');
    }

    cout << 0 << " " << S << "\n";
    cout.flush();
    return 0;
}