#include <bits/stdc++.h>
using namespace std;

struct Result {
    int conf = INT_MAX;
    vector<int> color;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.push_back({u, v});
    }

    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    vector<int> deg(n);
    for (int i = 0; i < n; i++) deg[i] = (int)adj[i].size();

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto greedyInit = [&](bool randomize) -> vector<int> {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);

        if (randomize) {
            vector<uint32_t> key(n);
            for (int i = 0; i < n; i++) key[i] = rng();
            sort(order.begin(), order.end(), [&](int a, int b) {
                if (deg[a] != deg[b]) return deg[a] > deg[b];
                return key[a] < key[b];
            });
        } else {
            sort(order.begin(), order.end(), [&](int a, int b) { return deg[a] > deg[b]; });
        }

        vector<int> color(n, 0);
        vector<char> assigned(n, 0);

        for (int v : order) {
            int cnt[4] = {0, 0, 0, 0};
            for (int u : adj[v]) if (assigned[u]) cnt[color[u]]++;

            int best = min(cnt[1], min(cnt[2], cnt[3]));
            int cand[3], k = 0;
            for (int c = 1; c <= 3; c++) if (cnt[c] == best) cand[k++] = c;
            color[v] = cand[rng() % k];
            assigned[v] = 1;
        }

        if (randomize) {
            int flips = max(1, n / 20);
            for (int i = 0; i < flips; i++) {
                int v = (int)(rng() % n);
                color[v] = 1 + (int)(rng() % 3);
            }
        }
        return color;
    };

    auto randomInit = [&]() -> vector<int> {
        vector<int> color(n);
        for (int i = 0; i < n; i++) color[i] = 1 + (int)(rng() % 3);
        return color;
    };

    auto localSearch = [&](vector<int> initColor, int stepLimit, chrono::steady_clock::time_point deadline) -> Result {
        vector<int> color = std::move(initColor);

        vector<array<int,4>> cnt(n);
        for (int i = 0; i < n; i++) cnt[i].fill(0);

        for (auto [u, v] : edges) {
            cnt[u][color[v]]++;
            cnt[v][color[u]]++;
        }

        int conflicts = 0;
        for (auto [u, v] : edges) if (color[u] == color[v]) conflicts++;

        vector<char> inConf(n, 0);
        vector<int> pos(n, -1);
        vector<int> confList;
        confList.reserve(n);

        auto add = [&](int x) {
            pos[x] = (int)confList.size();
            confList.push_back(x);
            inConf[x] = 1;
        };
        auto remove = [&](int x) {
            int p = pos[x];
            int y = confList.back();
            confList[p] = y;
            pos[y] = p;
            confList.pop_back();
            pos[x] = -1;
            inConf[x] = 0;
        };
        auto updateStatus = [&](int x) {
            bool f = (cnt[x][color[x]] > 0);
            if (f) {
                if (!inConf[x]) add(x);
            } else {
                if (inConf[x]) remove(x);
            }
        };

        for (int i = 0; i < n; i++) if (cnt[i][color[i]] > 0) add(i);

        int bestConf = conflicts;
        vector<int> bestColor = color;
        int stagnate = 0;

        auto recolor = [&](int v, int newc) {
            int old = color[v];
            if (old == newc) return;
            for (int u : adj[v]) {
                int cu = color[u];
                if (cu == old) conflicts--;
                if (cu == newc) conflicts++;
                cnt[u][old]--;
                cnt[u][newc]++;
                updateStatus(u);
            }
            color[v] = newc;
            updateStatus(v);
        };

        for (int iter = 0; iter < stepLimit; iter++) {
            if ((iter & 2047) == 0) {
                if (chrono::steady_clock::now() >= deadline) break;
            }

            if (conflicts == 0) break;
            if (conflicts < bestConf) {
                bestConf = conflicts;
                bestColor = color;
                stagnate = 0;
            } else {
                stagnate++;
            }

            if (confList.empty()) break;

            int v = confList[rng() % confList.size()];
            if (confList.size() >= 2) {
                int v2 = confList[rng() % confList.size()];
                if (cnt[v2][color[v2]] > cnt[v][color[v]]) v = v2;
            }

            int old = color[v];
            int vals[4] = {0, cnt[v][1], cnt[v][2], cnt[v][3]};
            int minVal = min(vals[1], min(vals[2], vals[3]));

            int cand[3], k = 0;
            for (int c = 1; c <= 3; c++) if (vals[c] == minVal) cand[k++] = c;

            int newc = cand[rng() % k];
            if (newc == old && k > 1 && (rng() % 100) < 80) {
                do newc = cand[rng() % k]; while (newc == old);
            }

            if (newc != old) {
                recolor(v, newc);
            } else {
                int secondVal = INT_MAX, secondColor = old;
                for (int c = 1; c <= 3; c++) {
                    if (c == old) continue;
                    if (vals[c] < secondVal) {
                        secondVal = vals[c];
                        secondColor = c;
                    }
                }
                int delta = secondVal - vals[old];
                int p = 0;
                if (delta <= 1) p = 25;
                else if (delta == 2) p = 10;
                else if (delta == 3) p = 4;
                else p = 1;

                if (stagnate > 300) p *= 2;
                if (stagnate > 1500) p *= 3;
                if (p > 200) p = 200;

                if ((int)(rng() % 1000) < p) recolor(v, secondColor);
            }

            if (stagnate > 6000) {
                int shakes = 1 + n / 50;
                for (int s = 0; s < shakes; s++) {
                    int x = (int)(rng() % n);
                    int c = 1 + (int)(rng() % 3);
                    if (c != color[x]) recolor(x, c);
                }
                stagnate = 0;
            }
        }

        if (conflicts < bestConf) {
            bestConf = conflicts;
            bestColor = color;
        }

        return {bestConf, bestColor};
    };

    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(1750);

    int baseSteps;
    if (m > 300000) baseSteps = 20000;
    else if (m > 150000) baseSteps = 40000;
    else if (m > 50000) baseSteps = 90000;
    else baseSteps = 150000;

    Result globalBest;
    globalBest.conf = INT_MAX;
    globalBest.color.assign(n, 1);

    int restart = 0;
    while (true) {
        if (chrono::steady_clock::now() >= deadline) break;

        vector<int> init;
        if (restart == 0) init = greedyInit(false);
        else if (restart % 2 == 1) init = greedyInit(true);
        else init = randomInit();

        int steps = baseSteps;
        if (restart >= 3) steps = (int)(steps * 0.7);
        if (restart >= 6) steps = (int)(steps * 0.5);
        if (steps < 5000) steps = 5000;

        Result res = localSearch(std::move(init), steps, deadline);
        if (res.conf < globalBest.conf) {
            globalBest.conf = res.conf;
            globalBest.color = std::move(res.color);
            if (globalBest.conf == 0) break;
        }

        restart++;
        if (restart > 30) break;
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        int c = globalBest.color[i];
        if (c < 1 || c > 3) c = 1;
        cout << c;
    }
    cout << '\n';
    return 0;
}