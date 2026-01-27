#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;

    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];

    vector<string> t(M);
    for (int k = 0; k < M; k++) cin >> t[k];

    vector<vector<pair<int,int>>> pos(26);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            pos[grid[i][j] - 'A'].push_back({i, j});
        }
    }

    string S;
    S.reserve(M * 5);
    for (int k = 0; k < M; k++) S += t[k];
    int L = (int)S.size();

    vector<vector<int>> parent(L);
    vector<int> dpPrev, dpCurr;

    auto &cand0 = pos[S[0] - 'A'];
    int K0 = (int)cand0.size();
    dpPrev.assign(K0, 0);
    parent[0].assign(K0, -1);
    for (int i = 0; i < K0; i++) {
        dpPrev[i] = abs(cand0[i].first - si) + abs(cand0[i].second - sj) + 1;
    }

    for (int s = 1; s < L; s++) {
        auto &candPrev = pos[S[s - 1] - 'A'];
        auto &candCur = pos[S[s] - 'A'];
        int Kprev = (int)candPrev.size();
        int Kcur = (int)candCur.size();
        dpCurr.assign(Kcur, INT_MAX / 4);
        parent[s].assign(Kcur, -1);
        for (int i = 0; i < Kcur; i++) {
            int best = INT_MAX / 4;
            int bestIdx = -1;
            for (int j = 0; j < Kprev; j++) {
                int dist = abs(candPrev[j].first - candCur[i].first) + abs(candPrev[j].second - candCur[i].second) + 1;
                int val = dpPrev[j] + dist;
                if (val < best) {
                    best = val;
                    bestIdx = j;
                }
            }
            dpCurr[i] = best;
            parent[s][i] = bestIdx;
        }
        dpPrev.swap(dpCurr);
    }

    auto &candLast = pos[S[L - 1] - 'A'];
    int lastIdx = 0;
    int best = INT_MAX;
    for (int i = 0; i < (int)candLast.size(); i++) {
        if (dpPrev[i] < best) {
            best = dpPrev[i];
            lastIdx = i;
        }
    }

    vector<pair<int,int>> path(L);
    int idx = lastIdx;
    for (int s = L - 1; s >= 0; --s) {
        auto &cand = pos[S[s] - 'A'];
        path[s] = cand[idx];
        if (s > 0) idx = parent[s][idx];
    }

    for (auto &p : path) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}