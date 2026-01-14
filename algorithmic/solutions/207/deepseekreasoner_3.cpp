#include <iostream>
#include <vector>
#include <set>
#include <cmath>
#include <algorithm>
using namespace std;

typedef long long ll;

struct Result {
    int R;
    vector<pair<int, int>> swaps;
    ll V;
};

Result simulate(const vector<int>& S, const vector<pair<int, int>>& jerry, bool use_min) {
    int N = (int)S.size();
    int M = (int)jerry.size();
    vector<int> val = S;
    vector<int> pos(N);
    for (int i = 0; i < N; ++i) pos[S[i]] = i;
    vector<int> cost(N);
    set<pair<int, int>> mis;  // (cost, element)
    for (int i = 0; i < N; ++i) {
        cost[i] = abs(pos[i] - i);
        if (cost[i] > 0) mis.insert({cost[i], i});
    }

    vector<pair<int, int>> our;
    vector<ll> dist;
    bool sorted_found = false;
    int sorted_round = -1;

    for (int k = 0; k < M; ++k) {
        int x = jerry[k].first, y = jerry[k].second;

        // Jerry's move
        if (x != y) {
            int a = val[x], b = val[y];
            if (cost[a] > 0) mis.erase({cost[a], a});
            if (cost[b] > 0) mis.erase({cost[b], b});
            swap(val[x], val[y]);
            swap(pos[a], pos[b]);
            cost[a] = abs(pos[a] - a);
            cost[b] = abs(pos[b] - b);
            if (cost[a] > 0) mis.insert({cost[a], a});
            if (cost[b] > 0) mis.insert({cost[b], b});
        }

        // Our move
        int u = 0, v = 0;
        if (!mis.empty()) {
            bool reciprocal = false;
            if (x != y) {
                int a = val[x], b = val[y];  // elements currently at x and y after Jerry's swap
                for (int e : {a, b}) {
                    if (cost[e] == 0) continue;
                    int target_e = e;
                    int c = val[target_e];
                    if (c == e) continue;
                    if (pos[c] == target_e && pos[e] == c) {
                        u = pos[e];
                        v = pos[c];
                        reciprocal = true;
                        break;
                    }
                }
            }
            if (!reciprocal) {
                int i;
                if (use_min) {
                    auto it = mis.begin();
                    i = it->second;
                } else {
                    auto it = mis.rbegin();
                    i = it->second;
                }
                u = pos[i];
                v = i;
            }
        }

        // Apply our swap
        if (u != v) {
            int c = val[u], d = val[v];
            if (cost[c] > 0) mis.erase({cost[c], c});
            if (cost[d] > 0) mis.erase({cost[d], d});
            swap(val[u], val[v]);
            swap(pos[c], pos[d]);
            cost[c] = abs(pos[c] - c);
            cost[d] = abs(pos[d] - d);
            if (cost[c] > 0) mis.insert({cost[c], c});
            if (cost[d] > 0) mis.insert({cost[d], d});
        }

        our.push_back({u, v});
        ll d = abs(u - v);
        dist.push_back(d);

        if (mis.empty() && !sorted_found) {
            sorted_found = true;
            sorted_round = k;
        }
    }

    int R;
    if (sorted_found) {
        R = sorted_round + 1;
    } else {
        R = M;  // fallback
    }

    ll total_sum = 0;
    for (int i = 0; i < R; ++i) total_sum += dist[i];
    ll V = (ll)R * total_sum;
    return {R, our, V};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<int> S(N);
    for (int i = 0; i < N; ++i) cin >> S[i];
    int M;
    cin >> M;
    vector<pair<int, int>> jerry(M);
    for (int i = 0; i < M; ++i) {
        cin >> jerry[i].first >> jerry[i].second;
    }

    // Check if already sorted
    bool already_sorted = true;
    for (int i = 0; i < N; ++i) if (S[i] != i) { already_sorted = false; break; }
    if (already_sorted) {
        cout << "0\n0\n";
        return 0;
    }

    Result res_min = simulate(S, jerry, true);
    Result res_max = simulate(S, jerry, false);

    Result best = (res_min.V <= res_max.V) ? res_min : res_max;

    cout << best.R << "\n";
    for (int i = 0; i < best.R; ++i) {
        cout << best.swaps[i].first << " " << best.swaps[i].second << "\n";
    }
    cout << best.V << "\n";

    return 0;
}