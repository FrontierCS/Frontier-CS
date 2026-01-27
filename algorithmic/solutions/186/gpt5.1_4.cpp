#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> deg(N + 1);
    for (int i = 1; i <= N; ++i) deg[i] = (int)adj[i].size();

    vector<int> color(N + 1, 0);
    vector<int> sat(N + 1, 0);
    vector<char> colored(N + 1, 0);

    const int MAXC = MAXN;
    vector<vector<char>> hasColor(N + 1, vector<char>(MAXC + 1, 0));

    vector<char> usedColor(MAXC + 2, 0);
    vector<int> touched;

    int coloredCount = 0;
    int maxColor = 0;

    while (coloredCount < N) {
        int best = -1;
        for (int i = 1; i <= N; ++i) {
            if (colored[i]) continue;
            if (best == -1 ||
                sat[i] > sat[best] ||
                (sat[i] == sat[best] && deg[i] > deg[best])) {
                best = i;
            }
        }
        int u = best;

        touched.clear();
        for (int v : adj[u]) {
            int c = color[v];
            if (c != 0 && !usedColor[c]) {
                usedColor[c] = 1;
                touched.push_back(c);
            }
        }
        int chosenColor = 1;
        while (chosenColor <= maxColor && usedColor[chosenColor]) ++chosenColor;
        if (chosenColor > maxColor) maxColor = chosenColor;

        color[u] = chosenColor;
        colored[u] = 1;
        ++coloredCount;

        for (int c : touched) usedColor[c] = 0;

        for (int v : adj[u]) {
            if (colored[v]) continue;
            if (!hasColor[v][chosenColor]) {
                hasColor[v][chosenColor] = 1;
                ++sat[v];
            }
        }
    }

    for (int i = 1; i <= N; ++i)
        cout << color[i] << '\n';

    return 0;
}