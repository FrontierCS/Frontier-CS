#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, R;
    while ( (cin >> N >> R) ) {
        vector<pair<int,int>> uv(N);
        for (int i = 0; i < N; ++i) {
            int u, v;
            cin >> u >> v;
            uv[i] = {u, v};
        }
        string t;
        if (!(cin >> t)) return 0;
        cout << t << "\n";
    }
    return 0;
}