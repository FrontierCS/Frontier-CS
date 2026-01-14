#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m, tt;
    cin >> n >> m >> tt;
    vector<pair<int, int>> edges(m);
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        edges[i] = {a, b};
    }
    long long adds = (long long)n * (n - 1) / 2;
    long long K = m + adds;
    cout << K << '\n';
    for (auto [a, b] : edges) {
        cout << "- " << a << " " << b << '\n';
    }
    for (int i = 2; i <= n; i++) {
        for (int j = 1; j < i; j++) {
            cout << "+ " << i << " " << j << '\n';
        }
    }
    cout.flush();
    for (int rnd = 0; rnd < tt; rnd++) {
        vector<int> possible;
        for (int i = 1; i <= n; i++) possible.push_back(i);
        while (possible.size() > 1) {
            int u = possible[0];
            cout << "? 1 " << u << '\n';
            cout.flush();
            string s;
            cin >> s;
            if (s == "Lose") {
                cout << "! " << u << '\n';
                cout.flush();
                string verdict;
                cin >> verdict;
                if (verdict == "Wrong") return 0;
                break;
            } else {
                possible.erase(possible.begin());
            }
        }
        if (possible.size() == 1) {
            int u = possible[0];
            cout << "! " << u << '\n';
            cout.flush();
            string verdict;
            cin >> verdict;
            if (verdict == "Wrong") return 0;
        }
    }
    return 0;
}