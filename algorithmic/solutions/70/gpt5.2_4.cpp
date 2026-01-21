#include <bits/stdc++.h>
using namespace std;

static uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed = splitmix64(seed);
    mt19937 rng((uint32_t)seed);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; tc++) {
        int n, m, start;
        long long base_move_count;
        cin >> n >> m >> start >> base_move_count;

        vector<int> deg(n + 1, 0);
        for (int i = 0; i < m; i++) {
            int u, v;
            cin >> u >> v;
            deg[u]++, deg[v]++;
        }

        unordered_map<int,int> totalByDegree, visitedByDegree;
        totalByDegree.reserve(n * 2);
        visitedByDegree.reserve(n * 2);

        for (int v = 1; v <= n; v++) totalByDegree[deg[v]]++;

        long long moves = 0;
        long long stepsSinceNew = 0;
        int prevDegree = -1;

        visitedByDegree[deg[start]]++;

        while (true) {
            string tok;
            if (!(cin >> tok)) return 0;

            if (tok == "AC" || tok == "F") {
                break;
            }

            int d = stoi(tok);
            vector<int> nd(d), nf(d);
            for (int i = 0; i < d; i++) cin >> nd[i] >> nf[i];

            auto remainingFor = [&](int dv) -> int {
                auto itT = totalByDegree.find(dv);
                if (itT == totalByDegree.end()) return 0;
                int total = itT->second;
                int vis = 0;
                auto itV = visitedByDegree.find(dv);
                if (itV != visitedByDegree.end()) vis = itV->second;
                return max(0, total - vis);
            };

            int chosen = 1;
            bool chosenIsNew = false;

            vector<int> unvis;
            unvis.reserve(d);
            for (int i = 0; i < d; i++) if (nf[i] == 0) unvis.push_back(i);

            if (!unvis.empty()) {
                int bestDeg = INT_MAX;
                int bestRem = -1;
                vector<int> cand;
                for (int idx : unvis) {
                    int dv = nd[idx];
                    int rem = remainingFor(dv);
                    if (dv < bestDeg || (dv == bestDeg && rem > bestRem)) {
                        bestDeg = dv;
                        bestRem = rem;
                        cand.clear();
                        cand.push_back(idx);
                    } else if (dv == bestDeg && rem == bestRem) {
                        cand.push_back(idx);
                    }
                }
                uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
                chosen = cand[dist(rng)] + 1;
                chosenIsNew = true;
            } else {
                int pred = -1;
                if (prevDegree != -1) {
                    int cnt = 0, last = -1;
                    for (int i = 0; i < d; i++) {
                        if (nf[i] == 1 && nd[i] == prevDegree) {
                            cnt++;
                            last = i;
                        }
                    }
                    if (cnt == 1) pred = last;
                }

                long long bestScore = LLONG_MIN;
                vector<int> cand;
                cand.reserve(d);

                for (int i = 0; i < d; i++) {
                    int dv = nd[i];
                    int rem = remainingFor(dv);

                    long long score = 0;
                    score += (rem > 0 ? 1000000LL : 0LL);
                    score += 1000LL * rem;
                    score += 3LL * dv;

                    if (pred != -1 && i == pred && d > 1) score -= 7;
                    if (stepsSinceNew > n && pred != -1 && i == pred && d > 1) score -= 25;

                    if (score > bestScore) {
                        bestScore = score;
                        cand.clear();
                        cand.push_back(i);
                    } else if (score == bestScore) {
                        cand.push_back(i);
                    }
                }

                uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
                chosen = cand[dist(rng)] + 1;
            }

            if (chosenIsNew) {
                visitedByDegree[nd[chosen - 1]]++;
                stepsSinceNew = 0;
            } else {
                stepsSinceNew++;
            }

            cout << chosen << endl;

            prevDegree = d;
            moves++;
        }
    }

    return 0;
}