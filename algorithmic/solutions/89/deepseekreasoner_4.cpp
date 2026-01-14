#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;
    vector<vector<bool>> anc(n+1, vector<bool>(n+1, false));
    for (int v = 1; v <= n; ++v) {
        anc[v][v] = true;
        anc[1][v] = true;
    }
    for (int v = 2; v <= n; ++v) {
        for (int u = 2; u <= n; ++u) {
            if (u == v) continue;
            cout << "? 2 " << u << " 1 " << v << endl;
            int res;
            cin >> res;
            if (res == -1) return 0;
            if (res == 1) {
                anc[u][v] = true;
            }
        }
    }
    vector<int> cnt(n+1, 0);
    for (int v = 1; v <= n; ++v) {
        int c = 0;
        for (int u = 1; u <= n; ++u) {
            if (anc[u][v]) ++c;
        }
        cnt[v] = c - 1;
    }
    vector<pair<int,int>> edges;
    for (int v = 2; v <= n; ++v) {
        int parent = -1;
        for (int u = 1; u <= n; ++u) {
            if (u != v && anc[u][v] && cnt[u] == cnt[v] - 1) {
                parent = u;
                break;
            }
        }
        edges.emplace_back(parent, v);
    }
    cout << "!" << endl;
    for (auto [u, v] : edges) {
        cout << u << " " << v << endl;
    }
    return 0;
}