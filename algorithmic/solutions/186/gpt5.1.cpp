#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> color(N, 0);
    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();

    vector<int> satDeg(N, 0);
    vector<bitset<512>> usedColors(N);
    vector<char> colored(N, 0);

    int coloredCount = 0;
    int maxColorUsed = 0;

    // Choose initial vertex: one with maximum degree
    int first = 0;
    for (int i = 1; i < N; ++i) {
        if (deg[i] > deg[first]) first = i;
    }

    while (coloredCount < N) {
        int vtx = -1;
        if (coloredCount == 0) {
            vtx = first;
        } else {
            int bestSat = -1;
            int bestDeg = -1;
            int bestIdx = -1;
            for (int i = 0; i < N; ++i) {
                if (!colored[i]) {
                    int sd = satDeg[i];
                    if (sd > bestSat || (sd == bestSat && deg[i] > bestDeg)) {
                        bestSat = sd;
                        bestDeg = deg[i];
                        bestIdx = i;
                    }
                }
            }
            vtx = bestIdx;
        }

        bitset<512> &b = usedColors[vtx];
        int chosenColor = 0;
        for (int c = 0; c <= maxColorUsed; ++c) {
            if (!b.test(c)) {
                chosenColor = c + 1;
                break;
            }
        }
        if (chosenColor == 0) {
            chosenColor = maxColorUsed + 1;
        }
        if (chosenColor > maxColorUsed) maxColorUsed = chosenColor;

        color[vtx] = chosenColor;
        colored[vtx] = 1;
        ++coloredCount;

        int cidx = chosenColor - 1;
        for (int to : adj[vtx]) {
            if (colored[to]) continue;
            if (!usedColors[to].test(cidx)) {
                usedColors[to].set(cidx);
                ++satDeg[to];
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        if (color[i] == 0) color[i] = 1;
        cout << color[i] << '\n';
    }

    return 0;
}