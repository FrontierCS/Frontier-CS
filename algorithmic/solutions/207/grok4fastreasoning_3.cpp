#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<int> S(N);
    for (int i = 0; i < N; i++) {
        cin >> S[i];
    }
    int M;
    cin >> M;
    vector<pair<int, int>> jerry(M);
    for (int j = 0; j < M; j++) {
        int x, y;
        cin >> x >> y;
        jerry[j] = {x, y};
    }

    vector<int> pos(N);
    for (int i = 0; i < N; i++) {
        pos[S[i]] = i;
    }

    set<pair<int, int>> misplaced; // {cost, v}
    vector<int> current_cost(N, -1);
    for (int v = 0; v < N; v++) {
        int p = pos[v];
        if (p != v) {
            int c = abs(p - v);
            current_cost[v] = c;
            misplaced.insert({c, v});
        }
    }

    bool initial_sorted = misplaced.empty();
    int best_r = -1;
    long long best_v = LLONG_MAX / 2;
    if (initial_sorted) {
        best_r = 0;
        best_v = 0;
    }

    vector<pair<int, int>> my_swaps(M, {0, 0});
    vector<int> my_costs(M, 0);
    long long cum = 0;

    for (int k = 0; k < M; k++) {
        // Jerry's swap
        int a = jerry[k].first;
        int b = jerry[k].second;
        if (a != b) {
            int va = S[a];
            int vb = S[b];
            // Erase old
            if (current_cost[va] != -1) {
                misplaced.erase({current_cost[va], va});
            }
            if (current_cost[vb] != -1) {
                misplaced.erase({current_cost[vb], vb});
            }
            // Swap
            swap(S[a], S[b]);
            // Update pos
            pos[va] = b;
            pos[vb] = a;
            // New costs
            int newc_va = abs(b - va);
            if (newc_va > 0) {
                current_cost[va] = newc_va;
                misplaced.insert({newc_va, va});
            } else {
                current_cost[va] = -1;
            }
            int newc_vb = abs(a - vb);
            if (newc_vb > 0) {
                current_cost[vb] = newc_vb;
                misplaced.insert({newc_vb, vb});
            } else {
                current_cost[vb] = -1;
            }
        }

        // My move
        pair<int, int> swapuv = {0, 0};
        int dk = 0;
        if (!misplaced.empty()) {
            auto it = *misplaced.begin();
            int cost = it.first;
            int val = it.second;
            int p = pos[val];
            int t = val;
            if (p != t) {
                swapuv = {p, t};
                dk = cost;
                // Perform swap
                int x = S[t];
                // Erase old
                if (current_cost[val] != -1) {
                    misplaced.erase({current_cost[val], val});
                }
                if (current_cost[x] != -1) {
                    misplaced.erase({current_cost[x], x});
                }
                // Swap S
                swap(S[p], S[t]);
                // Update pos
                pos[val] = t;
                pos[x] = p;
                // Update costs
                current_cost[val] = -1;
                int newc_x = abs(p - x);
                if (newc_x > 0) {
                    current_cost[x] = newc_x;
                    misplaced.insert({newc_x, x});
                } else {
                    current_cost[x] = -1;
                }
            }
        }
        my_swaps[k] = swapuv;
        my_costs[k] = dk;
        cum += dk;

        // Check if sorted
        if (misplaced.empty()) {
            long long thisv = (long long)(k + 1) * cum;
            if (thisv < best_v) {
                best_v = thisv;
                best_r = k + 1;
            }
        }
    }

    // If not found, use M if sorted
    if (best_r == -1) {
        cum = 0;
        for (int d : my_costs) cum += d;
        long long thisv = (long long)M * cum;
        best_r = M;
        best_v = thisv;
    }

    cout << best_r << '\n';
    for (int i = 0; i < best_r; i++) {
        cout << my_swaps[i].first << " " << my_swaps[i].second << '\n';
    }
    cout << best_v << '\n';

    return 0;
}