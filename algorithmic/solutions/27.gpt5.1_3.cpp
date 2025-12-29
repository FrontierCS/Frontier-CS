#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n, m;
    if (!(cin >> n >> m)) return 0;

    long long nm = n * m;

    if (n == 0 || m == 0) {
        cout << 0 << '\n';
        return 0;
    }

    if (n == 1 || m == 1) {
        cout << nm << '\n';
        for (int i = 1; i <= n; ++i)
            for (int j = 1; j <= m; ++j)
                cout << i << ' ' << j << '\n';
        return 0;
    }

    bool swapped = false;
    int S, L;
    if (n <= m) {
        S = (int)n;
        L = (int)m;
    } else {
        swapped = true;
        S = (int)m;
        L = (int)n;
    }

    int D = (int)std::sqrt((double)S) + 2;
    if (D > S) D = S;

    vector<vector<char>> pairSeen(S, vector<char>(S, 0));
    vector<vector<int>> colRows(L);

    int totalCells = S * L;
    vector<int> cells(totalCells);
    iota(cells.begin(), cells.end(), 0);
    mt19937 rng(712367821);
    shuffle(cells.begin(), cells.end(), rng);

    vector<pair<int,int>> edges;
    edges.reserve(totalCells);

    for (int idx : cells) {
        int a = idx / L;
        int b = idx % L;

        if ((int)colRows[b].size() >= D) continue;

        bool ok = true;
        for (int r2 : colRows[b]) {
            if (pairSeen[a][r2]) {
                ok = false;
                break;
            }
        }
        if (!ok) continue;

        for (int r2 : colRows[b]) {
            pairSeen[a][r2] = 1;
            pairSeen[r2][a] = 1;
        }
        colRows[b].push_back(a);
        edges.emplace_back(a, b);
    }

    cout << edges.size() << '\n';
    for (auto &e : edges) {
        int a = e.first;
        int b = e.second;
        int r, c;
        if (!swapped) {
            r = a + 1;
            c = b + 1;
        } else {
            r = b + 1;
            c = a + 1;
        }
        cout << r << ' ' << c << '\n';
    }
    return 0;
}