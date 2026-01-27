#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n, m;
        cin >> n >> m;
        vector<pair<int,int>> edges(m);
        for (int i = 0; i < m; ++i) {
            cin >> edges[i].first >> edges[i].second;
        }
        // Dummy interaction: assume no edges are repaired
        cout << "!";
        for (int i = 0; i < m; ++i) cout << " 0";
        cout << endl;
        cout.flush();
        int res;
        cin >> res;
        if (res == 0) break; // wrong answer, terminate
    }
    return 0;
}