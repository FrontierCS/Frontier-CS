#include <bits/stdc++.h>
using namespace std;

using Clock = std::chrono::steady_clock;
using TimePoint = Clock::time_point;

static inline bool time_remaining(const TimePoint& deadline) {
    return Clock::now() < deadline;
}

pair<vector<char>, int> greedyMIS(const vector<vector<int>>& g, const vector<int>& order) {
    int n = (int)g.size();
    vector<char> inS(n, 0), banned(n, 0);
    int K = 0;
    for (int v : order) {
        if (!banned[v]) {
            inS[v] = 1;
            ++K;
            banned[v] = 1;
            for (int u : g[v]) banned[u] = 1;
        }
    }
    return {inS, K};
}

void augmentToMaximal(const vector<vector<int>>& g, vector<char>& inS, vector<int>& cnt) {
    int n = (int)g.size();
    for (int i = 0; i < n; ++i) {
        if (!inS[i] && cnt[i] == 0) {
            inS[i] = 1;
            for (int nb : g[i]) cnt[nb]++;
        }
    }
}

void twoSwapImprove(const vector<vector<int>>& g, vector<char>& inS, const TimePoint& deadline) {
    int n = (int)g.size();
    vector<int> cnt(n, 0);
    for (int v = 0; v < n; ++v) if (inS[v]) {
        for (int nb : g[v]) cnt[nb]++;
    }

    vector<char> inCand(n, 0);
    vector<int> mark(n, 0);
    int stamp = 1;

    bool improved = true;
    int passes = 0;
    while (improved && time_remaining(deadline)) {
        improved = false;

        vector<int> sList;
        sList.reserve(n);
        for (int v = 0; v < n; ++v) if (inS[v]) sList.push_back(v);

        for (int v : sList) {
            if (!time_remaining(deadline)) break;
            if (!inS[v]) continue;

            vector<int> cand;
            cand.reserve(g[v].size());
            for (int nb : g[v]) {
                if (!inS[nb] && cnt[nb] == 1) {
                    cand.push_back(nb);
                    inCand[nb] = 1;
                }
            }

            if ((int)cand.size() >= 2) {
                bool pairFound = false;
                int uSel = -1, wSel = -1;

                for (int u : cand) {
                    if (pairFound) break;
                    ++stamp;
                    for (int t : g[u]) if (inCand[t]) mark[t] = stamp;
                    for (int w : cand) {
                        if (w == u) continue;
                        if (mark[w] != stamp) {
                            pairFound = true;
                            uSel = u;
                            wSel = w;
                            break;
                        }
                    }
                }

                if (pairFound) {
                    inS[v] = 0;
                    for (int nb : g[v]) cnt[nb]--;

                    inS[uSel] = 1;
                    for (int nb : g[uSel]) cnt[nb]++;

                    inS[wSel] = 1;
                    for (int nb : g[wSel]) cnt[nb]++;

                    improved = true;
                }
            }

            for (int x : cand) inCand[x] = 0;
        }

        if (improved && time_remaining(deadline)) {
            augmentToMaximal(g, inS, cnt);
        }
        passes++;
        if (passes >= 3) break; // limit passes to control time
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<vector<int>> g(N);
    g.reserve(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    for (int i = 0; i < N; ++i) {
        auto &vec = g[i];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) deg[i] = (int)g[i].size();

    vector<char> bestS(N, 0);
    int bestK = 0;

    vector<int> ids(N);
    iota(ids.begin(), ids.end(), 0);

    std::mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    TimePoint start = Clock::now();
    TimePoint triesDeadline = start + chrono::milliseconds(1200);
    TimePoint finalDeadline = start + chrono::milliseconds(1900);

    while (time_remaining(triesDeadline)) {
        vector<int> order = ids;
        shuffle(order.begin(), order.end(), rng);
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            if (deg[a] != deg[b]) return deg[a] < deg[b];
            return a < b;
        });
        auto res = greedyMIS(g, order);
        if (res.second > bestK) {
            bestK = res.second;
            bestS = move(res.first);
        }
    }

    twoSwapImprove(g, bestS, finalDeadline);

    for (int i = 0; i < N; ++i) {
        cout << (bestS[i] ? 1 : 0) << '\n';
    }
    return 0;
}