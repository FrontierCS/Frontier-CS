#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    while (cin >> n >> m) {
        vector<string> S(m);
        vector<int> T(m);
        for (int i = 0; i < m; ++i) {
            cin >> S[i];
            string t;
            cin >> t;
            T[i] = t[0] - '0';
        }
        
        vector<int> mistakes(n, 0);
        for (int j = 0; j < n; ++j) {
            int cnt = 0;
            for (int i = 0; i < m; ++i) {
                if ((S[i][j] - '0') != T[i]) ++cnt;
            }
            mistakes[j] = cnt;
        }
        
        int best = 0;
        for (int j = 1; j < n; ++j) {
            if (mistakes[j] < mistakes[best]) best = j;
        }
        
        for (int i = 0; i < m; ++i) {
            cout << S[i][best] << '\n';
        }
    }
    return 0;
}