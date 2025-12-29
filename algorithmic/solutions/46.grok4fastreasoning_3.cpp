#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
    int J, M;
    cin >> J >> M;
    vector<vector<int>> route(J, vector<int>(M));
    vector<vector<ll>> p(J, vector<ll>(M));
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            cin >> route[j][k] >> p[j][k];
        }
    }
    vector<vector<int>> pos(J, vector<int>(M));
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int m = route[j][k];
            pos[j][m] = k;
        }
    }
    auto compute_makespan = [&](const vector<vector<int>>& orders) -> ll {
        int N = J * M;
        vector<vector<pair<int, ll>>> g(N);
        for (int j = 0; j < J; j++) {
            for (int k = 0; k < M - 1; k++) {
                int u = j * M + k;
                int v = j * M + (k + 1);
                g[u].emplace_back(v, p[j][k]);
            }
        }
        for (int m = 0; m < M; m++) {
            for (int i = 0; i < J - 1; i++) {
                int ja = orders[m][i];
                int jb = orders[m][i + 1];
                int ka = pos[ja][m];
                int kb = pos[jb][m];
                int u = ja * M + ka;
                int v = jb * M + kb;
                g[u].emplace_back(v, p[ja][ka]);
            }
        }
        vector<int> indeg(N, 0);
        for (int u = 0; u < N; u++) {
            for (auto [v, w] : g[u]) {
                indeg[v]++;
            }
        }
        vector<ll> dist(N, 0);
        queue<int> q;
        for (int i = 0; i < N; i++) {
            if (indeg[i] == 0) q.push(i);
        }
        int visited = 0;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            visited++;
            for (auto [v, w] : g[u]) {
                dist[v] = max(dist[v], dist[u] + w);
                if (--indeg[v] == 0) q.push(v);
            }
        }
        if (visited < N) return LLONG_MAX / 2;
        ll makespan = 0;
        for (int j = 0; j < J; j++) {
            int k = M - 1;
            int id = j * M + k;
            ll comp = dist[id] + p[j][k];
            makespan = max(makespan, comp);
        }
        return makespan;
    };
    auto local_search = [&](vector<vector<int>> start) -> pair<vector<vector<int>>, ll> {
        auto curr = start;
        ll cur_ms = compute_makespan(curr);
        bool changed = true;
        int iters = 0;
        const int MAX_ITERS = 1000;
        while (changed && iters++ < MAX_ITERS) {
            changed = false;
            ll min_score = cur_ms;
            pair<int, int> best_swap = {-1, -1};
            for (int m = 0; m < M; m++) {
                for (int i = 0; i < J - 1; i++) {
                    auto temp = curr;
                    swap(temp[m][i], temp[m][i + 1]);
                    ll score = compute_makespan(temp);
                    if (score < min_score && score < LLONG_MAX / 2) {
                        min_score = score;
                        best_swap = {m, i};
                    }
                }
            }
            if (best_swap.first != -1) {
                int m = best_swap.first, ii = best_swap.second;
                swap(curr[m][ii], curr[m][ii + 1]);
                cur_ms = min_score;
                changed = true;
            }
        }
        return {curr, cur_ms};
    };
    // SPT
    vector<vector<int>> spt_orders(M, vector<int>(J));
    for (int m = 0; m < M; m++) {
        vector<pair<ll, int>> vp;
        for (int j = 0; j < J; j++) {
            vp.emplace_back(p[j][pos[j][m]], j);
        }
        sort(vp.begin(), vp.end());
        for (int i = 0; i < J; i++) spt_orders[m][i] = vp[i].second;
    }
    auto [spt_final, spt_final_ms] = local_search(spt_orders);
    // LPT
    vector<vector<int>> lpt_orders(M, vector<int>(J));
    for (int m = 0; m < M; m++) {
        vector<pair<ll, int>> vp;
        for (int j = 0; j < J; j++) {
            vp.emplace_back(p[j][pos[j][m]], j);
        }
        sort(vp.rbegin(), vp.rend());
        for (int i = 0; i < J; i++) lpt_orders[m][i] = vp[i].second;
    }
    auto [lpt_final, lpt_final_ms] = local_search(lpt_orders);
    // Select best
    vector<vector<int>> solution;
    if (spt_final_ms <= lpt_final_ms) {
        solution = spt_final;
    } else {
        solution = lpt_final;
    }
    // Output
    for (int m = 0; m < M; m++) {
        for (int i = 0; i < J; i++) {
            if (i) cout << " ";
            cout << solution[m][i];
        }
        cout << endl;
    }
    return 0;
}